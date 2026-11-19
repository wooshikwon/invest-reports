"""live.py 1분 회차 시험. 토스·야후·Worker를 가짜로 바꾸고, 장 운영 시각은 실제 XNYS 달력을 쓴다."""
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import live  # noqa: E402

NY = live.NEW_YORK
BOARD = {"nasdaq": {"dates": ["2026-10-01"], "stocks": [{"symbol": "AAPL"}, {"symbol": "MSFT"}]},
         "biotech": {"dates": ["2026-10-01"], "stocks": [{"symbol": "AMGN"}]}}
BASE = {"QQQ": 500.0, "IBB": 100.0}  # 2026-11-18 정규장 종가


class Answer:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise live.requests.HTTPError(str(self.status_code))


class Market:
    """가짜 토스·야후. `prices`는 토스 시세 응답의 심볼마다 (가격, 시각), `closes`는 마감 1분봉, `spark`는 야후 1분봉이다."""

    def __init__(self):
        self.prices, self.closes, self.spark, self.toss_down = {}, {}, {}, False
        self.toss, self.yahoo = [], []

    def toss_get(self, url, params, timeout, headers):
        self.toss.append((url.rsplit("/", 1)[-1], params))
        if self.toss_down:
            raise live.requests.ConnectTimeout()
        if url.endswith("/prices"):
            asked = params["symbols"].split(",")
            return Answer({"result": [{"symbol": symbol, "lastPrice": str(price), "currency": "USD", "timestamp": stamp or ""}
                                      for symbol, (price, stamp) in self.prices.items() if symbol in asked]})
        if params["interval"] == "1d":
            return Answer({"result": {"candles": [{"timestamp": "2026-11-18T14:00:00.000+09:00", "closePrice": str(BASE[params["symbol"]])}]}})
        price = self.closes[params["symbol"]]  # 토스 1분봉의 시각은 봉이 끝나는 시각이다
        return Answer({"result": {"candles": [{"timestamp": params["before"], "closePrice": str(price)}]}})

    def yahoo_get(self, url, impersonate, timeout, params):
        asked = params["symbols"].split(",")
        self.yahoo.extend(asked)
        result = []
        for symbol in asked:
            bars = self.spark.get(symbol, [])
            result.append({"symbol": symbol, "response": [{"meta": {}, "timestamp": [int(moment.timestamp()) for moment, _ in bars],
                                                           "indicators": {"quote": [{"close": [price for _, price in bars]}]}}]})
        return Answer({"spark": {"result": result}})


@pytest.fixture
def market(tmp_path, monkeypatch):
    found = Market()
    monkeypatch.setattr(live, "DATA", tmp_path)
    monkeypatch.setattr(live, "public_board", lambda: BOARD)
    monkeypatch.setattr(live, "holding_symbols", lambda: [])
    monkeypatch.setattr(live.Toss, "token", lambda self, dead=None: "token")
    monkeypatch.setattr(live.requests, "get", found.toss_get)
    monkeypatch.setattr(live.chrome, "get", found.yahoo_get)
    found.written = []
    monkeypatch.setattr(live.build, "post_live", lambda name, value: found.written.append(name))
    return found


def at(day: str, clock: str) -> dt.datetime:
    return dt.datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=NY)


def kst(day: str, clock: str) -> str:
    return dt.datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=NY).astimezone(live.build.SEOUL).isoformat()


def test_outside_hours_calls_nothing(market):
    assert live.tick(at("2026-11-19", "03:59:10")) == {}  # 프리장 전
    assert market.toss == [] and market.written == []
    market.prices = {symbol: (10.0, kst("2026-11-19", "19:59:50")) for symbol in ("QQQ", "IBB", "AAPL", "MSFT", "AMGN")}
    market.closes = {symbol: 9.0 for symbol in market.prices}
    assert set(live.tick(at("2026-11-19", "20:00:10"))) == {"premarket", "afterhours"}  # 마감 값과 애프터장 끝 값을 받는다
    market.toss.clear()
    assert live.tick(at("2026-11-19", "20:01:10")) == {}  # 그날 값을 다 받았다
    assert live.tick(at("2026-11-19", "23:30:00")) == {}
    assert market.toss == [] and market.yahoo == []


def test_holiday_calls_nothing(market):
    assert live.tick(at("2026-11-26", "10:00:05")) == {}  # 추수감사절
    assert live.tick(at("2026-11-28", "10:00:05")) == {}  # 토요일
    assert market.toss == [] and market.yahoo == [] and market.written == []


def test_close_wait_then_fix(market):
    market.prices = {"QQQ": (505.0, kst("2026-11-19", "15:58:59")), "IBB": (99.0, kst("2026-11-19", "15:58:30")),
                     "AAPL": (10.0, kst("2026-11-19", "15:58:00")), "MSFT": (20.0, kst("2026-11-19", "15:58:00")), "AMGN": (30.0, kst("2026-11-19", "15:57:00"))}
    live.tick(at("2026-11-19", "15:59:05"))
    market.toss.clear()
    for clock in ("16:00:05", "16:02:05", "16:04:59"):
        assert live.tick(at("2026-11-19", clock)) == {}
    assert market.toss == []
    market.closes = {"QQQ": 506.0, "IBB": 98.0, "AAPL": 11.0, "MSFT": 21.0}  # AMGN 마감 1분봉은 토스가 답하지 않는다
    market.spark = {"AMGN": []}  # 야후도 봉이 없다
    market.prices = {symbol: (price + 1, kst("2026-11-19", "16:04:30")) for symbol, (price, _) in market.prices.items()}
    written = live.tick(at("2026-11-19", "16:05:05"))
    fixed = written["premarket"]["nasdaq"]["2026-11-19"]
    assert fixed["time"] == "2026-11-19T16:00:00-05:00" and fixed["phase"] == "regular"
    assert fixed["ratio"] == 1.012 and fixed["stocks"] == {"AAPL": 11.0, "MSFT": 21.0}
    assert written["premarket"]["biotech"]["2026-11-19"]["stocks"] == {"AMGN": 30.0}  # 마감 값을 못 받으면 앞 회차 값을 둔다
    after = written["afterhours"]["nasdaq"]["2026-11-19"]
    assert after["time"] == "2026-11-19T16:05:00-05:00" and after["stocks"] == {"AAPL": 11.0, "MSFT": 21.0}
    assert after["ratio"] == round(506.0 / 506.0, 6)
    assert written["afterhours"]["biotech"]["2026-11-19"]["ratio"] == round(100.0 / 98.0, 6)
    assert {params["before"] for name, params in market.toss if name == "candles" and params["interval"] == "1m"} == {"2026-11-19T16:00:00-05:00"}
    market.toss.clear()
    assert set(live.tick(at("2026-11-19", "16:06:05"))) == {"afterhours"}  # 마감 값은 한 번만 고정한다
    assert [name for name, _ in market.toss] == ["prices"]


def test_early_close_waits_after_its_own_close(market):
    assert live.tick(at("2026-11-27", "13:02:00")) == {}  # 추수감사절 다음날은 13:00에 닫힌다
    assert live.calendar_day(dt.date(2026, 11, 27))["closed"] == "2026-11-27T13:00:00-05:00"
    assert market.toss == []


def test_premarket_without_trades_is_null(market):
    market.prices = {"QQQ": (501.0, kst("2026-11-19", "05:00:30")), "IBB": (100.5, kst("2026-11-19", "03:40:00")),
                     "AAPL": (10.0, kst("2026-11-19", "03:30:00")),  # 주간거래 체결이라 프리장 전이다
                     "MSFT": (20.0, None), "AMGN": (30.0, kst("2026-11-19", "04:30:00"))}
    written = live.tick(at("2026-11-19", "05:01:05"))["premarket"]
    nasdaq, biotech = written["nasdaq"]["2026-11-19"], written["biotech"]["2026-11-19"]
    assert nasdaq == {"session": "2026-11-18", "time": "2026-11-19T05:01:00-05:00", "phase": "pre", "ratio": 1.002,
                      "stocks": {"AAPL": None, "MSFT": None}}
    assert biotech["ratio"] is None and biotech["stocks"] == {"AMGN": 30.0}
    assert market.yahoo == []  # 체결 시각 없는 MSFT는 야후에 묻지 않는다
    assert [name for name, _ in market.toss].count("prices") == 1


def test_toss_down_falls_back_to_yahoo(market):
    market.prices = {"QQQ": (501.0, kst("2026-11-19", "09:40:00")), "IBB": (100.5, kst("2026-11-19", "09:40:00")),
                     "AAPL": (10.0, kst("2026-11-19", "09:40:00")), "MSFT": (20.0, kst("2026-11-19", "09:40:00")), "AMGN": (30.0, kst("2026-11-19", "09:40:00"))}
    live.tick(at("2026-11-19", "09:41:05"))
    market.toss_down = True
    market.spark = {"QQQ": [(at("2026-11-19", "09:41"), 502.0)], "IBB": [(at("2026-11-19", "09:41"), 101.0)],
                    "AAPL": [(at("2026-11-19", "09:40"), 10.5), (at("2026-11-19", "09:41"), None)],
                    "MSFT": [], "AMGN": [(at("2026-11-19", "03:50"), 31.0)]}
    written = live.tick(at("2026-11-19", "09:42:05"))["premarket"]
    nasdaq = written["nasdaq"]["2026-11-19"]
    assert nasdaq["ratio"] == 1.004 and nasdaq["stocks"] == {"AAPL": 10.5, "MSFT": 20.0}  # 야후 봉이 비면 앞 회차 값을 둔다
    assert written["biotech"]["2026-11-19"]["stocks"] == {"AMGN": 30.0}
    assert sorted(market.yahoo) == ["AAPL", "AMGN", "IBB", "MSFT", "QQQ"]


def test_regular_keeps_last_premarket_as_pre(market):
    market.prices = {"QQQ": (501.0, kst("2026-11-19", "09:29:30")), "IBB": (100.5, kst("2026-11-19", "09:29:30")),
                     "AAPL": (10.0, kst("2026-11-19", "09:29:30")), "MSFT": (20.0, kst("2026-11-19", "09:29:30")), "AMGN": (30.0, kst("2026-11-19", "09:29:30"))}
    live.tick(at("2026-11-19", "09:30:05"))
    market.prices = {symbol: (price * 2, kst("2026-11-19", "09:30:40")) for symbol, (price, _) in market.prices.items()}
    for clock in ("09:31:05", "09:32:05"):
        written = live.tick(at("2026-11-19", clock))["premarket"]
    value = written["nasdaq"]["2026-11-19"]
    assert value["phase"] == "regular" and value["time"] == "2026-11-19T09:32:00-05:00" and value["stocks"] == {"AAPL": 20.0, "MSFT": 40.0}
    assert value["pre"] == {"time": "2026-11-19T09:30:00-05:00", "ratio": 1.002, "stocks": {"AAPL": 10.0, "MSFT": 20.0}}


def test_old_dates_are_dropped(market):
    (live.DATA / "premarket.json").write_text('{"nasdaq": {"2026-09-30": {"time": "x"}, "2026-10-01": {"time": "y", "phase": "regular"}}}')
    market.prices = {"QQQ": (501.0, kst("2026-11-19", "05:00:30"))}
    written = live.tick(at("2026-11-19", "05:01:05"))["premarket"]
    assert sorted(written["nasdaq"]) == ["2026-10-01", "2026-11-19"]


def test_toss_retries_after_too_many_requests(market, monkeypatch):
    answers = [Answer({}, 429), Answer({"result": []})]
    monkeypatch.setattr(live.requests, "get", lambda url, params, timeout, headers: answers.pop(0))
    monkeypatch.setattr(live.time, "sleep", lambda seconds: None)
    toss = live.Toss()
    assert toss.get("/api/v1/prices", {"symbols": "QQQ"}) == [] and toss.calls["prices"] == 2
    answers[:] = [Answer({}, 429)] * live.ATTEMPTS
    with pytest.raises(live.requests.HTTPError):
        toss.get("/api/v1/candles", {"symbol": "QQQ"})
