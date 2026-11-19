"""골든 캡처가 미니 앱에 돌려주는 지어낸 값.

계좌 요약(`invest-account`), 실시간 값(`invest-live`의 `premarket`·`afterhours`·`progress`), 다음날 사전 리포트를 모두 여기서 만든다.
계좌 값과 신호등 값은 손으로 지어낸 상수와 고정 시드의 난수로 만들고, 실시간 체결가는 `r/market.json` 지도의 공개 종가에 종목마다 고정한 비율을 곱해 만든다.
실제 계좌, 토스, Worker, 소유자 ID는 읽지 않는다. 모든 시각은 `NOW` 하나에서 나온다.
"""
import datetime as dt
import importlib.util
import json
import math
import random
import re
import zlib
from pathlib import Path

KST = dt.timezone(dt.timedelta(hours=9))
NEW_YORK = dt.timezone(dt.timedelta(hours=-5))
# 고정 시각은 리포트 날짜 2026-11-19의 뉴욕 정규장이 열린 직후다(KST 23:45, 뉴욕 09:45). 이 시각에 20261119 리포트가 가장 늦은 리포트이고,
# 같은 세션이 열릴 때 만든 다음날 사전 리포트 20261120이 정규장 실시간 값을 그린다.
NOW = dt.datetime(2026, 11, 19, 14, 45, tzinfo=dt.timezone.utc)
TODAY = NOW.astimezone(KST).date().isoformat()
SESSION = NOW.astimezone(NEW_YORK).date().isoformat()
PREVIOUS = "2026-11-18"
PRE_KEY, PRE_DAY, BASE_KEY = "20261120-nasdaq", "2026-11-20", "20261119-nasdaq"


def account() -> dict:
    """내 자산 페이지와 거래 내역 화면이 받는 계좌 요약. 값은 모두 지어낸 값이다."""
    rng = random.Random(3)
    stamp = NOW.astimezone(KST)
    run_at = (stamp + dt.timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")

    def bell(n, mu, sd, scale=1):
        return [scale * math.exp(-((i - mu) / sd) ** 2 / 2) for i in range(n)]

    def walk(n, drift, vol):
        v, out = 0.0, []
        for _ in range(n):
            v += rng.gauss(drift, vol)
            out.append(round(v, 5))
        return out

    def days(n):
        d, out = dt.date(2026, 9, 21), []
        while len(out) < n:
            d += dt.timedelta(days=1)
            if d.weekday() < 5:
                out.append(d.isoformat())
        return out

    def perf(anchor, target, current, mu):
        n = 42
        base = walk(n, 0.0012, 0.009)
        aimed = [b + g for b, g in zip(base, walk(n, 0.0004, 0.003))]
        done = [t + g for t, g in zip(aimed, walk(n, -0.0001, 0.002))]
        return {"leverage": {"anchor": anchor, "target": target, "current": current, "low": -0.5, "high": 1.0,
                             "today": bell(61, mu, 7), "quiet": bell(61, 20, 9, 0.8)},
                "returns": {"days": days(n), "anchor": base, "target": aimed, "realized": done}}

    def item(symbol, quantity, price, average, sector):
        return {"symbol": symbol, "name": symbol, "currency": "USD", "quantity": quantity, "price": price, "average": average,
                "value": quantity * price, "purchase": quantity * average, "profit": quantity * (price - average), "rate": price / average - 1,
                "daily": quantity * price * .01, "dailyRate": .01, "sector": sector}

    def fill(symbol, side, quantity, price, day, time):
        return {"symbol": symbol, "side": side, "quantity": quantity, "price": price, "amount": round(quantity * price, 2), "at": f"{day}T{time}:00+09:00"}

    def order(symbol, side, usd, shares):
        return {"symbol": symbol, "side": side, "krw": usd * 1330.5, "usd": usd, "shares": shares}

    signal = {"date": TODAY, "sectors": {
        "nasdaq": {"color": "red",
                   "optimizer": {"color": "red", "reason": "나스닥 추종 배율 격차 0.061이 문턱 0.05를 넘었지만 필요 3일 가운데 2일만 채워 오늘 발동하지 않는다."},
                   "conditional": {"color": "green", "reason": "오늘 나스닥에 걸린 조건부 일정이 없다."}},
        "biotech": {"color": "orange",
                    "optimizer": {"color": "green", "reason": "바이오 추종 배율 격차 0.031이 문턱 0.025를 5일째 넘어 발동했다."},
                    "conditional": {"color": "orange", "reason": "FDA 자문위원회 표결 결과를 23:30 집행 때 판정한다."}}}}
    return {
        "time": stamp.strftime("%Y-%m-%dT%H:%M:00+09:00"), "rate": 1330.5,
        "accounts": {"KRW": {"cash": 152300.0, "value": 0, "purchase": 0, "profit": 0, "daily": 0},
                     "USD": {"cash": 812.44, "value": 0, "purchase": 0, "profit": 0, "daily": 0}},
        "items": [item("QQQ", 12.5, 600, 640, "nasdaq"), item("QLD", 80, 70, 40, "nasdaq"), item("TQQQ", 30, 55, 66, "nasdaq"),
                  item("IBB", 15, 200, 190, "biotech"), item("BIB", 22, 61.2, 58.4, "biotech"), item("SGOV", 40, 100.5, 100.4, "sgov")],
        "performance": {"sectors": {"nasdaq": perf(1.5, 1.82, 1.61, 38), "biotech": perf(1.0, 0.86, 0.92, 15)}},
        "trades": {"signal": signal, "time": stamp.isoformat(), "request": {"date": TODAY, "run_at": run_at, "sectors": {
            "nasdaq": {"status": "pending", "order_count": 2, "decided_at": None},
            "biotech": {"status": "pending", "order_count": 1, "decided_at": None}}},
            "sectors": {
                "nasdaq": [
                    {"date": TODAY, "sector": "nasdaq", "state": "pending", "current": 1.61, "target": 1.82, "anchor": 1.5, "run_at": run_at,
                     "reason": "금리 인하 기대가 커지고 반도체 실적 발표를 앞두고 상승 경로의 비중이 늘었다.",
                     "orders": [order("QLD", "BUY", 820.0, 11.7), order("QQQ", "SELL", 300.0, 0.5)], "fills": []},
                    {"date": PREVIOUS, "sector": "nasdaq", "state": "executed", "current": 1.48, "target": 1.61, "anchor": 1.5,
                     "reason": "고용 지표가 예상보다 약해 하락 쪽 경로가 줄었다.",
                     "orders": [order("QLD", "BUY", 610.0, 8.8)], "fills": [fill("QLD", "BUY", 8.8, 69.31, PREVIOUS, "23:31")]},
                    {"date": "2026-11-17", "sector": "nasdaq", "state": "not_required", "current": 1.49, "target": 1.48, "anchor": 1.5,
                     "reason": "", "orders": [], "fills": []},
                    {"date": "2026-11-14", "sector": "nasdaq", "state": "unfilled", "current": 1.55, "target": 1.49, "anchor": 1.5,
                     "reason": "물가 지표 발표를 앞두고 배율을 낮췄다.", "orders": [order("TQQQ", "SELL", 410.0, 7.4)], "fills": []},
                ],
                "biotech": [
                    {"date": TODAY, "sector": "biotech", "state": "pending", "current": 0.92, "target": 0.86, "anchor": 1.0, "run_at": run_at,
                     "reason": "대형 임상 결과 발표가 다음 주로 밀려 변동성이 커졌다.", "orders": [order("BIB", "SELL", 260.0, 4.2)], "fills": []},
                    {"date": "2026-11-12", "sector": "biotech", "state": "executed", "current": 0.98, "target": 0.92, "anchor": 1.0,
                     "reason": "약가 협상 대상 확대 보도로 하락 경로가 늘었다.",
                     "orders": [order("IBB", "SELL", 300.0, 1.5)], "fills": [fill("IBB", "SELL", 1.5, 199.8, "2026-11-12", "23:31")]},
                ]}},
        "decisions": None,
    }


def decide(kept: dict, body: str) -> dict:
    """`/decide`가 돌려주는 결정. 받은 결정을 `kept`(계좌 요약)의 `decisions`에 더한다."""
    asked = json.loads(body)
    answer = {"date": asked["date"], "sectors": {**((kept["decisions"] or {}).get("sectors", {})),
                                                 asked["sector"]: {"decision": asked["decision"], "at": NOW.astimezone(KST).isoformat()}}}
    kept["decisions"] = answer
    return answer


def _tilt(symbol: str, salt: str) -> float:
    """종목과 세션마다 고정한 등락 비율. -2.5%에서 +2.5% 사이다."""
    return (zlib.crc32(f"{salt}:{symbol}".encode()) % 501 - 250) / 10000


def _prices(stocks: list, n: int, salt: str) -> dict:
    out = {}
    for stock in stocks:
        close = stock["closes"][n] if n < len(stock["closes"]) else None
        out[stock["symbol"]] = None if close is None else round(close * (1 + _tilt(stock["symbol"], salt)), 2)
    return out


def live(data_root: Path) -> dict:
    """`invest-live`의 세 값. 지도의 마지막 날짜(`PREVIOUS`) 종가에 고정 비율을 곱한 체결가로 리포트 날짜(`SESSION`)의 정규장 값과
    그 앞 프리장 값, 지도 날짜의 애프터장 값을 만든다."""
    board = json.loads((data_root / "r" / "market.json").read_text(encoding="utf-8"))["map"]
    premarket, afterhours = {}, {}
    for index, found in board.items():
        n = found["dates"].index(PREVIOUS)
        pre = {"time": f"{SESSION}T09:20:00-05:00", "ratio": round(1 + _tilt(index, "pre"), 6), "stocks": _prices(found["stocks"], n, "pre")}
        premarket[index] = {SESSION: {"session": PREVIOUS, "time": f"{SESSION}T09:40:00-05:00", "phase": "regular",
                                      "ratio": round(1 + _tilt(index, "regular"), 6), "stocks": _prices(found["stocks"], n, "regular"), "pre": pre}}
        afterhours[index] = {PREVIOUS: {"time": f"{PREVIOUS}T19:50:00-05:00", "ratio": round(1 + _tilt(index, "after"), 6),
                                        "stocks": _prices(found["stocks"], n, "after")}}
    progress = {"date": PRE_DAY, "indexes": {index: {"step": 1, "since": f"{TODAY}T23:40:00+09:00"} for index in board}, "plan": [0, 20, 60, 120]}
    return {"premarket": premarket, "afterhours": afterhours, "progress": progress}


def pre_report(data_root: Path) -> dict:
    """다음날 사전 리포트 `PRE_KEY`를 v0.8 본 리포트 `BASE_KEY`로 지어 `{경로: 바이트}`로 돌려준다.

    build.py `pre`처럼 카드 JSON을 지우고 1개월 지수 방향 예측 절 본문을 비운 뒤 `pre_issues`와 `pre_indicators`를 거치고, 본 리포트 카드의
    종가 기록으로 사전 리포트 카드를 붙인다. 지표 카드 표시(`mark_indicators`)는 vault 자료가 있어야 하므로 거치지 않는다.
    목록 항목은 정규장 중에 만든 사전 리포트처럼 `stage`가 `pre`이고 `live`가 `SESSION`이다.
    """
    spec = importlib.util.spec_from_file_location("golden_build", data_root / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    body = (data_root / "r" / BASE_KEY / "report.html").read_text(encoding="utf-8")
    cards = json.loads(re.search(r'<script type="application/json" id="cards">(.*?)</script>', body, flags=re.DOTALL).group(1))
    body = re.sub(r'<script type="application/json" id="cards">.*?</script>\n?', "", body, flags=re.DOTALL)
    outlook = re.search(r'<h2 id="[^"]*">1개월 지수 방향 예측</h2>', body)
    end = body.find("<h2", outlook.end())
    body = body[:outlook.end()] + "\n" + body[end:]
    body = build.pre_indicators(build.pre_issues(body, dt.date.fromisoformat(PRE_DAY)))
    cut = cards["dates"].index(PREVIOUS) + 1
    dates, history = cards["dates"][:cut], cards["history"][:cut]
    card = {"pre": True, "dates": dates, "history": history, "day": PRE_DAY, "base_date": dates[-1], "base": history[-1]}
    body += f'<script type="application/json" id="cards">{json.dumps(card, ensure_ascii=False)}</script>\n'
    entries = json.loads((data_root / "r" / "index.json").read_text(encoding="utf-8"))
    day = dt.date.fromisoformat(PRE_DAY)
    entries[PRE_KEY] = {"title": entries[BASE_KEY]["title"], "day": f"{PRE_DAY} ({'월화수목금토일'[day.weekday()]})", "date": PRE_DAY,
                        "index": "nasdaq", "stage": "pre", "updated": f"{TODAY} 23:35",
                        "moves": {"session": None, "after": None, "close": None, "base": None}, "live": SESSION}
    listing = json.dumps(dict(sorted(entries.items(), reverse=True)), ensure_ascii=False, indent=1) + "\n"
    return {"r/index.json": listing.encode(), f"r/{PRE_KEY}/report.html": body.encode()}
