"""build.py 시험. invest-live Worker는 가짜로 바꾸고, 시각은 `build.dt`를 바꿔 고정한다."""
import datetime as dt
import html
import json
import re
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


def test_progress_counts_the_coordination_stage(worker, monkeypatch, tmp_path):
    frozen(monkeypatch, "2026-11-23T20:40:00")  # 서울 11/24 10:40
    folder = tmp_path / "vault" / "routine/invest/2026-11/2026-11-24/nasdaq"
    (folder / "system").mkdir(parents=True)
    for offset, name in enumerate(("input-manifest.json", "system/form-draft.md", "scratchpad.md", "system/cards-first.json")):
        path = folder / name
        path.write_text("{}", encoding="utf-8")
        moment = dt.datetime(2026, 11, 24, 10, offset * 10, tzinfo=build.SEOUL).timestamp()
        build.os.utime(path, (moment, moment))
    monkeypatch.setattr(build, "published_entries", lambda out: {})
    monkeypatch.setattr(build, "progress_plan", lambda vault, entries, today: [0])
    found = build.progress(tmp_path / "vault", tmp_path)["indexes"]["nasdaq"]
    assert build.PROGRESS_MARKS[found["step"]][0] == "system/cards-first.json"
    assert found["since"] == "2026-11-24T10:30:00+09:00"


def past_session(vault: Path, date: str, coordination: dict[str, str]) -> dict:
    """지난 세션 하나의 도구 호출 요약과 조정 파일. 10:00에 시작해 11:30에 끝나고 11:40에 리포트를 올렸다."""
    folder = vault / f"routine/invest/{date[:7]}/{date}/nasdaq"
    (folder / "system").mkdir(parents=True)
    calls = [("10:20:00", "Write  ok  /x/system/form-draft.md"), ("10:30:00", "Write  ok  /x/scratchpad.md"),
             ("11:10:00", "Write  ok  /x/report.md"), ("11:15:00", "Agent[invest-style]  ok  교정"),
             ("11:20:00", "Agent[invest-image]  ok  그림")]
    lines = ["# 도구 호출 요약", "# 세션 s", "# 10:00:00 ~ 11:30:00 KST · 호출 5회", ""] + [f"{at}  main  {call}" for at, call in calls]
    (folder / "system/invest-report-nasdaq-tools.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, clock in coordination.items():
        path = folder / name
        path.write_text("{}", encoding="utf-8")
        moment = dt.datetime.fromisoformat(f"{date}T{clock}").replace(tzinfo=build.SEOUL).timestamp()
        build.os.utime(path, (moment, moment))
    return {"date": date, "index": "nasdaq", "written": f"{date} 11:40"}


def test_progress_plan_measures_the_coordination_stage_from_its_files(tmp_path):
    vault = tmp_path / "vault"
    entries = {"a": past_session(vault, "2026-11-20", {"system/cards-first.json": "10:40:00", "system/confirmed-events.json": "10:50:00"})}
    assert build.progress_plan(vault, entries, dt.date(2026, 11, 24)) == [0, 20, 30, 40, 50, 70, 75, 80, 90, 100]


def test_progress_plan_gives_a_session_without_cards_no_coordination_minutes(tmp_path):
    vault = tmp_path / "vault"
    entries = {"a": past_session(vault, "2026-11-20", {}),
               "b": past_session(vault, "2026-11-21", {"system/cards-first.json": "09:50:00"})}
    assert build.progress_plan(vault, entries, dt.date(2026, 11, 24)) == [0, 20, 30, 30, 30, 70, 75, 80, 90, 100]


def test_realized_reads_only_resolved_entries_with_a_branch(tmp_path):
    vault = tmp_path / "vault"
    source = build.report_path(vault, dt.date(2026, 11, 20), "biotech")
    source.parent.mkdir(parents=True)
    source.with_name("tree.json").write_text(json.dumps({"issues": [
        {"id": "FF-044-3", "name": "이란 본토 타격", "branches": [{"id": "FF-044-3.b1", "name": "타격 재개"}]},
        {"id": "FF-046-1", "name": "버텍스 실적", "branches": [{"id": "FF-046-1.b1", "name": "매출 상회"}]}]}, ensure_ascii=False), encoding="utf-8")
    later = build.report_path(vault, dt.date(2026, 11, 23), "biotech").with_name("tree.json")
    later.parent.mkdir(parents=True)
    later.write_text(json.dumps({"resolved": [{"id": "FF-044-3", "dropped": "두 사건으로 나눴다"},
                                              {"id": "FF-046-1", "branch": "FF-046-1.b1", "outcome": "매출이 컨센서스를 넘었다"}]},
                                ensure_ascii=False), encoding="utf-8")
    found = [build.realized(vault, "biotech", source, name, dt.date(2026, 11, 21), dt.date(2026, 11, 24)) for name in ("이란 본토 타격", "버텍스 실적")]
    assert found == [None, {"id": "FF-046-1", "branch": "매출 상회", "outcome": "매출이 컨센서스를 넘었다"}]


def split_vault(vault: Path) -> None:
    """11/20에 이란 합의(FF-044-3)를 적은 바이오 리포트, 11/21에 그 사안을 새 항목 FF-047의 사안 FF-047-1로 나눈 나무, 11/24에 FF-047-1을 해소한 나무."""
    def write(day: str, name: str, value) -> None:
        path = vault / f"routine/invest/2026-11/{day}/biotech/{name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False), encoding="utf-8")

    origin = {"id": "FF-044-3", "name": "이란 합의 발표", "item": "FF-044", "announced": "2026-11-22 10:00",
              "branches": [{"id": "FF-044-3.b1", "name": "합의", "outcome": "EV-007-o1"}, {"id": "FF-044-3.b2", "name": "결렬", "outcome": "EV-007-o2"}]}
    split = {"id": "FF-047-1", "name": "이란 합의 발표", "item": "FF-047", "from": ["FF-044-3"], "announced": "2026-11-22 10:00",
             "branches": [{"id": "FF-047-1.b1", "name": "합의 서명", "outcome": "EV-007-o1"}, {"id": "FF-047-1.b2", "name": "협상 결렬", "outcome": "EV-007-o2"}]}
    write("2026-11-20", "tree.json", {"issues": [origin]})
    write("2026-11-20", "system/issues.json", {"issues": [{"issue": 1, "id": "FF-044", "nodes": ["FF-044"]}]})
    write("2026-11-21", "tree.json", {"issues": [split]})
    write("2026-11-21", "system/issues.json", {"issues": [{"issue": 1, "id": "FF-047", "nodes": ["FF-047"]}]})
    write("2026-11-24", "tree.json", {"issues": [], "resolved": [{"id": "FF-047-1", "branch": "FF-047-1.b1", "outcome": "합의문에 서명했다"}]})
    write("2026-11-24", "system/issues.json", {"issues": [{"issue": 1, "id": "FF-047", "nodes": ["FF-047"]}]})


def test_lineage_joins_a_split_issue_to_its_origin(tmp_path):
    vault = tmp_path / "vault"
    split_vault(vault)
    lineage = build.issue_lineage(vault, "biotech", dt.date(2026, 11, 24))
    assert build.lineage_items(lineage, "FF-047") == {"FF-047", "FF-044"}
    assert build.lineage_items(lineage, "FF-044") == {"FF-044"}
    assert build.origins(lineage, {"FF-047-1"}) == {"FF-047-1", "FF-044-3"}
    source = build.report_path(vault, dt.date(2026, 11, 20), "biotech")
    found = build.realized(vault, "biotech", source, "이란 합의 발표", dt.date(2026, 11, 22), dt.date(2026, 11, 24))
    assert found == {"id": "FF-047-1", "branch": "합의", "outcome": "합의문에 서명했다"}


def test_issue_history_follows_the_origin_of_a_split_issue(tmp_path):
    vault, out = tmp_path / "vault", tmp_path / "out"
    split_vault(vault)
    for day in ("20261120", "20261121"):
        page = out / "r" / f"{day}-biotech" / "report.html"
        page.parent.mkdir(parents=True)
        page.write_text(f'<h2 id="상세-이슈-해설">상세 이슈 해설</h2>\n<h3 data-issue="{"FF-044" if day == "20261120" else "FF-047"}">1. 이란</h3>\n<p>{day}</p>\n',
                        encoding="utf-8")
    history = build.issue_history(vault, "biotech", dt.date(2026, 11, 24), out)
    assert [(str(when), number) for when, number, _ in history["FF-047"]] == [("2026-11-20", 1), ("2026-11-21", 1)]


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


NEWS = """---
created: 2026-11-20
---

# 종목 뉴스 2026-11-20-18 nasdaq-1

## 상세 이슈 해설
---

### 1. 엔비디아 칩 수출 허가

요약: 미국 상무부가 엔비디아의 칩 수출을 "절반"만 허가했다. 엔비디아는 남은 물량을 다른 고객에게 돌렸다.

- 상무부 심사에 의문이 커졌다
- 허가 물량은 지난해의 절반이다
- 엔비디아는 **다른 고객**으로 물량을 돌린다

#### <mark>이슈 해설</mark>

리드 문단이다.

첫 문단이다. 엔비디아는 가이던스를 냈다.

##### 허가 물량

셋째 문단이다.

넷째 문단에 대형 주문과 계좌가 나온다.

##### 엔비디아의 답

다섯째 문단이다.

### 2. 연준 회의 `양방향` `중요도 높음`

#### <mark>이슈 해설</mark> 금리 동결 전망

한 문단뿐이다.
"""


def article_folder(tmp_path: Path, charts: list[dict]) -> Path:
    folder = tmp_path / "nasdaq-1"
    (folder / "system").mkdir(parents=True)
    (folder / "news.md").write_text(NEWS, encoding="utf-8")
    (folder / "system" / "terms.json").write_text(json.dumps({"terms": [
        {"section": "상세 이슈 해설", "block": "1. 엔비디아 칩 수출 허가", "form": "가이던스", "nth": 0, "id": "guidance", "term": "가이던스", "desc": "실적 전망"}]},
        ensure_ascii=False), encoding="utf-8")
    (folder / "system" / "issue-charts.json").write_text(json.dumps({"charts": [{"card": card} for card in charts]}, ensure_ascii=False), encoding="utf-8")
    return folder


def test_issue_articles_read_each_article(tmp_path):
    folder = article_folder(tmp_path, [{"issue": 1, "after": 3}])
    found = build.issue_articles(folder / "news.md", folder, Path.home() / "obsidian-vault")
    assert [(item["issue"], item["title"], item["headline"]) for item in found] == [(1, "엔비디아 칩 수출 허가", ""), (2, "연준 회의", "금리 동결 전망")]
    assert [item["summary"] for item in found] == ['미국 상무부가 엔비디아의 칩 수출을 "절반"만 허가했다. 엔비디아는 남은 물량을 다른 고객에게 돌렸다.', ""]
    assert found[0]["subheads"] == ["상무부 심사에 의문이 커졌다", "허가 물량은 지난해의 절반이다", "엔비디아는 다른 고객으로 물량을 돌린다"]
    assert found[1]["subheads"] == []  # 제목과 말머리 사이에 목록이 없는 기사
    first = found[0]["html"]
    assert first.startswith("<p>리드 문단이다.</p>")  # 말머리 뒤 본문만 담는다
    assert "요약:" not in first
    assert "<ul>" not in first
    assert [line for line in first.splitlines() if line.startswith("<h5")] == ["<h5>허가 물량</h5>", "<h5>엔비디아의 답</h5>"]
    assert ' id="' not in first
    assert first.count('<button class="term"') == 1 and first.count('class="issue-chart"') == 1
    assert "대형 주문과 계좌" in first  # 공개본 금지어는 검사하지 않는다
    assert found[1]["html"] == "<p>한 문단뿐이다.</p>"


def blocks(html_body: str) -> list[str]:
    """문단은 `p`, 소제목은 `h5`, 그래프 카드는 `chart`로 줄인 이슈 1 본문의 차례."""
    return ["chart" if tag == "figure" else tag for tag in re.findall(r"<(p|h5|figure)\b", html_body)]


@pytest.mark.parametrize("after, order", [
    (1, ["p", "chart", "p", "h5", "p", "p", "h5", "p"]),
    (2, ["p", "p", "h5", "p", "chart", "p", "h5", "p"]),  # 둘째 문단 바로 뒤가 소제목이라 다음 문단 사이로 미룬다
    (3, ["p", "p", "h5", "p", "chart", "p", "h5", "p"]),  # 소제목은 문단으로 세지 않는다
    (4, ["p", "p", "h5", "p", "p", "h5", "p", "chart"]),
    (9, ["p", "p", "h5", "p", "p", "h5", "p", "chart"]),  # 문단이 그보다 적으면 마지막 문단 뒤
])
def test_issue_charts_sit_between_paragraphs(tmp_path, after, order):
    folder = article_folder(tmp_path, [{"issue": 1, "after": after}])
    assert blocks(build.issue_articles(folder / "news.md", folder, Path.home() / "obsidian-vault")[0]["html"]) == order


@pytest.mark.parametrize("after, at", [(2, "<p>2</p>"), (5, "<p>3</p>")])
def test_issue_charts_without_subheads_count_every_paragraph(tmp_path, after, at):
    body = ('<h2 id="상세-이슈-해설">상세 이슈 해설</h2>\n<h3 id="a">1. 가</h3>\n<h4 id="b"><mark>이슈 해설</mark> 나</h4>\n'
            + "".join(f"<p>{k}</p>\n" for k in range(1, 4)) + '<h2 id="다음">다음</h2>\n')
    card = {"issue": 1, "after": after}
    plan = tmp_path / "issue-charts.json"
    plan.write_text(json.dumps({"charts": [{"card": card}]}), encoding="utf-8")
    figure = f'\n<figure class="issue-chart" data-card="{html.escape(json.dumps(card))}"></figure>'
    assert build.mark_issue_charts(body, plan) == body.replace(at, at + figure)


def test_issue_images_put_the_body_image_after_the_heading_and_the_cover_on_the_heading(tmp_path):
    from PIL import Image
    assets, target, out = tmp_path / "assets", tmp_path / "out" / "r" / "k", tmp_path / "out"
    assets.mkdir()
    target.mkdir(parents=True)
    for name in ("issue-1-1.webp", "issue-1-2.webp", "issue-2-1.webp"):
        Image.new("RGB", (16, 9)).save(assets / name, format="WEBP")
    plan = tmp_path / "issue-images.json"
    plan.write_text(json.dumps({"issues": [{"issue": 1, "images": [{"caption": "본문 그림 설명"}, {"caption": "목록 그림 설명"}]}]}, ensure_ascii=False), encoding="utf-8")
    body = '<h2 id="상세-이슈-해설">상세 이슈 해설</h2>\n<h3 data-issue="a">1. 첫 이슈</h3>\n<p>본문</p>\n<h3>2. 둘째 이슈</h3>\n<p>본문</p>\n'
    marked = build.mark_issue_images(body, assets, plan, target, out)
    first, second = marked.split("<h3")[1:]
    assert re.match(r' data-cover="r/k/issue-1-2\.webp\?v=\w+" data-issue="a">', first)
    assert first.count('class="photo"') == 1 and "issue-1-1.webp" in first and "본문 그림 설명" in first and "목록 그림 설명" not in first
    assert "data-cover" not in second and second.count('class="photo"') == 1
    assert "data-thumb" not in marked


def test_carried_issue_keeps_the_cover_of_the_report_that_wrote_it(tmp_path):
    out = tmp_path / "out"
    earlier = out / "r" / "20261123-nasdaq"
    earlier.mkdir(parents=True)
    (earlier / "report.html").write_text('<h2 id="상세-이슈-해설">상세 이슈 해설</h2>\n<h3 data-cover="r/20261123-nasdaq/issue-2-2.webp" data-issue="x">2. 옛 이슈</h3>\n<p>옛 본문</p>\n',
                                         encoding="utf-8")
    bundles = tmp_path / "issues.json"
    bundles.write_text(json.dumps({"issues": [{"issue": 1, "id": "x", "carry": {"date": "2026-11-23", "issue": 2}}]}), encoding="utf-8")
    body = '<h2 id="상세-이슈-해설">상세 이슈 해설</h2>\n<h3 data-issue="x" data-summary="요약이다.">1. 옮긴 이슈</h3>\n<p>오늘 본문</p>\n'
    marked = build.mark_issue_carry(body, bundles, "nasdaq", out)
    assert '<h3 data-cover="r/20261123-nasdaq/issue-2-2.webp" data-issue="x" data-summary="요약이다.">1. 옮긴 이슈</h3>' in marked
    assert "옛 본문" in marked and "오늘 본문" not in marked
