"""build.py가 invest-live Worker와 주고받는 실시간 값 시험. Worker는 가짜로 바꾸고, 시각은 `build.dt`를 바꿔 고정한다."""
import datetime as dt
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build  # noqa: E402

NY = build.NEW_YORK


def board() -> dict:
    return {"nasdaq": {"dates": ["2026-11-18", "2026-11-19"], "stocks": [{"symbol": "AAPL"}, {"symbol": "MSFT"}]},
            "biotech": {"dates": ["2026-11-18", "2026-11-19"], "stocks": [{"symbol": "AMGN"}]}}


PREVIOUS = {"nasdaq": {"dates": ["2026-11-17", "2026-11-18"], "stocks": [{"symbol": "AAPL", "after": [9.0, 10.0]},
                                                                         {"symbol": "MSFT", "after": [19.0, None]}]}}


def frozen(monkeypatch, clock: str) -> None:
    """build.py가 읽는 지금 시각(`dt.datetime.now`)을 뉴욕 시각 `clock`으로 고정한다."""
    moment = dt.datetime.fromisoformat(clock).replace(tzinfo=NY)

    class Clock(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return moment.astimezone(tz) if tz else moment.replace(tzinfo=None)

    monkeypatch.setattr(build, "dt", types.SimpleNamespace(datetime=Clock, date=dt.date, time=dt.time, timedelta=dt.timedelta))


@pytest.fixture
def worker(monkeypatch):
    """가짜 invest-live. `values`가 `GET /` 응답이고, `asked`에 읽은 횟수를, `written`에 쓴 값을 적는다."""
    class Worker:
        values, asked, written = {}, [], []

    monkeypatch.setattr(build, "read_live", lambda: Worker.asked.append(1) or Worker.values)
    monkeypatch.setattr(build, "post_live", lambda name, value: Worker.written.append((name, value)))
    Worker.asked, Worker.written = [], []
    return Worker


class Source:
    """`price_source`를 흉내 낸다. 심볼마다 정한 값을 돌려주고, 값이 없는 심볼은 두 출처가 모두 답하지 않은 것처럼 RuntimeError를 낸다."""

    def __init__(self, prices: dict):
        self.prices, self.asked = prices, []

    def batch_time_price(self, symbol: str, day: str, end: str) -> dict:
        self.asked.append((symbol, day, end))
        if symbol not in self.prices:
            raise RuntimeError(f"{symbol} 답 없음")
        return {"price": self.prices[symbol]}


def test_after_prices_takes_the_afterhours_close_price(monkeypatch):
    frozen(monkeypatch, "2026-11-19T20:30:00")
    source = Source({"AAPL": 11.004, "AMGN": 30.0})
    found = board()
    build.after_prices(found, PREVIOUS, source)
    assert found["nasdaq"]["stocks"][0]["after"] == [10.0, 11.0]  # 앞 날짜 값은 앞 지도에서 옮기고, 마지막 날짜 값은 둘째 자리로 반올림한다
    assert found["nasdaq"]["stocks"][1]["after"] == [None, None]  # 두 출처가 답하지 않은 종목은 null이다
    assert ("AAPL", "2026-11-19", "2026-11-19T20:00:00-05:00") in source.asked  # 끝 시각은 그날 20:00 ET다


def test_after_prices_waits_for_the_afterhours_close(monkeypatch):
    frozen(monkeypatch, "2026-11-19T19:30:00")
    source = Source({"AAPL": 11.0})
    build.after_prices(board(), PREVIOUS, source)
    assert source.asked == []


@pytest.mark.parametrize("value", [None, {"date": "2026-11-20", "plan": [0], "indexes": {}}])
def test_progress_writes_only_to_the_worker(worker, monkeypatch, capsys, value):
    monkeypatch.setattr(build, "progress", lambda vault, out: value)
    monkeypatch.setattr(sys, "argv", ["build.py", "--progress"])
    assert build.main() == 0
    assert worker.written == ([] if value is None else [("progress", value)])
    assert capsys.readouterr().out == ("progress\n" if value else "\n")


@pytest.mark.parametrize("flag", ["--premarket", "--afterhours"])
def test_old_live_flags_are_gone(monkeypatch, flag):
    monkeypatch.setattr(sys, "argv", ["build.py", flag])
    with pytest.raises(SystemExit) as raised:
        build.main()
    assert raised.value.code == 2
