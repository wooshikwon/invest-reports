#!/usr/bin/env python3
"""live.py — 미국 장이 열린 동안 1분마다 공개 종목의 마지막 체결가를 invest-live Worker의 DO에 쓴다.

cron(`~/scripts/cron/invest-live-tick.sh`)이 1분마다 `tick()`을 부른다. 회차마다 장 시간을 판정하고, 토스 `GET /api/v1/prices`를 한 번 불러
공개 종목과 보유 종목의 마지막 체결가를 받고, `premarket`·`afterhours` 값을 조립해 `POST /write/{이름}`으로 쓴다.
공개 종목은 `r/market.json` 지도 종목과 지수 ETF(`SECTOR_DB_TICKERS`)다. 보유 종목은 `~/data/invest-account/holdings.json`(심볼만)에서 읽고,
그 체결가는 invest-live에 쓰지 않고 invest-account Worker의 DO에 `POST /live`로만 쓴다. 토스가 답하지 않거나 빠뜨린 심볼만 야후 `v7/finance/spark`에서 받는다.
토스가 체결 시각 없이 준 심볼은 체결이 없는 것으로 보고 야후에 묻지 않는다. 토큰은 toss-trader와 함께 쓰는 캐시 파일만 쓴다.

값의 스키마는 build.py 머리 설명의 `premarket`·`afterhours` 값과 같다. `premarket`은 프리장(`PREMARKET_OPEN`)부터 정규장이 닫힐 때까지 1분마다 그 분의 값을 쓰고,
정규장이 닫히고 `CLOSE_WAIT`가 지난 첫 회차가 마감 시각까지 끝난 1분봉으로 마감 값을 한 번 더 받아 고정한다.
`afterhours`는 `AFTER_OPEN`과 마감 고정 회차 가운데 늦은 쪽부터 `AFTER_CLOSE`까지 1분마다 쓴다.
체결가는 `premarket`이면 오늘 `PREMARKET_OPEN` 뒤, `afterhours`이면 오늘 정규장 마감 뒤 체결만 쓴다. 그 체결이 없으면 앞 회차 값을 두고,
앞 회차 값도 없으면 null이다. 지도의 첫 날짜보다 앞선 날짜의 값은 지운다.
휴장일, 프리장 전, 마감 뒤 `CLOSE_WAIT` 안, 그날 값을 이미 다 받은 회차는 토스를 부르지 않고 끝난다.

앞 세션 날짜와 정규장 마감 시각은 세션마다 한 번 `exchange_calendars`에서, 지수 ETF의 앞 세션 종가는 그 세션의 첫 장중 회차에 토스 일봉에서 받아
`~/data/invest-reports/live/session-{YYYY-MM-DD}.json`에 둔다. 앞 회차 값은 DO에 쓴 값과 같은 `{이름}.json`에 두고 다시 읽는다.
회차마다 가격 없는 기록(`tick-{날짜}.log`)과, DO에 쓴 그날 값(`snap-{날짜}.jsonl`)을 남긴다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import exchange_calendars
import requests
from curl_cffi import requests as chrome

import build
from build import AFTER_CLOSE, AFTER_OPEN, NEW_YORK, PREMARKET_CLOSE, PREMARKET_OPEN, ROOT

sys.path.insert(0, str(Path.home() / "obsidian-vault/agent/skills/tool/invest-report/scripts"))
from path_bands import SECTOR_DB_TICKERS  # noqa: E402  지수마다의 지수 ETF

DATA = Path.home() / "data" / "invest-reports" / "live"
HOLDINGS = Path.home() / "data" / "invest-account" / "holdings.json"  # account_push가 쓰는 보유 종목 심볼 목록(0600)
TOSS = "https://openapi.tossinvest.com"
ACCOUNT_URL = "https://invest-account.wonwooshik.workers.dev"  # 계좌 Worker 주소. `POST /live`가 보유 종목 체결가를 DO에 쓴다
TOSS_ENV = Path.home() / ".toss_env"
# 토스는 한 자격증명에 토큰 하나만 살려 두고, 새로 발급하면 앞의 토큰을 바로 거절한다. 그래서 toss-trader와 같은 캐시 파일과 자물쇠를 쓰고,
# 남은 시간이 `TOKEN_MARGIN`초보다 많은 캐시 토큰은 새로 받지 않는다.
TOKEN_CACHE = Path.home() / "repos" / "toss-trader" / ".token_cache.json"
TOKEN_LOCK = TOKEN_CACHE.with_suffix(".lock")
TOKEN_MARGIN = 300
TIMEOUT = 15
ENCODING = "gzip, deflate"  # 토스 응답의 압축 방식. toss-trader 클라이언트와 같이 zstd를 뺀다
SPARK = "https://query1.finance.yahoo.com/v7/finance/spark"
SPARK_BATCH = 20  # 야후 spark 한 번에 묻는 심볼 수 상한
CANDLE_WAIT = 0.05  # 토스 1분봉을 이어 부를 때 사이를 띄우는 초. 차트 조회는 초당 20회까지 받는다
# 초당 상한은 같은 자격증명을 쓰는 toss-trader·판단 배치와 함께 센다. 그래서 429로 거절된 조회는 `RETRY_WAIT`초 뒤 `ATTEMPTS`번까지 부른다.
RETRY_WAIT = 2
ATTEMPTS = 3
CLOSE_WAIT = dt.timedelta(minutes=5)  # 마감 체결이 1분봉에 실리기를 기다리는 시간
KEEP_DAYS = 7  # `DATA`의 날짜 붙은 파일을 남기는 날 수
NAMES = ("premarket", "afterhours")


def toss_symbol(symbol: str) -> str:
    """야후 심볼을 토스 심볼로. 종류주 구분자가 야후는 붙임표, 토스는 점이다."""
    return symbol.replace("-", ".")


def save(path: Path, value) -> None:
    """`value`를 JSON으로 `path`에 0600으로 한 번에 바꿔 쓴다."""
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temp.chmod(0o600)
    os.replace(temp, path)


def load(path: Path, empty):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else empty


class Toss:
    """토스 Open API 조회. 부른 횟수를 경로마다 세고(`calls`), 야후로 넘긴 심볼 수를 센다(`yahoo`)."""

    def __init__(self):
        self.calls = {"prices": 0, "candles": 0}
        self.yahoo = 0

    @staticmethod
    def cached(dead: str | None) -> str | None:
        try:
            cache = json.loads(TOKEN_CACHE.read_text())
        except (OSError, ValueError):
            return None
        if cache.get("access_token") and cache["access_token"] != dead and cache.get("expires_at", 0) - TOKEN_MARGIN > time.time():
            return cache["access_token"]
        return None

    def token(self, dead: str | None = None) -> str:
        """캐시의 살아 있는 토큰. 없으면 자물쇠를 잡고 캐시를 다시 읽은 뒤, 그래도 없을 때만 새로 받아 캐시에 쓴다."""
        if found := self.cached(dead):
            return found
        with open(TOKEN_LOCK, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                if found := self.cached(dead):
                    return found
                keys = dict(line.strip().split("=", 1) for line in TOSS_ENV.read_text().splitlines() if "=" in line)
                answer = requests.post(f"{TOSS}/oauth2/token", timeout=30, headers={"Accept-Encoding": ENCODING},
                                       data={"grant_type": "client_credentials", "client_id": keys["TOSS_API_KEY"], "client_secret": keys["TOSS_API_SECRET"]})
                answer.raise_for_status()
                issued = answer.json()
                mode = TOKEN_CACHE.stat().st_mode & 0o777 if TOKEN_CACHE.exists() else 0o600
                temp = TOKEN_CACHE.with_name(f".{TOKEN_CACHE.name}.tmp")
                temp.write_text(json.dumps({"access_token": issued["access_token"], "expires_at": time.time() + issued.get("expires_in", 86400)}))
                temp.chmod(mode)
                os.replace(temp, TOKEN_CACHE)
                return issued["access_token"]
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def get(self, path: str, params: dict) -> dict:
        """GET 한 번의 응답 본문(`result`). 401이면 그 토큰을 죽은 것으로 보고 한 번만 다시 부른다.

        429면 `RETRY_WAIT`초 뒤 다시 부르고, `ATTEMPTS`번 모두 거절되면 HTTPError를 낸다.
        """
        used, renewed = self.token(), False
        for _ in range(ATTEMPTS):
            self.calls[path.rsplit("/", 1)[-1]] += 1
            answer = requests.get(f"{TOSS}{path}", params=params, timeout=TIMEOUT,
                                  headers={"Authorization": f"Bearer {used}", "Accept-Encoding": ENCODING})
            if answer.status_code == 401 and not renewed:
                used, renewed = self.token(dead=used), True
                continue
            if answer.status_code == 429:
                time.sleep(RETRY_WAIT)
                continue
            answer.raise_for_status()
            return answer.json()["result"]
        answer.raise_for_status()
        raise RuntimeError("토스 토큰이 두 번 거절됨")


def spark(symbols: list[str], **params) -> dict[str, dict]:
    """야후 spark의 심볼마다 응답(`meta`, `timestamp`, `indicators`). 답하지 않은 묶음의 심볼은 빠진다."""
    found = {}
    for start in range(0, len(symbols), SPARK_BATCH):
        try:
            answer = chrome.get(SPARK, impersonate="chrome124", timeout=20,
                                params={"symbols": ",".join(symbols[start:start + SPARK_BATCH]), "range": "1d", "interval": "1m", **params})
            answer.raise_for_status()
            for item in answer.json()["spark"]["result"] or []:
                if item.get("response"):
                    found[item["symbol"]] = item["response"][0]
        except Exception as error:  # noqa: BLE001  야후가 답하지 않으면 그 묶음을 비워 둔다
            print(f"야후 spark가 답하지 않음: {type(error).__name__}", file=sys.stderr)
    return found


def bars(response: dict, before: dt.datetime | None = None) -> tuple[float, str] | None:
    """spark 응답에서 `before` 전에 시작한 마지막 1분봉의 (종가, 봉 시각 ISO). 봉이 없으면 None.

    야후는 끝나지 않은 마지막 봉에 그 봉의 마지막 체결 시각을 붙이므로, 봉 시각을 체결 시각으로 쓴다.
    """
    closes = (response.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    for stamp, close in reversed(list(zip(response.get("timestamp") or [], closes))):
        began = dt.datetime.fromtimestamp(stamp, NEW_YORK)
        if close is not None and (before is None or began < before):
            return close, began.isoformat()
    return None


def public_prices(symbols: list[str], toss: Toss | None = None) -> dict[str, tuple[float, str | None]]:
    """심볼마다 (마지막 체결가, 체결 시각 ISO 또는 None). 토스를 한 번 부르고, 토스가 답하지 않거나 빠뜨린 심볼만 야후에서 받는다.

    토스가 체결 시각 없이 준 심볼은 시각을 None으로 두고 야후에 묻지 않는다. 두 출처 모두 답하지 않은 심볼은 빠진다.
    """
    toss = toss or Toss()
    found = {}
    try:
        answer = toss.get("/api/v1/prices", {"symbols": ",".join(toss_symbol(symbol) for symbol in symbols)})
        given = {item["symbol"]: item for item in answer or []}
        for symbol in symbols:
            item = given.get(toss_symbol(symbol))
            if item and item.get("lastPrice") not in (None, ""):
                found[symbol] = (float(item["lastPrice"]), item.get("timestamp") or None)
    except (requests.RequestException, RuntimeError, ValueError, KeyError) as error:
        print(f"토스 시세가 답하지 않음: {type(error).__name__}", file=sys.stderr)
    rest = [symbol for symbol in symbols if symbol not in found]
    toss.yahoo += len(rest)
    for symbol, response in spark(rest, includePrePost="true").items():
        if trade := bars(response):
            found[symbol] = trade
    return found


def close_trades(symbols: list[str], closed: dt.datetime, toss: Toss) -> dict[str, tuple[float, str]]:
    """심볼마다 정규장 마감 시각까지 끝난 마지막 1분봉의 (종가, 체결 끝 시각 ISO). 토스 1분봉에서, 답하지 않은 심볼은 야후에서 받는다.

    토스 1분봉의 시각은 봉이 끝나는 시각이다. 그래서 마감 시각이 붙은 봉이 마감 경매 체결까지 담은 마지막 봉이다.
    """
    found = {}
    for symbol in symbols:
        try:
            page = toss.get("/api/v1/candles", {"symbol": toss_symbol(symbol), "interval": "1m", "count": 1, "before": closed.isoformat()})
            if candles := page.get("candles"):
                found[symbol] = (float(candles[0]["closePrice"]), dt.datetime.fromisoformat(candles[0]["timestamp"]).isoformat())
        except (requests.RequestException, RuntimeError, ValueError, KeyError) as error:
            print(f"토스 1분봉이 답하지 않음: {type(error).__name__}", file=sys.stderr)
        time.sleep(CANDLE_WAIT)
    for symbol, response in spark([symbol for symbol in symbols if symbol not in found], includePrePost="true").items():
        if trade := bars(response, closed):
            found[symbol] = trade
    return found


def base_closes(session: str, toss: Toss) -> dict[str, float]:
    """지수 ETF마다 앞 세션 정규장 종가. 토스 일봉에서, 답하지 않은 ETF는 야후 일봉에서 받는다."""
    found = {}
    for etf in sorted(set(SECTOR_DB_TICKERS.values())):
        try:
            page = toss.get("/api/v1/candles", {"symbol": toss_symbol(etf), "interval": "1d", "count": 5})
            for candle in page.get("candles") or []:
                if candle["timestamp"][:10] == session:
                    found[etf] = float(candle["closePrice"])
        except (requests.RequestException, RuntimeError, ValueError, KeyError) as error:
            print(f"토스 일봉이 답하지 않음: {type(error).__name__}", file=sys.stderr)
    for etf, response in spark([etf for etf in sorted(set(SECTOR_DB_TICKERS.values())) if etf not in found], range="5d", interval="1d").items():
        closes = (response.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
        for stamp, close in zip(response.get("timestamp") or [], closes):
            if close is not None and dt.datetime.fromtimestamp(stamp, NEW_YORK).date().isoformat() == session:
                found[etf] = float(close)
    return found


def calendar_day(day: dt.date) -> dict:
    """뉴욕 날짜 `day`의 장 운영. 세션이면 앞 세션 날짜(`session`)와 정규장 마감 시각(`closed`)이다. 세션마다 한 번 받아 파일에 둔다."""
    path = DATA / f"session-{day}.json"
    if path.exists():
        return load(path, {})
    xnys = exchange_calendars.get_calendar("XNYS")
    found = {"date": day.isoformat(), "open": bool(xnys.is_session(day.isoformat()))}
    if found["open"]:
        found["session"] = xnys.previous_session(day.isoformat()).date().isoformat()
        found["closed"] = xnys.session_close(day.isoformat()).to_pydatetime().astimezone(NEW_YORK).isoformat()
    DATA.mkdir(parents=True, exist_ok=True)
    save(path, found)
    edge = (day - dt.timedelta(days=KEEP_DAYS)).isoformat()
    for old in DATA.iterdir():
        stem = old.name.split("-", 1)
        if stem[0] in ("session", "tick", "snap") and len(stem) > 1 and stem[1][:10] < edge:
            old.unlink()
    return found


def rounds(now: dt.datetime, day: dict, kept: dict[str, dict]) -> dict[str, tuple[dt.datetime, str]]:
    """이번 회차에 쓸 값 이름마다 (끝 시각, 구간). 구간은 프리장 `pre`, 정규장 `regular`, 마감 고정 `close`, 애프터장 `after`다."""
    if not day["open"] or now.time() < PREMARKET_OPEN:
        return {}
    today, minute = now.date(), now.replace(second=0, microsecond=0)
    closed = dt.datetime.fromisoformat(day["closed"])
    written = lambda name: {kept[name].get(index, {}).get(today.isoformat(), {}).get("time") for index in SECTOR_DB_TICKERS}
    due = {}
    if now < closed:
        due["premarket"] = (minute, "regular" if minute > dt.datetime.combine(today, PREMARKET_CLOSE, NEW_YORK) else "pre")
    elif now >= closed + CLOSE_WAIT and written("premarket") != {closed.isoformat()}:
        due["premarket"] = (closed, "close")
    if now >= max(dt.datetime.combine(today, AFTER_OPEN, NEW_YORK), closed + CLOSE_WAIT):
        end = min(minute, dt.datetime.combine(today, AFTER_CLOSE, NEW_YORK))
        if written("afterhours") != {end.isoformat()}:
            due["afterhours"] = (end, "after")
    return due


def public_board() -> dict:
    """원격 main의 `r/market.json` 지도. 게시 worktree가 받는 원격 참조를 한 번에 읽어 게시 중인 파일과 섞이지 않는다."""
    shown = subprocess.run(["git", "-C", str(ROOT), "show", "origin/main:r/market.json"], capture_output=True, text=True, check=True)
    return json.loads(shown.stdout)["map"]


def holding_symbols() -> list[str]:
    """보유 종목 심볼. 파일이 없으면 빈 목록이다."""
    return load(HOLDINGS, [])


def post_account(now: dt.datetime, prices: dict[str, float]) -> None:
    """invest-account Worker의 DO에 보유 종목 체결가를 `POST /live`로 덮어쓴다. 비밀 값은 ~/.cloudflare_env의 `ACCOUNT_SECRET`으로만 받는다.

    Worker가 204를 답하지 않으면 RuntimeError를 낸다.
    """
    if not os.environ.get("ACCOUNT_SECRET"):
        raise EnvironmentError("환경변수 없음: ACCOUNT_SECRET")
    answer = requests.post(f"{ACCOUNT_URL}/live", json={"time": now.isoformat(timespec="seconds"), "prices": prices}, timeout=TIMEOUT,
                           headers={"X-Account-Secret": os.environ["ACCOUNT_SECRET"], "User-Agent": "invest-reports"})
    if answer.status_code != 204:
        raise RuntimeError(f"invest-account 쓰기 실패: {answer.status_code}")


def priced(trade: tuple[float, str | None] | None, start: dt.datetime) -> float | None:
    """`start` 뒤에 난 체결의 가격. 체결 시각이 없거나 `start` 전이면 None."""
    return trade[0] if trade and trade[1] and dt.datetime.fromisoformat(trade[1]) > start else None


def assemble(kept: dict, board: dict, trades: dict, end: dt.datetime, span: str, day: dict, base: dict[str, float] | None = None) -> dict:
    """`kept`의 오늘 값을 `trades`로 갈아 새 값을 돌려준다. `span`이 `after`면 `afterhours`, 아니면 `premarket` 값이다.

    `base`는 `afterhours` 비율의 분모인 지수마다 오늘 정규장 ETF 종가다(`{지수: 종가}`).
    """
    today = end.date().isoformat()
    closed = dt.datetime.fromisoformat(day["closed"])
    start = closed if span == "after" else dt.datetime.combine(end.date(), PREMARKET_OPEN, NEW_YORK)
    phase = {"pre": "pre", "regular": "regular", "close": "regular", "after": None}[span]
    for index, found in board.items():
        own = kept.setdefault(index, {})
        before = own.get(today)
        same = before if before and before.get("phase") == phase else None
        etf, under = SECTOR_DB_TICKERS[index], (base or {}).get(index) if span == "after" else day.get("base", {}).get(SECTOR_DB_TICKERS[index])
        ratio = (price := priced(trades.get(etf), start)) and under and round(price / under, 6)
        value = {"time": end.isoformat(),
                 "ratio": ratio if ratio is not None else (same or {}).get("ratio"),
                 "stocks": {stock["symbol"]: (round(price, 2) if (price := priced(trades.get(stock["symbol"]), start)) is not None
                                              else (same or {}).get("stocks", {}).get(stock["symbol"])) for stock in found["stocks"]}}
        if phase:
            value = {"session": day["session"], "time": value["time"], "phase": phase, "ratio": value["ratio"], "stocks": value["stocks"]}
            dawn = before and (before.get("pre") if before.get("phase") == "regular" else {name: before[name] for name in ("time", "ratio", "stocks")})
            if phase == "regular" and dawn:
                value["pre"] = dawn
        own[today] = value
        for old in [old for old in own if old < found["dates"][0]]:
            del own[old]
    return kept


def tick(now: dt.datetime | None = None) -> dict[str, dict]:
    """1분 회차. 장 시간 판정, 일괄 조회, 값 조립, invest-live 쓰기, invest-account 쓰기를 차례로 부르고, invest-live에 쓴 값을 이름마다 돌려준다."""
    now = now or dt.datetime.now(NEW_YORK)
    day = calendar_day(now.date())
    kept = {name: load(DATA / f"{name}.json", {}) for name in NAMES}
    due = rounds(now, day, kept)
    if not due:
        return {}
    toss, board = Toss(), public_board()
    if "base" not in day:
        day["base"] = base_closes(day["session"], toss)
        save(DATA / f"session-{now.date()}.json", day)
    public = sorted({stock["symbol"] for found in board.values() for stock in found["stocks"]} | set(SECTOR_DB_TICKERS.values()))
    held = holding_symbols()
    trades = public_prices(sorted(set(public) | set(held)), toss)
    if not any(symbol in trades for symbol in public):
        raise RuntimeError("토스와 야후 모두 체결가를 주지 않음")
    written = {}
    if "premarket" in due:
        end, span = due["premarket"]
        use = close_trades(public, end, toss) if span == "close" else trades
        written["premarket"] = assemble(kept["premarket"], board, use, end, span, day)
    if "afterhours" in due:
        end, span = due["afterhours"]
        today = now.date().isoformat()
        closes = {index: ratio * day["base"][etf] for index, etf in SECTOR_DB_TICKERS.items()
                  if (ratio := kept["premarket"].get(index, {}).get(today, {}).get("ratio")) and day["base"].get(etf)}
        written["afterhours"] = assemble(kept["afterhours"], board, trades, end, span, day, closes)
    for name, value in written.items():
        build.post_live(name, value)
        save(DATA / f"{name}.json", value)
        with open(DATA / f"snap-{now.date()}.jsonl", "a", encoding="utf-8") as snaps:
            for index, days in value.items():
                snaps.write(json.dumps({"name": name, "index": index, **days[now.date().isoformat()]}, separators=(",", ":")) + "\n")
    if prices := {symbol: trades[symbol][0] for symbol in held if symbol in trades}:
        post_account(now, prices)
    record = {"at": now.isoformat(timespec="seconds"), "wrote": sorted(written), "calls": toss.calls,
              "yahoo": toss.yahoo,
              "null": {name: sum(price is None for days in value.values() for price in days[now.date().isoformat()]["stocks"].values())
                       for name, value in written.items()}}
    with open(DATA / f"tick-{now.date()}.log", "a", encoding="utf-8") as log:
        log.write(json.dumps(record, separators=(",", ":")) + "\n")
    os.chmod(DATA / f"snap-{now.date()}.jsonl", 0o600)
    return written


def main() -> int:
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    print(" ".join(tick()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
