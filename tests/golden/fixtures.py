"""골든 캡처가 미니 앱에 돌려주는 지어낸 값.

계좌 요약(`invest-account`)과 실시간 값(`invest-live`의 `premarket`·`afterhours`·`progress`·`index`), 종목 뉴스 기사(`invest-news`)를 모두 여기서 만든다.
`split`은 v0.8 리포트 자료를 build.py가 지금 쓰는 모양(이슈 과거 맥락과 요약 카드 값을 `history.json`·`cards.json`으로 뺀 모양)으로 바꾼다.
계좌 값과 신호등 값은 손으로 지어낸 상수와 고정 시드의 난수로 만들고, 실시간 체결가는 `r/market.json` 지도의 공개 종가에 종목마다 고정한 비율을 곱해 만든다.
실제 계좌, 토스, Worker, 소유자 ID는 읽지 않는다. 모든 시각은 `NOW` 하나에서 나온다.
"""
import datetime as dt
import html
import json
import math
import random
import re
import zlib
from pathlib import Path

KST = dt.timezone(dt.timedelta(hours=9))
NEW_YORK = dt.timezone(dt.timedelta(hours=-5))
# 고정 시각은 리포트 날짜 2026-11-19의 뉴욕 정규장이 열린 직후다(KST 23:45, 뉴욕 09:45). 이 시각에 20261119 리포트가 가장 늦은 리포트이고,
# 그 리포트의 날짜 지점 `POINT`의 정규장 실시간 값을 그린다.
NOW = dt.datetime(2026, 11, 19, 14, 45, tzinfo=dt.timezone.utc)
TODAY = NOW.astimezone(KST).date().isoformat()
SESSION = NOW.astimezone(NEW_YORK).date().isoformat()
PREVIOUS = "2026-11-18"
BASE_KEY = "20261119-nasdaq"


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


POINT = "2026-11-19"
# 시점 이름 → (고정 시각 UTC, 그 시각의 실시간 값). 값은 모두 지어낸 값이다.
MOMENTS = {
    "after": dt.datetime(2026, 11, 19, 1, 0, tzinfo=dt.timezone.utc),
    "futures": dt.datetime(2026, 11, 19, 9, 0, tzinfo=dt.timezone.utc),
    "pre": dt.datetime(2026, 11, 19, 13, 30, tzinfo=dt.timezone.utc),
    "regular": NOW,
    "closed": dt.datetime(2026, 11, 19, 22, 0, tzinfo=dt.timezone.utc),
}


def live(data_root: Path, moment: str = "regular") -> dict:
    """`invest-live`의 값. 지도의 마지막 날짜(`PREVIOUS`) 종가에 고정 비율을 곱한 체결가로 `moment` 시점까지 쌓인 날짜 지점 `POINT`의 값을 만든다.

    `after`는 애프터마켓만, `futures`는 선물 창(나스닥만 `basis: futures`), `pre`는 프리마켓, `regular`는 정규장 진행 중(`phase: regular`, 진행 봉 `ohlc`),
    `closed`는 장 마감 뒤(마지막 봉)다. 지수 값 `index`는 지어낸 값이고 `loaded`는 그 시각 직전이다."""
    board = json.loads((data_root / "r" / "market.json").read_text(encoding="utf-8"))["map"]
    at = MOMENTS[moment]
    ny = lambda t: t.astimezone(NEW_YORK).strftime("%Y-%m-%dT%H:%M:00-05:00")
    premarket, afterhours = {}, {}
    for index, found in board.items():
        n = found["dates"].index(PREVIOUS)
        after = {"time": f"{PREVIOUS}T19:50:00-05:00", "ratio": round(1 + _tilt(index, "after"), 6), "stocks": _prices(found["stocks"], n, "after"), "point": POINT}
        if moment == "futures" and index == "nasdaq":
            after.update(basis="futures", futures_time=ny(at))
        pre = {"time": f"{POINT}T09:20:00-05:00", "ratio": round(1 + _tilt(index, "pre"), 6), "stocks": _prices(found["stocks"], n, "pre"), "session": PREVIOUS, "phase": "pre", "point": POINT}
        r = round(1 + _tilt(index, "regular"), 6)
        regular = {"time": ny(at if moment == "regular" else dt.datetime(2026, 11, 19, 21, 0, tzinfo=dt.timezone.utc)), "ratio": r,
                   "stocks": _prices(found["stocks"], n, "regular"), "session": PREVIOUS, "phase": "regular", "point": POINT,
                   "ohlc": {"open": round(r - .004, 6), "high": round(r + .006, 6), "low": round(r - .009, 6), "close": r}, "pre": pre}
        if moment in ("after", "futures"):
            afterhours[index] = {PREVIOUS: after}
        elif moment == "pre":
            premarket[index] = {POINT: pre}
        else:
            premarket[index] = {POINT: regular}
    ndx = {"^NDX": 21000.0, "^NBI": 4500.0, "CL=F": 61.25}
    loaded = (at - dt.timedelta(minutes=2)).astimezone(KST).strftime("%Y-%m-%dT%H:%M:00+09:00")
    index_values = {sym: {"price": price, "time": loaded, "loaded": loaded} for sym, price in ndx.items()}
    progress = {"date": POINT, "indexes": {index: {"step": 1, "since": f"{TODAY}T23:40:00+09:00"} for index in board}, "plan": [0, 20, 60, 120]}
    return {"premarket": premarket, "afterhours": afterhours, "progress": progress, "index": index_values}


NEWS_URL = "https://invest-news.wonwooshik.workers.dev"
# 종목 뉴스 SAMPLE 기사. (회차, 지수, 종목, 제목, 머리 줄)이고 값은 모두 지어낸 값이다. 회차 시작 시각은 `NOW`(11/19 23:45 KST) 앞이다.
# 최신 회차(11/19 18:00)에는 나스닥 기사가 일곱 편이고 바이오 기사는 없다. NVDA를 단 기사는 서른한 편이다.
NEWS = [
    ("2026-11-19-18", "nasdaq", ["NVDA"], "엔비디아, 차세대 AI 칩 출하를 한 분기 앞당겨", "공급망 점검에서 첫 물량이 12월에 나간다고 확인…데이터센터 주문 늘어"),
    ("2026-11-19-18", "nasdaq", ["AAPL", "MSFT"], "애플과 마이크로소프트, 기업용 AI 비서 제휴 넓혀", "두 회사가 업무용 서비스에서 같은 모델을 쓴다"),
    ("2026-11-19-06", "nasdaq", ["NVDA"], "엔비디아 주가, 실적 발표 다음 날 3% 내려", "매출은 예상을 넘었지만 다음 분기 이익률 전망이 낮았다"),
    ("2026-11-18-18", "nasdaq", ["TSLA"], "테슬라, 유럽 판매가 석 달 만에 늘어", "보급형 모델이 나온 뒤 10월 등록 대수가 앞 달보다 많았다"),
    ("2026-11-18-06", "nasdaq", ["NVDA"], "엔비디아, 3분기 매출이 시장 예상을 웃돌아", "데이터센터 매출이 한 해 전보다 크게 늘었다"),
    ("2026-11-17-06", "nasdaq", ["AMD"], "AMD, 데이터센터 칩 새 고객 확보", "클라우드 기업 한 곳이 내년 물량을 주문했다"),
    ("2026-11-16-18", "nasdaq", ["NVDA"], "엔비디아 실적 발표를 앞두고 옵션 거래 늘어", "실적 발표 주간의 주가 변동 기대가 커졌다"),
    ("2026-11-15-06", "nasdaq", ["META"], "메타, 내년 데이터센터 투자 계획 늘려", "AI 연산 설비에 쓰는 돈이 올해보다 많아진다"),
    ("2026-11-13-06", "nasdaq", ["NVDA"], "엔비디아, 중동 데이터센터에 칩 공급 계약", "두 해에 걸쳐 칩을 나눠 공급한다"),
    ("2026-11-12-06", "nasdaq", ["NVDA"], "엔비디아, 새 네트워크 장비 공개", "데이터센터 서버 사이 연결 속도를 두 배로 높였다"),
    ("2026-11-10-18", "nasdaq", ["NVDA"], "엔비디아 공급사 주가가 함께 올라", "메모리와 기판 업체의 주문이 늘었다"),
    ("2026-11-09-06", "nasdaq", ["NVDA"], "엔비디아, 자율주행 플랫폼 협력사 늘려", "완성차 업체 두 곳이 새로 합류했다"),
    ("2026-11-06-18", "nasdaq", ["NVDA"], "엔비디아, 연례 개발자 행사 일정 공개", "행사는 내년 3월에 열린다"),
    ("2026-11-05-06", "nasdaq", ["NVDA"], "엔비디아, 소프트웨어 구독 가격 올려", "기업용 AI 도구 구독료가 내년부터 오른다"),
    ("2026-11-03-18", "nasdaq", ["NVDA"], "엔비디아, 유럽 연구소 세워", "현지 대학과 AI 연구를 함께 한다"),
    ("2026-11-19-06", "biotech", ["AMGN"], "암젠, 비만 치료제 3상 결과 발표일 확정", "다음 달 학회에서 결과를 낸다"),
    ("2026-11-18-18", "biotech", ["GILD", "VRTX"], "길리어드와 버텍스, 약가 협상 대상에 올라", "두 회사의 대표 약이 내년 협상 목록에 들었다"),
    ("2026-11-17-18", "biotech", ["REGN"], "리제네론, 안과 치료제 처방 줄어", "경쟁 약이 나온 뒤 석 달째 처방이 줄었다"),
    ("2026-11-19-18", "nasdaq", ["TSLA"], "테슬라, 자율주행 택시 운행 지역을 두 도시 늘려", "새 지역은 다음 달부터 유료로 운행한다"),
    ("2026-11-19-18", "nasdaq", ["AMD"], "AMD, 새 AI 가속기 출하 시작", "첫 물량은 클라우드 기업 두 곳에 간다"),
    ("2026-11-19-18", "nasdaq", ["AMD"], "AMD, 서버 칩 가격을 올려", "내년 1분기 주문부터 새 가격을 쓴다"),
    ("2026-11-19-18", "nasdaq", ["META"], "메타, 스마트 안경 새 모델 공개", "카메라와 화면을 넣은 모델이 내년에 나온다"),
    ("2026-11-19-18", "nasdaq", ["INTC"], "인텔, 파운드리 고객 한 곳 더 확보", "2나노급 공정으로 칩을 만든다"),
]
# 종목 상세 주요 뉴스 절의 장 넘기기와 번호 줄을 시험하는 NVDA의 10월 기사 스무 편.
NEWS += [(f"2026-10-{day:02d}-06", "nasdaq", ["NVDA"], f"엔비디아 10월 {day}일 SAMPLE 기사", f"10월 {day}일 SAMPLE 요약이다") for day in range(20, 0, -1)]
# 최신 회차의 종목별 회차 구간 변동률(%). INTC는 값을 받지 못한 종목이다.
NEWS_MOVES = {"NVDA": 4.1, "AAPL": 1.2, "MSFT": 0.9, "TSLA": 6.5, "AMD": 3.0, "META": 0.8}
# 뉴스 Worker에 등록한 최신 회차. SAMPLE 기사의 가장 늦은 회차다.
NEWS_ROUND = max(name for name, *_ in NEWS)
NEWS_CARD = {"issue": 1, "after": 2, "name": "차세대 칩 분기 출하 물량", "asof": "SAMPLE · 11/19", "value": "55", "unit": "만 개",
             "figure": {"type": "bars", "items": [], "groups": [["2분기", [[30, "30만 개"]]], ["3분기", [[42, "42만 개"]]], ["4분기 예상", [[55, "55만 개"]]]],
                        "min": 0, "max": 55},
             "state": ["앞 분기보다 31% 많다", "#ffffff"], "caption": "4분기 예상 출하 물량은 회사가 밝힌 공급 계획에서 셈했다."}

NEWS_TERM = {"id": "guidance", "term": "가이던스", "desc": "기업이 직접 내놓은 다음 분기나 한 해의 실적 전망치다."}
# 첫 기사의 소제목 세 줄. 첫 줄은 그 기사의 머리 줄과 같다. 나머지 기사는 소제목 줄 없이 올린 기사처럼 빈 목록이다.
NEWS_SUBHEADS = [NEWS[0][4], "공급사의 기판 수율이 목표를 넘어 출하를 앞당겼다", "주가는 발표 뒤 시간외 거래에서 2% 올랐다"]


def _news_body(title: str, rich: bool) -> str:
    """SAMPLE 기사 본문 HTML. `rich`면 build.py `issue_articles`가 만드는 조각처럼 소제목 두 개, 이슈 그래프 카드 하나, 단어표 용어 하나를 둔다."""
    lead = f"<p>{html.escape(title)}. 이 문단은 리드다. 회사가 밝힌 내용과 시장의 반응을 두 문장으로 쓴다.</p>"
    if not rich:
        return lead + "\n<p>둘째 문단은 사실의 배경을 쓴다. 숫자는 모두 지어낸 값이다.</p>"
    card = html.escape(json.dumps(NEWS_CARD, ensure_ascii=False))
    term = f'<button class="term" type="button" data-term="{NEWS_TERM["term"]}" data-desc="{NEWS_TERM["desc"]}">가이던스</button>'
    return "\n".join([
        lead,
        "<p>회사는 4분기 출하 물량이 55만 개라고 밝혔다. 3분기 42만 개보다 31% 많다.</p>",
        f'<figure class="issue-chart" data-card="{card}"></figure>',
        "<p>출하를 앞당긴 이유는 공급사의 생산 수율이 오른 데 있다.</p>",
        "<p>경쟁사 AMD와 인텔도 주문을 늘렸다. 인텔리전스 사업과 애플리케이션 시장은 영향을 받지 않았고, 엔비디아는 같은 날 다른 계약도 밝혔다.</p>",
        "<h5>공급사 수율이 오른 덕분</h5>",
        "<p>기판 공급사는 지난달 새 공정의 수율이 목표를 넘었다고 밝혔다.</p>",
        f"<p>회사는 다음 분기 매출 {term}를 바꾸지 않았다.</p>",
        "<h5>주가는 장 마감 뒤 올라</h5>",
        "<p>발표 뒤 시간외 거래에서 주가가 2% 올랐다.</p>",
        "<p>시장은 다음 달 고객 행사에서 나올 주문 규모를 기다린다.</p>",
    ])


def news() -> list[dict]:
    """SAMPLE 기사마다 뉴스 Worker `GET /articles/{ID}`가 돌려주는 값과 회차 시작 시각(`start`). ID는 `{회차}-{지수}-1-{회차 안 순번}`이다.
    첫 기사만 소제목 세 줄(`NEWS_SUBHEADS`)이 있다.
    그림 이름은 `sample-{첫 종목}-{순번}.webp`이고, `news_answer`가 리포트 자료의 `r/stocks/{종목}-{순번}.webp`로 답한다.
    기사마다 그림이 한 장이다."""
    out, seen = [], {}
    for n, (name, index, tickers, title, headline) in enumerate(NEWS):
        seen[(name, index)] = seen.get((name, index), 0) + 1
        time = f"{name[:10]}T{name[11:]}:00:00+09:00"
        images = [{"url": f"{NEWS_URL}/images/sample-{tickers[0]}-1.webp", "caption": f"{title} 관련 SAMPLE 그림"}]
        moves = {ticker: NEWS_MOVES[ticker] for ticker in tickers if ticker in NEWS_MOVES} if name == NEWS_ROUND else {}
        out.append({"id": f"{name}-{index}-1-{seen[(name, index)]}", "round": name, "time": time, "start": dt.datetime.fromisoformat(time), "moves": moves,
                    "indices": [index], "tickers": tickers, "title": title, "subheads": NEWS_SUBHEADS if n == 0 else [], "headline": headline,
                    "html": _news_body(title, n == 0),
                    "images": images, "charts": [NEWS_CARD] if n == 0 else [], "terms": [NEWS_TERM] if n == 0 else [], "sources": [{"url": f"https://example.com/news/{n}", "time": time}],
                    "previous": None})
    return out


def news_answer(data_root: Path, path: str, params: dict) -> tuple[int, bytes, str]:
    """뉴스 Worker 공개 읽기의 (응답 코드, 본문, 형식). 지수 목록은 `worker/news.js`처럼 최신 회차(`NEWS_ROUND`)의 지수 기사를 첫 종목의
    변동률이 큰 기사부터, 같으면 ID 순으로, 변동률이 없는 기사는 맨 뒤에 준다. 종목 목록은 그 종목을 단 최신 기사 `limit`편을
    회차 시작 시각이 늦은 기사부터, 같으면 ID 순으로 준다."""
    articles = sorted(news(), key=lambda a: (-a["start"].timestamp(), a["id"]))
    reply = lambda value: (200, json.dumps(value, ensure_ascii=False).encode(), "application/json")
    entry = lambda a: {"id": a["id"], "round": a["round"], "time": a["time"], "tickers": a["tickers"], "title": a["title"],
                       "headline": a["headline"], "image": a["images"][0]["url"] if a["images"] else None, "move": a["moves"].get(a["tickers"][0])}
    if path == "list" and "index" in params:
        found = sorted((a for a in articles if a["round"] == NEWS_ROUND and params["index"][0] in a["indices"]),
                       key=lambda a: (-a["moves"].get(a["tickers"][0], -1), a["id"]))
        return reply({"round": NEWS_ROUND, "time": f"{NEWS_ROUND[:10]}T{NEWS_ROUND[11:]}:00:00+09:00", "articles": [entry(a) for a in found]})
    if path == "list" and "ticker" in params:
        return reply({"articles": [entry(a) for a in articles if params["ticker"][0] in a["tickers"]][:int(params["limit"][0])]})
    if path.startswith("articles/"):
        found = next((a for a in articles if a["id"] == path[len("articles/"):]), None)
        return reply({k: v for k, v in found.items() if k not in ("start", "moves")}) if found else (404, b"", "application/json")
    image = re.fullmatch(r"images/sample-([A-Z.]+)-(\d+)\.webp", path)
    source = data_root / "r" / "stocks" / f"{image.group(1)}-{image.group(2)}.webp" if image else None
    if source and source.is_file():
        return 200, source.read_bytes(), "image/webp"
    return 404, b"", "application/json"


HISTORY_RE = re.compile(r'\s*<template class="issue-history">(.*?)</template>\s*', re.DOTALL)
SECTION_RE = re.compile(r'<section data-day="([^"]*)" data-title="([^"]*)">(.*?)</section>(?=<section data-day=|$)', re.DOTALL)
CARDS_RE = re.compile(r'<script type="application/json" id="cards">(.*?)</script>\n?', re.DOTALL)


def split(data_root: Path, overlay: dict) -> dict:
    """`r/*/report.html`(`overlay`에 있으면 그 바이트)의 `issue-history` 템플릿과 `#cards` 조각을 build.py처럼 `r/{키}/history.json`·`cards.json`으로 빼고,
    `r/index.json`의 목록 항목에 쓴 JSON의 이름을 `parts`로 적은 `{경로: 바이트}`를 돌려준다. 템플릿의 이슈 `id`는 그 앞 마지막 이슈 제목의 `data-issue`다."""
    out = dict(overlay)
    entries = json.loads(out.get("r/index.json") or (data_root / "r" / "index.json").read_bytes())
    for key in entries:
        path = f"r/{key}/report.html"
        found = data_root / path
        if path not in out and not found.is_file():
            continue
        body = (out.get(path) or found.read_bytes()).decode("utf-8")
        history = {}
        for match in HISTORY_RE.finditer(body):
            issue = re.findall(r'<h3[^>]*data-issue="([^"]*)"', body[:match.start()])[-1]
            history[html.unescape(issue)] = [{"day": day, "title": html.unescape(title), "html": chunk}
                                             for day, title, chunk in SECTION_RE.findall(match.group(1))]
        cards = CARDS_RE.search(body)
        values = {"history": history, "cards": json.loads(cards.group(1)) if cards else None}
        parts = [name for name, value in values.items() if value]
        if not parts:
            continue
        out[path] = CARDS_RE.sub("", HISTORY_RE.sub("\n", body)).encode()
        for name in parts:
            out[f"r/{key}/{name}.json"] = (json.dumps(values[name], ensure_ascii=False) + "\n").encode()
        entries[key]["parts"] = parts
    # 다시 만든 자료의 `updated`는 다시 만든 시각이라 `NOW`보다 늦을 수 있다. 머리 상자 시각이 리포트 날짜 0시보다 하루 넘게 늦은 값으로 나오지 않도록 `written`으로 되돌린다.
    cap = NOW.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    for entry in entries.values():
        if entry.get("updated", "") > cap:
            entry["updated"] = entry["written"]
    out["r/index.json"] = (json.dumps(entries, ensure_ascii=False, indent=1) + "\n").encode()
    return out
