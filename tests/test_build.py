"""build.py 시험. invest-live Worker는 가짜로 바꾸고, 시각은 `build.dt`를 바꿔 고정한다."""
import datetime as dt
import json
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


@pytest.mark.parametrize("flag", ["--stage", "--premarket", "--afterhours"])
def test_old_flags_are_gone(monkeypatch, flag):
    monkeypatch.setattr(sys, "argv", ["build.py", "--date", "2026-11-20", "--index", "nasdaq", flag, "pre"])
    with pytest.raises(SystemExit) as raised:
        build.main()
    assert raised.value.code == 2


def test_market_flag_writes_only_the_market_pages(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(build, "market", lambda vault, out: called.append(out) or out / "r" / "market.json")
    monkeypatch.setattr(build, "build", lambda *args: pytest.fail("--market은 리포트를 만들지 않는다"))
    monkeypatch.setattr(sys, "argv", ["build.py", "--market", "--out", str(tmp_path)])
    assert build.main() == 0
    assert called == [tmp_path]


def bands(folder: Path, base: str) -> Path:
    folder.mkdir(parents=True)
    (folder / "path-bands.json").write_text(json.dumps({"price_base_date": base}), encoding="utf-8")
    return folder


@pytest.mark.parametrize("base, point", [("2026-11-13", "2026-11-16"),  # 금요일 세션 뒤 판단은 월요일 세션이다
                                         ("2026-11-25", "2026-11-27"),  # 추수감사절 휴장을 건너뛴다
                                         ("2026-11-18", "2026-11-19")])
def test_judgment_point_is_the_next_session(tmp_path, base, point):
    assert build.judgment_point(bands(tmp_path / "nasdaq", base)) == point


def outlook_body(names: list[str]) -> str:
    parts = [f'<h3 id="{name}"><mark>{name}</mark> 말머리</h3>\n<p>{name} 본문</p>\n' for name in names]
    return ('<h2 id="요약">요약</h2>\n<h3 id="현재-상태"><mark>현재 상태</mark></h3>\n<p>다른 절</p>\n'
            '<h2 id="1개월-지수-방향-예측">1개월 지수 방향 예측</h2>\n' + "".join(parts) + '<h2 id="이벤트-캘린더">이벤트 캘린더</h2>\n<p>뒤 절</p>\n')


def test_outlook_sections_copy_the_three_sections():
    found = build.outlook_sections(outlook_body(["현재 상태", "지수 영향", "주요 분기와 예측", "종합 시나리오"]), "2026-11-16")
    assert found["point"] == "2026-11-16"
    assert list(found["sections"]) == list(build.OUTLOOK_SECTIONS)
    assert found["sections"]["현재 상태"] == '<h3 id="현재 상태"><mark>현재 상태</mark> 말머리</h3>\n<p>현재 상태 본문</p>'  # 다른 절의 같은 소제목은 쓰지 않는다
    assert found["sections"]["종합 시나리오"].endswith("<p>종합 시나리오 본문</p>")  # 다음 h2 앞에서 끊는다


def test_outlook_sections_need_all_three_sections():
    assert build.outlook_sections(outlook_body(["현재 상태", "주요 분기와 예측", "지수 영향"]), "2026-11-16") is None


@pytest.mark.parametrize("published, running", [({}, ["biotech", "nasdaq"]), ({"20261120-nasdaq": {}}, ["biotech"]),
                                                ({"20261120-nasdaq": {}, "20261120-biotech": {}}, [])])
def test_progress_runs_for_indexes_without_a_report(worker, monkeypatch, tmp_path, published, running):
    frozen(monkeypatch, "2026-11-19T20:30:00")  # 서울 11/20 10:30
    for index in ("nasdaq", "biotech"):
        folder = tmp_path / "vault" / f"routine/invest/2026-11/2026-11-20/{index}"
        folder.mkdir(parents=True)
        (folder / "input-manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(build, "published_entries", lambda out: published)
    monkeypatch.setattr(build, "progress_plan", lambda vault, entries, today: [0])
    value = build.progress(tmp_path / "vault", tmp_path)
    assert (sorted(value["indexes"]) if value else []) == running
    assert all(item["step"] == 0 for item in (value or {"indexes": {}})["indexes"].values())


def test_rewind_keeps_one_frame_per_point(monkeypatch, tmp_path):
    vault, out = tmp_path / "vault", tmp_path / "out"
    for day, base in (("2026-11-13", "2026-11-12"), ("2026-11-14", "2026-11-13"), ("2026-11-16", "2026-11-13")):
        bands(vault / f"routine/invest/2026-11/{day}/nasdaq", base)
        (out / "r" / f"{day.replace('-', '')}-nasdaq").mkdir(parents=True)
    monkeypatch.setattr(build, "card_scale", lambda index, vault: 1.0)
    monkeypatch.setattr(build, "card_frame", lambda date, folder, scale: {"date": date, "base_date": date, "days": [], "base": 1.0, "tree": {}})
    monkeypatch.setattr(build, "predictions_chart", lambda vault: types.SimpleNamespace(
        path_bands=types.SimpleNamespace(REFERENCE_DB_PATH=None, SECTOR_DB_TICKERS={"nasdaq": "^NDX"})))
    monkeypatch.setattr(build, "actual_returns", lambda *args: [])
    monkeypatch.setattr(build, "indicator_cards", lambda vault, index, day: {})
    build.rewind("nasdaq", vault, out)
    frames = json.loads((out / "r/rewind-nasdaq/cards.json").read_text(encoding="utf-8"))["frames"]
    assert [(frame["point"], frame["date"]) for frame in frames] == [("2026-11-13", "2026-11-13"), ("2026-11-16", "2026-11-16")]
