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
BASE = {"QQQ": 500.0, "IBB": 100.0}  # 11월 세션마다의 정규장 종가


class Answer:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise live.requests.HTTPError(str(self.status_code))


class Market:
    """가짜 토스·야후. `prices`는 토스 시세 응답의 심볼마다 (가격, 시각), `closes`는 마감 1분봉, `spark`는 야후 1분봉,
    `meta`는 야후 응답의 앞 세션 종가(`chartPreviousClose`)다.

    지수 묶음 요청은 `yahoo`에 넣지 않고 그 요청의 `range`를 `indexes`에 넣는다.
    """

    def __init__(self):
        self.prices, self.closes, self.spark, self.meta, self.toss_down = {}, {}, {}, {}, False
        self.toss, self.yahoo, self.indexes = [], [], []

    def toss_get(self, url, params, timeout, headers):
        self.toss.append((url.rsplit("/", 1)[-1], params))
        if self.toss_down:
            raise live.requests.ConnectTimeout()
        if url.endswith("/prices"):
            asked = params["symbols"].split(",")
            return Answer({"result": [{"symbol": symbol, "lastPrice": str(price), "currency": "USD", "timestamp": stamp or ""}
                                      for symbol, (price, stamp) in self.prices.items() if symbol in asked]})
        if params["interval"] == "1d":
            return Answer({"result": {"candles": [{"timestamp": f"2026-11-{date:02d}T14:00:00.000+09:00", "closePrice": str(BASE[params["symbol"]])}
                                                  for date in range(1, 31)]}})
        price = self.closes[params["symbol"]]  # 토스 1분봉의 시각은 봉이 끝나는 시각이다
        return Answer({"result": {"candles": [{"timestamp": params["before"], "closePrice": str(price)}]}})

    def yahoo_get(self, url, impersonate, timeout, params):
        asked = params["symbols"].split(",")
        if "^NDX" in asked:
            self.indexes.append(params["range"])
        else:
            self.yahoo.extend(asked)
        result = []
        for symbol in asked:
            bars = self.spark.get(symbol, [])
            meta = {"chartPreviousClose": self.meta[symbol]} if symbol in self.meta else {}
            result.append({"symbol": symbol, "response": [{"meta": meta, "timestamp": [int(moment.timestamp()) for moment, _ in bars],
                                                           "indicators": {"quote": [{"close": [price for _, price in bars]}]}}]})
        return Answer({"spark": {"result": result}})


@pytest.fixture
def market(tmp_path, monkeypatch):
    found = Market()
    monkeypatch.setattr(live, "DATA", tmp_path)
    monkeypatch.setattr(live, "public_board", lambda: BOARD)
    monkeypatch.setattr(live, "holding_symbols", lambda: [])
    monkeypatch.setattr(live, "ETFS", tmp_path / "etfs.json")
    monkeypatch.setattr(live.Toss, "token", lambda self, dead=None: "token")
    monkeypatch.setattr(live.requests, "get", found.toss_get)
    monkeypatch.setattr(live.chrome, "get", found.yahoo_get)
    found.written = []
    monkeypatch.setattr(live.build, "post_live", lambda name, value: found.written.append((name, value)))
    found.accounts = []
    monkeypatch.setattr(live, "post_account", lambda now, prices: found.accounts.append((now.isoformat(), prices)))
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


def test_holiday_calls_no_toss(market):
    assert live.tick(at("2026-11-26", "10:00:05")) == {}  # 추수감사절
    assert live.tick(at("2026-11-28", "10:00:05")) == {}  # 토요일
    assert market.toss == [] and market.yahoo == [] and market.written == []
    assert market.indexes == ["5d", "5d"]  # 선물 시간대라 지수 묶음 요청만 부른다


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
    assert nasdaq == {"session": "2026-11-18", "point": "2026-11-19", "time": "2026-11-19T05:01:00-05:00", "phase": "pre", "ratio": 1.002,
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


def test_holdings_go_only_to_account(market, monkeypatch):
    monkeypatch.setattr(live, "holding_symbols", lambda: ["QQQ", "SGOV", "TQQQ"])  # TQQQ는 토스·야후 모두 답하지 않는다
    market.prices = {"QQQ": (501.0, kst("2026-11-19", "09:40:00")), "IBB": (100.5, kst("2026-11-19", "09:40:00")),
                     "AAPL": (10.0, kst("2026-11-19", "09:40:00")), "SGOV": (100.2, None)}
    market.spark = {"TQQQ": []}
    live.tick(at("2026-11-19", "09:41:05"))
    assert market.accounts == [("2026-11-19T09:41:05-05:00", {"QQQ": 501.0, "SGOV": 100.2})]
    assert market.written and all("SGOV" not in str(value) for _, value in market.written)  # 공개 종목이 아닌 보유 종목은 invest-live에 쓰지 않는다
    assert [name for name, _ in market.toss].count("prices") == 1


def test_no_holdings_writes_no_account(market):
    market.prices = {"QQQ": (501.0, kst("2026-11-19", "09:40:00"))}
    live.tick(at("2026-11-19", "09:41:05"))
    assert market.written and market.accounts == []


def test_holding_symbols_reads_symbol_list(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "HOLDINGS", tmp_path / "holdings.json")
    assert live.holding_symbols() == []
    (tmp_path / "holdings.json").write_text('["QQQ", "SGOV"]')
    assert live.holding_symbols() == ["QQQ", "SGOV"]


def test_post_account_needs_secret_and_204(monkeypatch):
    sent = []
    monkeypatch.setattr(live.requests, "post", lambda url, **kwargs: sent.append((url, kwargs)) or Answer(None, status))
    monkeypatch.delenv("ACCOUNT_SECRET", raising=False)
    with pytest.raises(EnvironmentError, match="ACCOUNT_SECRET"):
        live.post_account(at("2026-11-19", "09:41:05"), {"QQQ": 501.0})
    assert sent == []
    monkeypatch.setenv("ACCOUNT_SECRET", "sample-secret")
    status = 204
    live.post_account(at("2026-11-19", "09:41:05"), {"QQQ": 501.0})
    url, kwargs = sent[0]
    assert url == "https://invest-account.wonwooshik.workers.dev/live"
    assert kwargs["json"] == {"time": "2026-11-19T09:41:05-05:00", "prices": {"QQQ": 501.0}}
    assert kwargs["headers"]["X-Account-Secret"] == "sample-secret"
    status = 403
    with pytest.raises(RuntimeError, match="403"):
        live.post_account(at("2026-11-19", "09:41:05"), {"QQQ": 501.0})


STOCKS = ("QQQ", "IBB", "AAPL", "MSFT", "AMGN")


def traded(market, day: str, clock: str, scale: float = 1.0) -> None:
    """공개 종목 다섯이 `day` `clock`(뉴욕)에 체결한 토스 시세. 가격은 지어낸 SAMPLE 값이다."""
    market.prices = {symbol: (price * scale, kst(day, clock)) for symbol, price in zip(STOCKS, (505.0, 99.0, 10.0, 20.0, 30.0))}
    market.closes = {symbol: price for symbol, (price, _) in market.prices.items()}


def minutes(day: str, start: str, end: str, first: float, step: float) -> list[tuple[dt.datetime, float]]:
    """`start`부터 `end`까지 1분봉. 종가는 `first`에서 분마다 `step`씩 오른다."""
    found, moment = [], at(day, start)
    while moment <= at(day, end):
        found.append((moment, first + step * len(found)))
        moment += dt.timedelta(minutes=1)
    return found


def test_close_makes_next_point(market):
    """정규장 마감 고정 회차가 다음 세션의 날짜 지점을 만들고, 마감 값에 그날 정규장 시가·고가·저가·종가 비율을 적는다."""
    traded(market, "2026-11-19", "15:59:30")
    market.spark = {"^NDX": minutes("2026-11-19", "09:30", "16:00", 1010.0, 0.1), "^NBI": minutes("2026-11-19", "09:30", "16:00", 200.0, -0.1)}
    market.meta = {"^NDX": 1000.0, "^NBI": 200.0}
    written = live.tick(at("2026-11-19", "16:05:05"))
    close = written["premarket"]["nasdaq"]["2026-11-19"]
    assert close["point"] == "2026-11-19" and close["phase"] == "regular"
    assert close["ohlc"] == {"open": 1.01, "high": round(1049.0 / 1000, 6), "low": 1.01, "close": round(1049.0 / 1000, 6)}
    assert written["premarket"]["biotech"]["2026-11-19"]["ohlc"] == {"open": 1.0, "high": 1.0, "low": round(161.0 / 200, 6), "close": round(161.0 / 200, 6)}
    after = written["afterhours"]["nasdaq"]["2026-11-19"]
    assert after["point"] == "2026-11-20" and "basis" not in after  # 11/19 애프터장 값은 11/20 날짜 지점에 그린다


def test_after_hours_point_and_last_trade(market):
    traded(market, "2026-11-19", "16:59:40")
    written = live.tick(at("2026-11-19", "17:00:05"))
    assert set(written) == {"premarket", "afterhours"}
    assert all(days["2026-11-19"]["point"] == "2026-11-20" and "basis" not in days["2026-11-19"] for days in written["afterhours"].values())
    assert live.calendar_day(dt.date(2026, 11, 19))["trade"] == {"nasdaq": kst("2026-11-19", "16:59:40")}  # 선물 시간대의 기준 시각


def test_premarket_and_regular_points(market):
    traded(market, "2026-11-20", "05:00:30")
    market.spark = {"^NDX": minutes("2026-11-20", "09:30", "10:20", 1000.0, 1.0)}
    market.meta = {"^NDX": 1000.0}
    pre = live.tick(at("2026-11-20", "05:01:05"))["premarket"]["nasdaq"]["2026-11-20"]
    assert pre["point"] == "2026-11-20" and pre["phase"] == "pre" and "ohlc" not in pre
    traded(market, "2026-11-20", "10:14:50")
    regular = live.tick(at("2026-11-20", "10:15:05"))["premarket"]
    value = regular["nasdaq"]["2026-11-20"]
    assert value["point"] == "2026-11-20" and value["phase"] == "regular" and value["pre"]["time"] == "2026-11-20T05:01:00-05:00"
    assert value["ohlc"] == {"open": 1.0, "high": 1.045, "low": 1.0, "close": 1.045}  # 10:15에 시작한 봉까지 쓴다
    assert "ohlc" not in regular["biotech"]["2026-11-20"]  # ^NBI 1분봉이 없으면 적지 않는다


def test_session_after_holiday(market):
    """추수감사절(11/26) 뒤 세션 11/27의 날짜 지점은 11/25 애프터장 값과 11/27 프리장 값을 받는다."""
    traded(market, "2026-11-25", "16:59:40")
    live.tick(at("2026-11-25", "17:00:05"))
    traded(market, "2026-11-27", "05:00:30")
    written = live.tick(at("2026-11-27", "05:01:05"))
    pre = written["premarket"]["nasdaq"]["2026-11-27"]
    assert pre["session"] == "2026-11-25" and pre["point"] == "2026-11-27"
    after = {name: value for name, value in market.written if name == "afterhours"}["afterhours"]
    assert after["nasdaq"]["2026-11-25"]["point"] == "2026-11-27"


def test_futures_window_moves_only_nasdaq(market):
    traded(market, "2026-11-20", "15:59:30")
    live.tick(at("2026-11-20", "16:05:05"))
    traded(market, "2026-11-20", "19:59:50", 1.01)
    last = live.tick(at("2026-11-20", "20:00:10"))["afterhours"]
    nasdaq, biotech = last["nasdaq"]["2026-11-20"], last["biotech"]["2026-11-20"]
    market.toss.clear()
    market.spark = {"NQ=F": [(at("2026-11-20", "16:58"), 1000.0), (at("2026-11-20", "16:59"), 1002.0)]}
    assert live.tick(at("2026-11-20", "20:30:05")) == {}  # 애프터장 마지막 체결 뒤 선물 체결이 없으면 바꾸지 않는다
    market.spark["NQ=F"] += [(at("2026-11-22", "18:00"), 1010.0), (at("2026-11-22", "18:59"), 1020.0), (at("2026-11-22", "19:00"), 1030.0)]
    written = live.tick(at("2026-11-22", "19:00:05"))  # 일요일 19:00 ET
    moved = written["afterhours"]["nasdaq"]["2026-11-20"]
    assert moved["basis"] == "futures" and moved["futures_time"] == "2026-11-22T19:00:00-05:00"  # 19:00에 시작한 봉은 아직 끝나지 않았다
    assert moved["ratio"] == round(nasdaq["ratio"] * 1020.0 / 1002.0, 6)
    assert moved["time"] == nasdaq["time"] and moved["stocks"] == nasdaq["stocks"] and moved["point"] == "2026-11-23"
    assert written["afterhours"]["biotech"]["2026-11-20"] == biotech  # 바이오에는 선물이 없다
    assert live.tick(at("2026-11-22", "19:00:35")) == {}  # 같은 봉이면 다시 쓰지 않는다
    assert market.toss == [] and market.accounts == []
    assert market.indexes[-3:] == ["5d", "1d", "1d"]  # 기준을 잡는 첫 회차만 닷새치를 받는다


def test_no_futures_between_weekday_sessions(market):
    traded(market, "2026-11-18", "19:59:50")
    live.tick(at("2026-11-18", "20:00:10"))
    market.spark = {"NQ=F": minutes("2026-11-18", "19:50", "23:59", 1000.0, 1.0) + minutes("2026-11-19", "00:00", "03:59", 2000.0, 1.0)}
    market.written.clear()
    for clock in ("00:00:05", "02:00:05", "03:59:05"):
        assert live.tick(at("2026-11-19", clock)) == {}
    assert live.futures_window(at("2026-11-19", "02:00:05"), live.calendar_day(dt.date(2026, 11, 19))) is None
    assert live.futures_window(at("2026-11-23", "02:00:05"), live.calendar_day(dt.date(2026, 11, 23))) == ("2026-11-20", "2026-11-23")
    assert "futures" not in str(market.written)


def test_index_value_and_tick_log(market):
    traded(market, "2026-11-19", "09:40:00")
    market.spark = {"^NDX": minutes("2026-11-19", "09:30", "09:40", 1000.0, 1.0), "CL=F": minutes("2026-11-19", "09:30", "09:40", 60.0, 0.01)}
    first = live.tick(at("2026-11-19", "09:41:05"))["index"]
    assert first["^NDX"] == {"price": 1010.0, "time": "2026-11-19T09:40:00-05:00", "loaded": "2026-11-19T09:41:05-05:00"}
    assert set(first) == {"^NDX", "CL=F"}  # 1분봉이 없는 ^NBI는 적지 않는다
    market.spark["CL=F"] += [(at("2026-11-19", "09:41"), 61.0)]
    second = live.tick(at("2026-11-19", "09:42:05"))["index"]
    assert second["^NDX"] == first["^NDX"] and second["CL=F"]["loaded"] == "2026-11-19T09:42:05-05:00"  # 바뀐 지수만 받은 시각을 갈아 적는다
    assert "index" not in live.tick(at("2026-11-19", "09:43:05"))  # 1분봉 시각이 그대로면 쓰지 않는다
    records = [live.json.loads(line) for line in (live.DATA / "tick-2026-11-19.log").read_text().splitlines()]
    assert [record["index"] for record in records] == [1, 1, 1] and [record["calls"]["prices"] for record in records] == [1, 1, 1]
    assert "1010" not in (live.DATA / "tick-2026-11-19.log").read_text()  # 회차 기록에 가격을 쓰지 않는다


def test_old_values_get_points(market):
    (live.DATA / "afterhours.json").write_text('{"nasdaq": {"2026-11-18": {"time": "2026-11-18T20:00:00-05:00", "ratio": 1.0, "stocks": {}}}}')
    traded(market, "2026-11-19", "16:59:40")
    after = live.tick(at("2026-11-19", "17:00:05"))["afterhours"]["nasdaq"]
    assert after["2026-11-18"]["point"] == "2026-11-19" and after["2026-11-19"]["point"] == "2026-11-20"


def test_main_prints_only_toss_rounds(market, monkeypatch, capsys):
    tick = live.tick
    monkeypatch.setattr(live.sys, "argv", ["live.py"])
    traded(market, "2026-11-20", "19:59:50")
    live.tick(at("2026-11-20", "20:00:10"))
    market.spark = {"NQ=F": [(at("2026-11-20", "16:59"), 1000.0), (at("2026-11-22", "18:30"), 1010.0)]}
    monkeypatch.setattr(live, "tick", lambda toss: tick(at("2026-11-22", "19:00:05"), toss))
    live.main()
    assert capsys.readouterr().out == ""  # 선물 시간대 회차는 계좌 요약을 부르지 않게 아무것도 내지 않는다
    assert any(name == "afterhours" and "futures" in str(value) for name, value in market.written)
    traded(market, "2026-11-23", "05:00:30")
    monkeypatch.setattr(live, "tick", lambda toss: tick(at("2026-11-23", "05:01:05"), toss))
    live.main()
    assert capsys.readouterr().out.split() == ["premarket"]


ETF_TABLE = {"nasdaq": {"SAMPA": 1.0, "SAMPB": 2.0}, "biotech": {"SAMPC": 1.0}}  # 지어낸 심볼과 배율


def test_etf_table_reads_private_file(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "ETFS", tmp_path / "etfs.json")
    assert live.etf_table() == {}
    (tmp_path / "etfs.json").write_text(live.json.dumps(ETF_TABLE))
    assert live.etf_table() == ETF_TABLE


def test_futures_round_posts_account_prices_from_last_trades(market, monkeypatch):
    """선물 시간대: 나스닥 ETF 가격은 마지막 체결가 × (1 + 배율 × 선물 등락), 바이오와 그 밖의 보유 종목은 마지막 체결가 그대로다."""
    (live.ETFS).write_text(live.json.dumps(ETF_TABLE))
    monkeypatch.setattr(live, "holding_symbols", lambda: ["SAMPB", "SAMPC", "SAMPD"])
    traded(market, "2026-11-20", "15:59:30")
    market.prices.update({symbol: (price, kst("2026-11-20", "15:59:30")) for symbol, price in (("SAMPA", 100.0), ("SAMPB", 50.0), ("SAMPC", 20.0), ("SAMPD", 100.0))})
    live.tick(at("2026-11-20", "16:05:05"))
    traded(market, "2026-11-20", "19:59:50", 1.01)
    market.prices.update({symbol: (price, kst("2026-11-20", "19:59:50")) for symbol, price in (("SAMPA", 100.0), ("SAMPB", 50.0), ("SAMPC", 20.0), ("SAMPD", 100.0))})
    live.tick(at("2026-11-20", "20:00:10"))
    assert set(market.accounts[-1][1]) == {"SAMPA", "SAMPB", "SAMPC", "SAMPD"}  # 보유하지 않은 기준 묶음 ETF도 받는다
    market.accounts.clear()
    market.toss.clear()
    market.spark = {"NQ=F": [(at("2026-11-20", "16:58"), 1000.0), (at("2026-11-20", "16:59"), 1002.0),
                             (at("2026-11-22", "18:00"), 1010.0), (at("2026-11-22", "18:59"), 1020.0), (at("2026-11-22", "19:00"), 1030.0)]}
    market.written.clear()
    live.tick(at("2026-11-22", "19:00:05"))
    (when, prices), = market.accounts
    move = 1020.0 / 1002.0 - 1
    assert when == "2026-11-22T19:00:05-05:00"
    assert prices["SAMPA"] == pytest.approx(100.0 * (1 + move)) and prices["SAMPB"] == pytest.approx(50.0 * (1 + 2.0 * move))
    assert prices["SAMPC"] == 20.0 and prices["SAMPD"] == 100.0  # 바이오와 나스닥이 아닌 보유 종목은 마지막 체결가 그대로다
    assert market.toss == []  # 선물 시간대에는 토스를 부르지 않는다
    live.tick(at("2026-11-22", "19:00:35"))  # 새 선물 봉이 없어도 마지막 체결가로 계속 쓴다
    assert len(market.accounts) == 2 and market.accounts[-1][1]["SAMPA"] == prices["SAMPA"]
    published = str(market.written) + (live.DATA / "afterhours.json").read_text()
    assert not any(symbol in published for symbol in ("SAMPA", "SAMPB", "SAMPC", "SAMPD"))  # invest-live 값에는 계좌 값이 없다


def test_futures_round_without_last_trades_posts_nothing(market):
    (live.ETFS).write_text(live.json.dumps(ETF_TABLE))
    traded(market, "2026-11-20", "19:59:50")
    live.tick(at("2026-11-20", "20:00:10"))
    market.spark = {"NQ=F": [(at("2026-11-20", "16:59"), 1000.0), (at("2026-11-22", "18:30"), 1010.0)]}
    live.tick(at("2026-11-22", "19:00:05"))
    assert market.accounts == []


def test_regular_round_also_prices_etfs_not_held(market, monkeypatch):
    (live.ETFS).write_text(live.json.dumps(ETF_TABLE))
    monkeypatch.setattr(live, "holding_symbols", lambda: ["SAMPB"])
    market.prices = {"QQQ": (501.0, kst("2026-11-19", "09:40:00")), "SAMPA": (100.0, None), "SAMPB": (50.0, None), "SAMPC": (20.0, None)}
    live.tick(at("2026-11-19", "09:41:05"))
    assert market.accounts == [("2026-11-19T09:41:05-05:00", {"SAMPA": 100.0, "SAMPB": 50.0, "SAMPC": 20.0})]
    assert all("SAMP" not in str(value) for _, value in market.written)
