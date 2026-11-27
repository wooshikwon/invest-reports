#!/usr/bin/env python3
"""live.py — 1분마다 공개 종목의 마지막 체결가와 지수 값을 invest-live Worker의 DO에 쓴다.

cron(`~/scripts/cron/invest-live-tick.sh`)이 1분마다 `tick()`을 부른다. 회차마다 장 시간을 판정하고, 토스 `GET /api/v1/prices`를 한 번 불러
공개 종목과 보유 종목의 마지막 체결가를 받고, `premarket`·`afterhours` 값을 조립해 `POST /write/{이름}`으로 쓴다.
공개 종목은 `r/market.json` 지도 종목과 지수 ETF(`SECTOR_DB_TICKERS`)다. 보유 종목은 `~/data/invest-account/holdings.json`(심볼만)에서 읽고,
그 체결가는 invest-live에 쓰지 않고 invest-account Worker의 DO에 `POST /live`로만 쓴다. 보유하지 않은 기준 묶음 ETF의 체결가와 선물 추정에 쓰는 배율도
`~/data/invest-account/etfs.json`(account_push가 쓰는 비공개 파일)에서 읽어 같은 길로만 쓴다. 토스가 답하지 않거나 빠뜨린 심볼만 야후 `v7/finance/spark`에서 받는다.
토스가 체결 시각 없이 준 심볼은 체결이 없는 것으로 보고 야후에 묻지 않는다. 토큰은 toss-trader와 함께 쓰는 캐시 파일만 쓴다.

값의 스키마는 build.py 머리 설명의 `premarket`·`afterhours`·`index` 값과 같다. `premarket`은 프리장(`PREMARKET_OPEN`)부터 정규장이 닫힐 때까지 1분마다 그 분의 값을 쓰고,
정규장이 닫히고 `CLOSE_WAIT`가 지난 첫 회차가 그날 일봉의 공식 종가로 마감 값을 한 번 더 받아 고정한다.
`afterhours`는 `AFTER_OPEN`과 마감 고정 회차 가운데 늦은 쪽부터 `AFTER_CLOSE`까지 1분마다 쓴다.
체결가는 `premarket`이면 오늘 `PREMARKET_OPEN` 뒤, `afterhours`이면 오늘 정규장 마감 뒤 체결만 쓴다. 그 체결이 없으면 앞 회차 값을 두고,
앞 회차 값도 없으면 null이다. 지도의 첫 날짜보다 앞선 날짜의 값은 지운다.
지수 값마다 날짜 지점(`point`)을 적는다. 날짜 지점은 뉴욕 세션 날짜이고, `premarket` 값은 그 세션, `afterhours` 값은 XNYS 달력의 다음 세션이다.

앞 세션 `AFTER_CLOSE`부터 다음 세션 `PREMARKET_OPEN` 전까지가 선물 시간대(`futures`)다. 날짜 지점 하나는 애프터장, 선물 시간대, 프리장, 정규장 순서로 값을 받는다.
선물 시간대 지수 값: 나스닥 선물(`FUTURES`)이 애프터장 마지막 체결 뒤 새로 체결되면, 앞 세션의 나스닥 `afterhours` 값에
선물 시간대 값 `futures`(`time`, `ratio`)를 붙인다. 비율은 애프터장 마지막 비율 × (선물 마지막 체결가 ÷ 애프터장 마지막 체결 시각까지 끝난 선물 1분봉 종가)이다.
선물 마지막 체결은 끝난 마지막 1분봉의 종가(시각은 그 봉이 끝난 시각)와 야후 응답 `meta`의 마지막 체결(`regularMarketPrice`, `regularMarketTime`) 가운데 늦은 쪽이다.
야후는 미국 휴장일에 선물 1분봉을 주지 않고 `meta`의 마지막 체결만 갈아 준다. 선물 시장이 닫힌 주말에는 새 체결이 없으므로 쓰지 않는다.
애프터장 마지막 비율과 그 시각의 선물 종가는 선물 시간대 첫 회차에 `futures-{앞 세션}.json`에 둔다. 바이오에는 선물이 없어 `futures`를 붙이지 않는다.
선물 시간대 종목 값: 같은 회차가 토스 시세를 한 번 불러 지도 종목과 보유 종목의 주간거래(블루오션) 체결가를 받는다. 앞 세션 `AFTER_CLOSE` 뒤 체결이 있는
종목이 있으면 두 지수의 `afterhours` 값에 주간거래 값 `overnight`(`time`, `stocks`)를 붙인다. `stocks`는 종목마다 그 뒤 마지막 체결가이고, 체결이 없는
종목은 앞 회차 값을 두며 앞 회차 값도 없으면 null이다. `time`은 그 체결 가운데 가장 늦은 체결 시각이다.
계좌 가격도 같은 체결가로 invest-account에 쓴다. 앞 세션 `AFTER_CLOSE` 뒤 체결이 있는 보유 종목은 그 체결가를, 없는 종목은 앞 회차가 쓴 가격을 쓰고,
그 시각은 보유 종목 체결 가운데 가장 늦은 체결 시각이다. 보유 종목에 그 뒤 체결이 하나도 없거나 가격이 앞 회차와 같으면 쓰지 않는다.
장 밖과 휴장일 가운데 선물 시간대가 아닌 회차, 마감 뒤 `CLOSE_WAIT` 안, 그날 값을 이미 다 받은 회차는 아무것도 부르지 않고 끝난다.

회차마다 지수(`INDEX_SYMBOLS`)를 야후 spark 묶음 요청 한 번으로 받는다. 선물 시간대에는 선물 심볼도 같은 묶음에 넣는다.
`index` 값에는 지수마다 마지막 1분봉의 가격과 시각, 그 1분봉을 처음 받은 시각(`loaded`)을 적고, 1분봉 시각이 바뀐 회차에만 쓴다.
`premarket`의 정규장 값에는 ^NDX·^NBI의 그날 정규장 1분봉 종가로 만든 시가·고가·저가·종가를 앞 세션 지수 종가 대비 비율(`ohlc`)로 적고,
지도 종목마다 그날 정규장의 시가·고가·저가(`bars`, 정규장 첫 회차 체결가와 회차마다 받은 체결가의 최고·최저)를 적는다.

앞 세션·다음 세션 날짜와 정규장 마감 시각은 날짜마다 한 번 `exchange_calendars`에서, 지수 ETF의 앞 세션 종가는 그 세션의 첫 장중 회차에 토스 일봉에서 받아
`~/data/invest-reports/live/session-{YYYY-MM-DD}.json`에 둔다. 애프터장 회차는 나스닥 ETF의 마지막 체결 시각도 같은 파일에 둔다.
앞 회차 값은 DO에 쓴 값과 같은 `{이름}.json`에 두고 다시 읽는다. invest-account에 쓴 계좌 가격은 `account-sent.json`에, 마감 회차가 받은 보유 종목과 기준 묶음 ETF의 공식 종가는 `account-close.json`에 둔다.
계좌 가격은 이번 구간(프리장·정규장이면 그날 `PREMARKET_OPEN`, 애프터장이면 정규장 마감) 뒤 체결이 없는 종목에 앞 회차가 쓴 가격을 이어 쓴다.
회차마다 가격 없는 기록(`tick-{날짜}.log`)과, DO에 쓴 그날 값(`snap-{날짜}.jsonl`)을 남긴다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import functools
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
from build import AFTER_CLOSE, AFTER_OPEN, NEW_YORK, OIL_TICKER, PREMARKET_CLOSE, PREMARKET_OPEN, ROOT

sys.path.insert(0, str(Path.home() / "obsidian-vault/agent/skills/tool/invest-report/scripts"))
from path_bands import SECTOR_DB_TICKERS, SECTOR_INDEX_TICKERS  # noqa: E402  지수마다의 지수 ETF와 지수 심볼

DATA = Path.home() / "data" / "invest-reports" / "live"
HOLDINGS = Path.home() / "data" / "invest-account" / "holdings.json"  # account_push가 쓰는 보유 종목 심볼 목록(0600)
ETFS = Path.home() / "data" / "invest-account" / "etfs.json"  # account_push가 쓰는 지수마다 ETF와 배율(0600). 종목과 배율은 공개 저장소에 두지 않는다
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
CANDLE_WAIT = 0.05  # 토스 일봉을 이어 부를 때 사이를 띄우는 초. 차트 조회는 초당 20회까지 받는다
# 초당 상한은 같은 자격증명을 쓰는 toss-trader·판단 배치와 함께 센다. 그래서 429로 거절된 조회는 `RETRY_WAIT`초 뒤 `ATTEMPTS`번까지 부른다.
RETRY_WAIT = 2
ATTEMPTS = 3
CLOSE_WAIT = dt.timedelta(minutes=5)  # 마감 경매의 공식 종가가 일봉에 실리기를 기다리는 시간
KEEP_DAYS = 7  # `DATA`의 날짜 붙은 파일을 남기는 날 수
NAMES = ("premarket", "afterhours", "index")
INDEX_SYMBOLS = (*SECTOR_INDEX_TICKERS.values(), OIL_TICKER)  # `index` 값에 적는 야후 심볼
FUTURES = {"nasdaq": "NQ=F"}  # 선물 시간대에 애프터장 값을 바꾸는 지수와 그 선물의 야후 심볼


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
    """토스 Open API 조회. 부른 횟수를 경로마다 세고(`calls`), 야후로 넘긴 심볼 수(`yahoo`)와 지수 spark 묶음 요청 수(`index`)를 센다."""

    def __init__(self):
        self.calls = {"prices": 0, "candles": 0}
        self.yahoo = 0
        self.index = 0  # 지수 spark 묶음 요청 수
        self.night = False  # 선물 시간대 회차면 참이다

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


def ended(response: dict, moment: dt.datetime) -> tuple[int, float] | None:
    """spark 응답에서 `moment`까지 끝난 마지막 1분봉의 (봉 시작 시각 초, 종가). 봉이 없으면 None."""
    closes = (response.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    found = [(stamp, close) for stamp, close in zip(response.get("timestamp") or [], closes) if close is not None and stamp <= moment.timestamp() - 60]
    return found[-1] if found else None


def traded_last(response: dict, moment: dt.datetime) -> tuple[int, float] | None:
    """spark 응답에서 `moment`까지의 마지막 체결 (체결 시각 초, 체결가). 체결이 없으면 None.

    끝난 마지막 1분봉의 (끝난 시각, 종가)와 `meta`의 마지막 체결(`regularMarketTime`, `regularMarketPrice`) 가운데 늦은 쪽이다.
    """
    meta = response.get("meta") or {}
    found = [(bar[0] + 60, bar[1])] if (bar := ended(response, moment)) else []
    if meta.get("regularMarketTime") and meta.get("regularMarketPrice") is not None and meta["regularMarketTime"] <= moment.timestamp():
        found.append((meta["regularMarketTime"], meta["regularMarketPrice"]))
    return max(found) if found else None


def index_value(kept: dict, quotes: dict[str, dict], now: dt.datetime) -> dict | None:
    """`kept`의 `index` 값에서 마지막 1분봉 시각이 바뀐 지수만 갈아 새 값을 돌려준다. 바뀐 지수가 없으면 None."""
    value = dict(kept)
    for symbol in INDEX_SYMBOLS:
        if (last := bars(quotes.get(symbol) or {})) and (kept.get(symbol) or {}).get("time") != last[1]:
            value[symbol] = {"price": round(last[0], 2), "time": last[1], "loaded": now.isoformat(timespec="seconds")}
    return value if value != kept else None


def session_ohlc(quotes: dict[str, dict], opened: dt.datetime, end: dt.datetime) -> dict[str, dict]:
    """지수마다 `opened`부터 `end`까지 시작한 1분봉 종가의 시가·고가·저가·종가를 앞 세션 지수 종가로 나눈 비율.

    spark는 1분봉 종가만 주므로 네 값을 종가에서 고른다. 앞 세션 지수 종가는 하루치 응답의 `chartPreviousClose`다.
    그날 정규장 1분봉이 없거나 야후가 답하지 않은 지수는 빠진다.
    """
    found = {}
    for index, symbol in SECTOR_INDEX_TICKERS.items():
        response = quotes.get(symbol) or {}
        closes = [close for stamp, close in zip(response.get("timestamp") or [], (response.get("indicators", {}).get("quote") or [{}])[0].get("close") or [])
                  if close is not None and opened <= dt.datetime.fromtimestamp(stamp, NEW_YORK) <= end]
        if closes and (base := response.get("meta", {}).get("chartPreviousClose")):
            found[index] = {name: round(price / base, 6) for name, price in
                            (("open", closes[0]), ("high", max(closes)), ("low", min(closes)), ("close", closes[-1]))}
    return found


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


def session_closes(symbols: list[str], session: str, toss: Toss) -> dict[str, float]:
    """심볼마다 `session` 정규장 공식 종가. 토스 일봉에서, 답하지 않은 심볼은 야후 일봉에서 받는다.

    일봉 종가는 마감 경매에서 정해지는 공식 종가다.
    """
    found = {}
    for symbol in symbols:
        try:
            page = toss.get("/api/v1/candles", {"symbol": toss_symbol(symbol), "interval": "1d", "count": 5})
            for candle in page.get("candles") or []:
                if candle["timestamp"][:10] == session:
                    found[symbol] = float(candle["closePrice"])
        except (requests.RequestException, RuntimeError, ValueError, KeyError) as error:
            print(f"토스 일봉이 답하지 않음: {type(error).__name__}", file=sys.stderr)
        time.sleep(CANDLE_WAIT)
    for symbol, response in spark([symbol for symbol in symbols if symbol not in found], range="5d", interval="1d").items():
        closes = (response.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
        for stamp, close in zip(response.get("timestamp") or [], closes):
            if close is not None and dt.datetime.fromtimestamp(stamp, NEW_YORK).date().isoformat() == session:
                found[symbol] = float(close)
    return found


@functools.cache
def xnys():
    return exchange_calendars.get_calendar("XNYS")


def next_session(day: str) -> str:
    """뉴욕 날짜 `day` 뒤의 첫 세션 날짜."""
    return xnys().date_to_session((dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat(), "next").date().isoformat()


def calendar_day(day: dt.date) -> dict:
    """뉴욕 날짜 `day`의 장 운영. 날짜마다 한 번 받아 파일에 둔다.

    `session`은 `day` 전의 마지막 세션, `next`는 `day` 뒤의 첫 세션 날짜다. 세션이면 정규장 마감 시각(`closed`)도 적는다.
    """
    path = DATA / f"session-{day}.json"
    found = load(path, {})
    if "next" in found:
        return found
    found.update({"date": day.isoformat(), "open": bool(xnys().is_session(day.isoformat())),
                  "session": xnys().date_to_session((day - dt.timedelta(days=1)).isoformat(), "previous").date().isoformat(),
                  "next": next_session(day.isoformat())})
    if found["open"]:
        found["closed"] = xnys().session_close(day.isoformat()).to_pydatetime().astimezone(NEW_YORK).isoformat()
    DATA.mkdir(parents=True, exist_ok=True)
    save(path, found)
    edge = (day - dt.timedelta(days=KEEP_DAYS)).isoformat()
    for old in DATA.iterdir():
        stem = old.name.split("-", 1)
        if stem[0] in ("session", "tick", "snap", "futures") and len(stem) > 1 and stem[1][:10] < edge:
            old.unlink()
    return found


def futures_window(now: dt.datetime, day: dict) -> tuple[str, str] | None:
    """`now`가 선물 시간대이면 (앞 세션, 다음 세션) 날짜. 아니면 None. 선물 시간대는 앞 세션 `AFTER_CLOSE`부터 다음 세션 `PREMARKET_OPEN` 전까지다."""
    if not day["open"]:
        return day["session"], day["next"]
    if now.time() >= AFTER_CLOSE:
        return day["date"], day["next"]
    if now.time() < PREMARKET_OPEN:
        return day["session"], day["date"]
    return None


def rounds(now: dt.datetime, day: dict, kept: dict[str, dict]) -> dict[str, tuple[dt.datetime, str]]:
    """이번 회차에 쓸 값 이름마다 (끝 시각, 구간). 구간은 프리장 `pre`, 정규장 `regular`, 마감 고정 `close`, 애프터장 `after`, 선물 시간대 `futures`다.

    선물 시간대 구간은 그날 애프터장 마지막 값을 받은 뒤에만 든다.
    """
    minute = now.replace(second=0, microsecond=0)
    futures = {"afterhours": (minute, "futures")} if futures_window(now, day) else {}
    if not day["open"] or now.time() < PREMARKET_OPEN:
        return futures
    today = now.date()
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
    return due or futures


def futures_base(before: str, kept: dict, quotes: dict[str, dict]) -> dict:
    """선물 시간대의 기준. 지수마다 앞 세션 `before`의 애프터장 마지막 비율(`ratio`)과, 애프터장 마지막 체결 시각까지 끝난
    선물 1분봉의 (봉 시작 시각 초, 종가)(`base`)다.

    선물 시간대 첫 회차에 `futures-{before}.json`에 두고 다시 읽는다. 야후가 선물 1분봉을 주지 않은 회차는 파일을 두지 않아 다음 회차가 다시 받는다.
    애프터장 비율이나 체결 시각, 그때까지의 선물 1분봉이 없는 지수는 빠진다.
    """
    path = DATA / f"futures-{before}.json"
    if path.exists():
        return load(path, {})
    if not all((quotes.get(symbol) or {}).get("timestamp") for symbol in FUTURES.values()):
        return {}
    traded = load(DATA / f"session-{before}.json", {}).get("trade", {})
    found = {}
    for index, symbol in FUTURES.items():
        ratio = kept.get(index, {}).get(before, {}).get("ratio")
        if ratio and traded.get(index) and (base := ended(quotes[symbol], dt.datetime.fromisoformat(traded[index]))):
            found[index] = {"ratio": ratio, "base": list(base)}
    save(path, found)
    return found


def futures_value(kept: dict, base: dict, quotes: dict[str, dict], end: dt.datetime, before: str) -> dict | None:
    """선물 시간대의 `afterhours` 새 값. 선물이 `base` 봉 뒤 새로 체결된 지수만 앞 세션 `before`의 값에 `futures`를 붙이거나 갈아 돌려준다.

    `futures`의 `ratio`는 애프터장 마지막 비율 × (`end`까지의 선물 마지막 체결가(`traded_last`) ÷ 기준 종가)이고, `time`은 그 체결 시각이다.
    야후는 요청마다 앞선 체결을 답하기도 하므로, 이미 쓴 `futures`의 시각보다 늦은 체결만 쓴다. 애프터장 값 자체는 바꾸지 않는다. 갈 지수가 없으면 None.
    """
    changed = False
    for index, symbol in FUTURES.items():
        own = kept.get(index, {}).get(before)
        last = traded_last(quotes.get(symbol) or {}, end)
        if not (own and index in base and last and last[0] > base[index]["base"][0] + 60):
            continue
        moved = dt.datetime.fromtimestamp(last[0], NEW_YORK).isoformat()
        if (shown := own.get("futures", {}).get("time")) is None or dt.datetime.fromisoformat(shown).timestamp() < last[0]:
            own["futures"] = {"time": moved, "ratio": round(base[index]["ratio"] * last[1] / base[index]["base"][1], 6)}
            changed = True
    return kept if changed else None


def public_board() -> dict:
    """원격 main의 `r/market.json` 지도. 게시 worktree가 받는 원격 참조를 한 번에 읽어 게시 중인 파일과 섞이지 않는다."""
    shown = subprocess.run(["git", "-C", str(ROOT), "show", "origin/main:r/market.json"], capture_output=True, text=True, check=True)
    return json.loads(shown.stdout)["map"]


def holding_symbols() -> list[str]:
    """보유 종목 심볼. 파일이 없으면 빈 목록이다."""
    return load(HOLDINGS, [])


def etf_table() -> dict[str, dict[str, float]]:
    """지수마다 {ETF 심볼: 배율}. 파일이 없으면 빈 값이다."""
    return load(ETFS, {})


def overnight_value(kept: dict, board: dict, trades: dict[str, tuple[float, str | None]], start: dt.datetime, before: str) -> dict | None:
    """선물 시간대의 `afterhours` 새 값. 지수마다 앞 세션 `before`의 값에 주간거래 값 `overnight`(`time`, `stocks`)를 붙이거나 갈아 돌려준다.

    `stocks`는 지도 종목마다 `start`(앞 세션 `AFTER_CLOSE`) 뒤 마지막 체결가이고, 그 뒤 체결이 없으면 앞 회차 값, 그것도 없으면 null이다.
    `time`은 그 뒤 체결 가운데 가장 늦은 체결 시각이다. 앞 세션 값이 없거나 그 뒤 체결이 없거나 값이 그대로인 지수는 갈지 않는다. 간 지수가 없으면 None.
    """
    changed = False
    for index, found in board.items():
        own = kept.get(index, {}).get(before)
        times = [trades[stock["symbol"]][1] for stock in found["stocks"] if priced(trades.get(stock["symbol"]), start) is not None]
        if not own or not times:
            continue
        held = (own.get("overnight") or {}).get("stocks", {})
        value = {"time": max(dt.datetime.fromisoformat(moment) for moment in times).astimezone(NEW_YORK).isoformat(),
                 "stocks": {stock["symbol"]: (round(price, 2) if (price := priced(trades.get(stock["symbol"]), start)) is not None
                                              else held.get(stock["symbol"])) for stock in found["stocks"]}}
        if own.get("overnight") != value:
            own["overnight"] = value
            changed = True
    return kept if changed else None


def account_prices(held: list[str], trades: dict[str, tuple[float, str | None]], sent: dict[str, float], start: dt.datetime) -> dict[str, float]:
    """보유 종목마다 invest-account에 쓸 가격. 이번 구간 시작(`start`) 뒤 체결이 있으면 그 체결가, 없으면 앞 회차가 invest-account에 쓴 가격(`sent`),
    그것도 없으면 마지막 체결가다. 그래서 프리장이 열린 직후 아직 체결이 없는 종목은 선물 시간대에 쓴 주간거래 가격을 이어 쓴다.
    """
    found = {}
    for symbol in held:
        if (price := priced(trades.get(symbol), start)) is not None:
            found[symbol] = price
        elif symbol in sent:
            found[symbol] = sent[symbol]
        elif symbol in trades:
            found[symbol] = trades[symbol][0]
    return found


def post_account(now: dt.datetime, prices: dict[str, float], futures: str | None = None, close: dict | None = None) -> None:
    """invest-account Worker의 DO에 보유 종목 체결가를 `POST /live`로 덮어쓴다. 비밀 값은 ~/.cloudflare_env의 `ACCOUNT_SECRET`으로만 받는다.

    선물 시간대(주간거래) 체결가이면 `futures`에 그 체결가로 대신한 애프터장의 세션 날짜를 적는다. `close`는 마지막 정규장 마감 회차가 받은 그 세션의 공식 종가
    (`{session, next, prices}`)이고, Worker는 그 세션이 아직 정산되지 않았으면 이 종가로 그 세션 점을 확정한다.

    Worker가 204를 답하지 않으면 RuntimeError를 낸다.
    """
    if not os.environ.get("ACCOUNT_SECRET"):
        raise EnvironmentError("환경변수 없음: ACCOUNT_SECRET")
    body = {"time": now.isoformat(timespec="seconds"), "prices": prices, **({"futures": futures} if futures else {}), **({"close": close} if close else {})}
    answer = requests.post(f"{ACCOUNT_URL}/live", json=body, timeout=TIMEOUT,
                           headers={"X-Account-Secret": os.environ["ACCOUNT_SECRET"], "User-Agent": "invest-reports"})
    if answer.status_code != 204:
        raise RuntimeError(f"invest-account 쓰기 실패: {answer.status_code}")


def priced(trade: tuple[float, str | None] | None, start: dt.datetime) -> float | None:
    """`start` 뒤에 난 체결의 가격. 체결 시각이 없거나 `start` 전이면 None."""
    return trade[0] if trade and trade[1] and dt.datetime.fromisoformat(trade[1]) > start else None


def assemble(kept: dict, board: dict, trades: dict, end: dt.datetime, span: str, day: dict, base: dict[str, float] | None = None,
             ohlc: dict[str, dict] | None = None) -> dict:
    """`kept`의 오늘 값을 `trades`로 갈아 새 값을 돌려준다. `span`이 `after`면 `afterhours`, 아니면 `premarket` 값이다.

    `base`는 `afterhours` 비율의 분모인 지수마다 오늘 정규장 ETF 종가다(`{지수: 종가}`). `ohlc`는 정규장 값에 적는 지수마다 시가·고가·저가·종가 비율이다.
    날짜 지점은 `premarket` 값이면 오늘, `afterhours` 값이면 다음 세션이다.
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
        value = {"point": day["next"] if span == "after" else today, "time": end.isoformat(),
                 "ratio": ratio if ratio is not None else (same or {}).get("ratio"),
                 "stocks": {stock["symbol"]: (round(price, 2) if (price := priced(trades.get(stock["symbol"]), start)) is not None
                                              else (same or {}).get("stocks", {}).get(stock["symbol"])) for stock in found["stocks"]}}
        if phase:
            value = {"session": day["session"], **value, "phase": phase}
            value = {name: value[name] for name in ("session", "point", "time", "phase", "ratio", "stocks")}
            if phase == "regular" and (candle := (ohlc or {}).get(index) or (same or {}).get("ohlc")):
                value["ohlc"] = candle
            if phase == "regular":
                # 종목마다 그날 정규장의 [시가, 고가, 저가]. 시가는 정규장 첫 회차의 체결가이고, 고가·저가는 회차마다 받은 체결가로 넓힌다.
                held = (same or {}).get("bars", {})
                value["bars"] = {symbol: ([held[symbol][0], max(held[symbol][1], price), min(held[symbol][2], price)] if symbol in held else [price, price, price])
                                 if price is not None else held[symbol] for symbol, price in value["stocks"].items() if price is not None or symbol in held}
            dawn = before and (before.get("pre") if before.get("phase") == "regular" else {name: before[name] for name in ("time", "ratio", "stocks")})
            if phase == "regular" and dawn:
                value["pre"] = dawn
        own[today] = value
        for old in [old for old in own if old < found["dates"][0]]:
            del own[old]
    return kept


def pointed(name: str, value: dict) -> dict:
    """`value`의 지수 값 가운데 날짜 지점이 없는 값에 날짜 지점을 적는다. `premarket`은 그 날짜, `afterhours`는 그 날짜 뒤 첫 세션이다."""
    for days in value.values():
        for key, own in days.items():
            if "point" not in own:
                own["point"] = key if name == "premarket" else next_session(key)
    return value


def tick(now: dt.datetime | None = None, toss: Toss | None = None) -> dict[str, dict]:
    """1분 회차. 장 시간 판정, 일괄 조회, 값 조립, invest-live 쓰기, invest-account 쓰기를 차례로 부르고, invest-live에 쓴 값을 이름마다 돌려준다.

    선물 시간대 구간 회차는 지수 묶음 요청으로 나스닥 선물 값을 붙이고, 토스 시세 한 번으로 종목의 주간거래 값을 붙이며 계좌 가격을 쓴다.
    이 회차는 `toss.night`를 켜 `main`이 계좌 요약을 부르지 않게 한다.
    계좌 가격은 invest-account에만 쓰고 invest-live에는 쓰지 않는다.
    """
    now = now or dt.datetime.now(NEW_YORK)
    toss = toss or Toss()
    day = calendar_day(now.date())
    kept = {name: load(DATA / f"{name}.json", {}) for name in NAMES}
    due = rounds(now, day, kept)
    if not due:
        return {}
    window = futures_window(now, day)
    fresh = window and not (DATA / f"futures-{window[0]}.json").exists()
    toss.index += 1
    quotes = spark([*INDEX_SYMBOLS, *(FUTURES.values() if window else ())], range="5d" if fresh else "1d")
    today = now.date().isoformat()
    keys = {"premarket": today, "afterhours": today}
    written = {}
    if due.get("afterhours", (None, ""))[1] == "futures":
        end, keys["afterhours"] = due["afterhours"][0], window[0]
        toss.night = True
        base = futures_base(window[0], kept["afterhours"], quotes)
        if futures_value(kept["afterhours"], base, quotes, end, window[0]) is not None:
            written["afterhours"] = kept["afterhours"]
        start = dt.datetime.combine(dt.date.fromisoformat(window[0]), AFTER_CLOSE, NEW_YORK)
        board = public_board()
        held = sorted({*holding_symbols(), *(etf for etfs in etf_table().values() for etf in etfs)})
        trades = public_prices(sorted({stock["symbol"] for found in board.values() for stock in found["stocks"]} | set(held)), toss)
        if overnight_value(kept["afterhours"], board, trades, start, window[0]) is not None:
            written["afterhours"] = kept["afterhours"]
        moved, sent = [dt.datetime.fromisoformat(trades[symbol][1]) for symbol in held if priced(trades.get(symbol), start) is not None], load(DATA / "account-sent.json", {})
        if moved and (prices := account_prices(held, trades, sent, start)) and prices != sent:
            post_account(max(moved).astimezone(NEW_YORK), prices, window[0], load(DATA / "account-close.json", None))
            save(DATA / "account-sent.json", prices)
    else:
        board = public_board()
        if "base" not in day:
            day["base"] = session_closes(sorted(set(SECTOR_DB_TICKERS.values())), day["session"], toss)
            save(DATA / f"session-{today}.json", day)
        public = sorted({stock["symbol"] for found in board.values() for stock in found["stocks"]} | set(SECTOR_DB_TICKERS.values()))
        held = sorted({*holding_symbols(), *(etf for etfs in etf_table().values() for etf in etfs)})
        trades = public_prices(sorted(set(public) | set(held)), toss)
        if not any(symbol in trades for symbol in public):
            raise RuntimeError("토스와 야후 모두 체결가를 주지 않음")
        if "premarket" in due:
            end, span = due["premarket"]
            use = trades
            if span == "close":
                found = session_closes(sorted(set(public) | set(held)), today, toss)
                use = {symbol: (found[symbol], end.isoformat()) for symbol in public if symbol in found}
                if closing := {symbol: found[symbol] for symbol in held if symbol in found}:
                    save(DATA / "account-close.json", {"session": today, "next": day["next"], "prices": closing})
            ohlc = session_ohlc(quotes, dt.datetime.combine(now.date(), PREMARKET_CLOSE, NEW_YORK), end) if span != "pre" else None
            written["premarket"] = assemble(kept["premarket"], board, use, end, span, day, ohlc=ohlc)
        if "afterhours" in due:
            end, span = due["afterhours"]
            closes = {index: ratio * day["base"][etf] for index, etf in SECTOR_DB_TICKERS.items()
                      if (ratio := kept["premarket"].get(index, {}).get(today, {}).get("ratio")) and day["base"].get(etf)}
            written["afterhours"] = assemble(kept["afterhours"], board, trades, end, span, day, closes)
            if found := {index: trades[SECTOR_DB_TICKERS[index]][1] for index in FUTURES
                         if priced(trades.get(SECTOR_DB_TICKERS[index]), dt.datetime.fromisoformat(day["closed"]))}:
                day["trade"] = {**day.get("trade", {}), **found}
                save(DATA / f"session-{today}.json", day)
        start = dt.datetime.fromisoformat(day["closed"]) if "afterhours" in due else dt.datetime.combine(now.date(), PREMARKET_OPEN, NEW_YORK)
        if prices := account_prices(held, trades, load(DATA / "account-sent.json", {}), start):
            post_account(now, prices, close=load(DATA / "account-close.json", None))
            save(DATA / "account-sent.json", prices)
    if (value := index_value(kept["index"], quotes, now)) is not None:
        written["index"] = value
    snap = DATA / f"snap-{today}.jsonl"
    for name, value in written.items():
        if name != "index":
            pointed(name, value)
        build.post_live(name, value)
        save(DATA / f"{name}.json", value)
        with open(snap, "a", encoding="utf-8") as snaps:
            for key, days in value.items():
                found = days if name == "index" else days.get(keys[name])
                if found:
                    snaps.write(json.dumps({"name": name, "index": key, **found}, separators=(",", ":")) + "\n")
    record = {"at": now.isoformat(timespec="seconds"), "wrote": sorted(written), "calls": toss.calls,
              "yahoo": toss.yahoo, "index": toss.index,
              "null": {name: sum(price is None for days in value.values() for price in days.get(keys[name], {}).get("stocks", {}).values())
                       for name, value in written.items() if name != "index"}}
    with open(DATA / f"tick-{today}.log", "a", encoding="utf-8") as log:
        log.write(json.dumps(record, separators=(",", ":")) + "\n")
    if snap.exists():
        os.chmod(snap, 0o600)
    return written


def main() -> int:
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    toss = Toss()
    written = tick(toss=toss)
    if sum(toss.calls.values()) and not toss.night:
        print(" ".join(written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
