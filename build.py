#!/usr/bin/env python3
"""build — 판단 리포트 공개본을 `invest-reports` `invest-reports` 미니 앱(`app.html`)이 읽는 HTML 조각으로 만든다. `run-with-notify.sh`의 `publish_miniapp`이 만든 조각을 게시한다.

사용법: python3 build.py --date 2026-10-19 --index nasdaq [--vault ~/obsidian-vault] [--out .]

`r/{YYYYMMDD}-{지수}/`에 `report.html`과 그림을 쓰고 `r/index.json`의 목록을 갱신한다. `invest-reports` 미니 앱은
`start_param`으로 받은 `{YYYYMMDD}-{지수}`를 열어 그 조각을 그린다.

공개본이 끝나는 자리와 공개본에 남으면 안 되는 말은 invest-report `report_pdf.py`의 값을 그대로 쓴다.
PDF와 `invest-reports` 미니 앱이 같은 자리에서 자르므로, 공개 채널로 나가는 두 판본의 내용이 같다.

`다가오는 이벤트` 표는 분기·확률·전개 예상 세 열이다. 휴대폰 폭에서 분기 이름이 접히지 않게 열마다
폭과 정렬을 정하는 이름표를 단다.

`다가오는 이벤트` 절에는 리포트 날짜 전 이틀 동안 발표된 이벤트도 넣는다. 리포트가 같은 사안 id의 이벤트를 이미
적었으면 리포트의 표만 둔다. 그 밖의 이벤트는 그 이벤트를 예측한 가장 최근 리포트의 표를 쓰고, 그 리포트의 사안 나무(`tree.json`)에서 이벤트의 사안 id를 찾아 뒤 사안 나무의 `resolved`가
그 id로 적은 실제 갈래 줄에 `hit` 이름표를 단다. `resolved`의 갈래는 갈래 id이므로, 표를 쓴 리포트의 사안 나무에서
그 id의 갈래 이름을 찾아 표의 줄과 잇는다. 갈래 id가 없는 앞 날짜 나무는 사안마다 나무 순서대로 `b1`부터 번호를 붙여
읽고, 갈래 id가 아닌 `resolved` 갈래는 이름으로 읽는다.
실제 갈래 줄의 전개 예상 뒤에는 `resolved`의 실제 전개(`outcome`)를 화살표와 함께 붙인다.
리포트 날짜와 그 뒤 이벤트의 표는 리포트 폴더 `system/display.json` `next`의 갈래 변화(`change`)를 확률 아래 작은 글씨로
붙인다. 표의 분기 이름이 모두 한 사안의 갈래 이름이면 그 사안의 표로 본다. 오르면 `▲`, 내리면 `▼`와 %p 차이를 쓰고,
변화가 없으면 `–`, 어제 나무에 없던 갈래는 `신규`, 오늘 다시 정의한 갈래는 `재정의`를 쓴다.
이벤트 소제목마다 발표일을 `data-day`로 달고 제목에서는 날짜를 지운다. `invest-reports` 미니 앱은 이 값으로 날짜 띠를 그리고
같은 날 이벤트를 한 장에 모은다. 제목 위에는 사안 나무의 발표 시각(`announced`)을 한국 시각(KST)으로 적는다.
발표 시각이 수집기가 채운 기본값(`PLACEHOLDER_TIMES`)이거나 사안 나무에 없으면 장전·장중·장후만 적는다.
중요도는 `data-level`로 달아 `invest-reports` 미니 앱이 날짜 띠에 점으로 그린다.

`r/index.json`에는 리포트마다 제목, 날짜 줄(`day`), 처음 만든 시각(`written`, 서울 시각)을 적는다. `invest-reports` 미니 앱은 제목 아래
작은 글씨로 날짜 줄과 처음 만든 시각을 그린다. 같은 리포트를 다시 만들어도 처음 만든 시각은 그대로 둔다.
`moves`에는 리포트 날짜 전날 정규장 종가의 앞 세션 종가 대비 등락률(`session`, %)과 기준 가격의 기준 가격 날짜 종가 대비
등락률(`after`, %)을 적는다. 전날이 휴장일이면 `session`은 `null`이다. 두 등락률은 `path-bands.json`의 ^NDX·^NBI 환산 가격과 `reference.db` 환산 종가로 재므로
6M + Predictions 그림의 종가 선과 기준 가격 차이와 같다. `invest-reports` 미니 앱은 날짜 줄 아래 회색 글씨로
`정규장`과 `장 마감 후` 등락률을 적고 등락률만 오르면 빨강, 내리면 파랑으로 칠한다. `null`은 `—`로 적는다.

`r/rewind-{지수}/`에는 지난 판단으로 되감는 슬라이더의 값을 쓴다. 되감기 날짜는 공개본이 있는 그 지수 리포트 가운데
가장 늦은 날짜에서 `REWIND_DAYS`일 안이고, `system/simulation.json`의 `quantiles`와 `system/tree-axes.json`이 있는
날짜다. `predict.png`는 가장 늦은 날짜의 6M + Predictions 그림에서 종가 선과 오늘 판단을 지운 바탕이고
(`predictions_chart.rewind`), `frames.json`은 바탕의 축 위치·종가와 날짜마다 6M + Predictions 범위, 그날 Montecarlo 그림과
축 위치, 그날 기준 가격 뒤의 실제 종가 수익률(%), 그날 권장 추종 배율 그림을 담는다. Montecarlo·권장 추종 배율 그림은
그날 공개본 폴더의 그림을 그대로 가리킨다. `invest-reports` 미니 앱은 슬라이더를 옮길 때 바탕 위에 그날 범위를 그리고,
그날 Montecarlo 그림 위에 실제 종가 선을 그린다.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
TABLE_RE = re.compile(r"<table>.*?</table>", re.DOTALL)
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
CELL_RE = re.compile(r"<t([hd])\b[^>]*>(.*?)</t\1>", re.DOTALL)
EVENT_HEADER = ["분기", "확률", "전개 예상"]
EVENTS_TITLE = "다가오는 이벤트"
# 이벤트 소제목 앞의 발표일. `2026-10-21(수)`, `2026-10-21(수)~10-28(수)`, `10/26(월) 장전` 꼴이다.
EVENT_DAY_RE = re.compile(r"^(?:(\d{4})-)?(\d{1,2})[-/](\d{1,2})\([^)]*\)(?:~\S+)?\s*(?:(장전|장중|장후)\s+)?")
LEVEL_RE = re.compile(r"\s*`중요도 ([^`]*)`")
LEVELS = {"높음": "high", "보통": "mid", "낮음": "low"}  # 소제목 중요도 표식의 말과 `data-level` 값
PAST_DAYS = 2  # 리포트 날짜 전 며칠 동안 발표된 이벤트를 넣는지
LOOKBACK = 7  # 지난 이벤트의 표를 찾을 때 거슬러 보는 리포트 날짜 수
REGULAR_OPEN, REGULAR_CLOSE = "09:30", "16:00"  # 뉴욕 정규장 시각. 발표 시각을 장전·장중·장후로 나눈다
# 발표 시각을 모를 때 채우는 뉴욕 시각. 실적의 장전(bmo)·장후(amc) 단서는 `calendar_store.py`가 08:00·16:05로,
# 장중(dmh)은 `render_inputs.py`가 12:00으로 채우고, 단서가 없는 발표는 16:00으로 적는다. 이 시각은 장 구분만 적는다.
PLACEHOLDER_TIMES = {"08:00", "12:00", "16:00", "16:05"}
NEW_YORK, SEOUL = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")
# 리포트 제목 끝의 날짜 줄. `나스닥 리포트 2026-10-22 (목)` 꼴이다.
TITLE_RE = re.compile(r"^(.*\S)\s+(\d{4}-\d{2}-\d{2} \([^)]*\))$")
REWIND_DAYS = 30  # 되감기 슬라이더가 거슬러 가는 날짜 범위


def report_pdf(vault: Path):
    sys.path.insert(0, str(vault / "agent/skills/tool/invest-report/scripts"))
    import report_pdf as module
    return module


def predictions_chart(vault: Path):
    sys.path.insert(0, str(vault / "agent/skills/tool/invest-report/scripts"))
    import predictions_chart as module
    return module


def versioned(path: Path, out: Path) -> str:
    return f"{path.relative_to(out).as_posix()}?v={hashlib.sha256(path.read_bytes()).hexdigest()[:10]}"


def actual_returns(db: Path, ticker: str, days: list[str], base: float, until: str) -> list[float]:
    """기준 가격 날짜 뒤 `until`까지의 거래일마다 기준 가격 대비 종가 수익률(%). 첫 값은 출발점 0이고 종가가 있는 날까지 잇는다.

    `until`은 가장 늦은 리포트의 기준 가격 날짜다. 그 리포트를 만든 뒤에 확정된 종가는 잇지 않는다.
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        closes = dict(con.execute(
            f"SELECT price_date, close FROM market_price WHERE ticker=? AND price_date IN ({','.join('?' * len(days))})",
            (ticker, *days)).fetchall())
    finally:
        con.close()
    values = [0.0]
    for day in days[1:]:
        if day > until or day not in closes:
            break
        values.append(round((closes[day] / base - 1) * 100, 3))
    return values


def moves(vault: Path, index: str, date: str) -> dict | None:
    """리포트 날짜 `date` 전날의 정규장 등락률과 장 마감 뒤 등락률(%). `path-bands.json`이나 앞 세션 종가가 없으면 `None`."""
    bands_path = vault / f"routine/invest/{date[:7]}/{date}/{index}/path-bands.json"
    if not bands_path.is_file():
        return None
    bands = json.loads(bands_path.read_text(encoding="utf-8"))
    chart = predictions_chart(vault)
    con = sqlite3.connect(f"file:{chart.path_bands.REFERENCE_DB_PATH}?mode=ro", uri=True)
    try:
        closes = [close for (close,) in con.execute(
            "SELECT close FROM market_price WHERE ticker=? AND price_date<=? ORDER BY price_date DESC LIMIT 2",
            (chart.path_bands.SECTOR_DB_TICKERS[index], bands["price_base_date"])).fetchall()]
    finally:
        con.close()
    if len(closes) < 2:
        return None
    close = float(bands["price_base_session_close"])
    previous = (dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()
    return {"session": round((close / closes[1] - 1) * 100, 2) + 0.0 if bands["price_base_date"] == previous else None,
            "after": round((float(bands["price_base"]) / close - 1) * 100, 2) + 0.0}


def rewind(index: str, vault: Path, out: Path) -> Path | None:
    """`r/rewind-{지수}/`에 되감기 바탕 그림과 `frames.json`을 쓴다. 되감을 날짜가 없으면 폴더를 지운다."""
    target = out / "r" / f"rewind-{index}"
    published = sorted(dt.date.fromisoformat(f"{p.name[:4]}-{p.name[4:6]}-{p.name[6:8]}")
                       for p in (out / "r").glob(f"*-{index}") if p.name[:8].isdigit())
    folders = {}
    for day in published:
        if published[-1] - day >= dt.timedelta(days=REWIND_DAYS):
            continue
        folder = vault / f"routine/invest/{day:%Y-%m}/{day}/{index}"
        key = out / "r" / f"{day:%Y%m%d}-{index}"
        if all(path.is_file() for path in (folder / "system" / "simulation.json", folder / "system" / "tree-axes.json",
                                          key / f"tree-{index}.png", key / f"chart-{index}.png")):
            folders[day.isoformat()] = folder
    if not folders:
        shutil.rmtree(target, ignore_errors=True)
        return None
    chart = predictions_chart(vault)
    target.mkdir(parents=True, exist_ok=True)
    latest = max(folders)
    base = chart.rewind(index, latest, folders, target / "predict.png",
                        chart.LEDGER_DIR / f"predictions-{index}.jsonl", chart.path_bands.REFERENCE_DB_PATH)
    predict = {item["day"]: item for item in base.pop("frames")}
    until = json.loads((folders[latest] / "path-bands.json").read_text(encoding="utf-8"))["price_base_date"]
    frames = []
    for day, folder in sorted(folders.items()):
        if day not in predict:
            continue
        key = out / "r" / f"{day.replace('-', '')}-{index}"
        bands = json.loads((folder / "path-bands.json").read_text(encoding="utf-8"))
        days = json.loads((folder / "system" / "simulation.json").read_text(encoding="utf-8"))["quantiles"]["days"]
        actual = actual_returns(chart.path_bands.REFERENCE_DB_PATH, chart.path_bands.SECTOR_DB_TICKERS[index], days,
                                float(bands["price_base"]), until)
        axes = json.loads((folder / "system" / "tree-axes.json").read_text(encoding="utf-8"))
        frames.append({"day": day, "predict": {k: v for k, v in predict[day].items() if k != "day"},
                       "tree": {"src": versioned(key / f"tree-{index}.png", out), **axes, "actual": actual},
                       "chart": {"src": versioned(key / f"chart-{index}.png", out)}})
    data = {"predict": {"src": versioned(target / "predict.png", out), **base}, "frames": frames}
    (target / "frames.json").write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def public_markdown(text: str, vault: Path, out_dir: Path, base: str) -> str:
    """공개본 마크다운. 그림은 `out_dir`로 복사하고 `app.html` 기준 상대 경로로 바꾼다.

    경로 뒤에 그림 내용의 해시를 붙인다. 같은 이름으로 다시 그린 그림을 텔레그램이 캐시에서 꺼내지 않게 하기 위해서다.
    """
    pdf = report_pdf(vault)
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = pdf.PUBLIC_CUT_RE.split(text, maxsplit=1)[0]
    pdf.check_public(text)
    text = re.sub(r"^(#{1,6} .*)\n---\s*$", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r'^<div style="height:[^"]*"></div>\s*$', "", text, flags=re.MULTILINE)

    def embed(match: re.Match) -> str:
        source = vault / match.group(1).strip()
        shutil.copy2(source, out_dir / source.name)
        version = hashlib.sha256(source.read_bytes()).hexdigest()[:10]
        return f"![]({base}/{source.name}?v={version})"

    return EMBED_RE.sub(embed, text)


def cells(row: str) -> list[str]:
    return [body.strip() for _, body in CELL_RE.findall(row)]


def mark_events(table: str) -> str:
    """이벤트 표의 열에 이름표를 단다. 다른 표는 그대로 둔다."""
    rows = [cells(r) for r in ROW_RE.findall(table)]
    if not rows or rows[0] != EVENT_HEADER:
        return table
    out = ['<table class="events">', "<thead><tr><th>분기</th><th>확률</th><th>전개 예상</th></tr></thead>", "<tbody>"]
    for branch, chance, outlook in rows[1:]:
        out.append(f'<tr><td class="branch">{branch}</td><td class="chance">{chance}</td><td>{outlook}</td></tr>')
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def event_day(text: str, date: dt.date) -> tuple[dt.date, str, str] | None:
    """소제목 글에서 발표일, 발표 시간대(장전·장중·장후), 날짜를 뺀 제목을 읽는다. 연도가 없으면 리포트 날짜에 가까운 해로 본다."""
    match = EVENT_DAY_RE.match(text)
    if not match:
        return None
    month, day = int(match.group(2)), int(match.group(3))
    if match.group(1):
        year = int(match.group(1))
    else:
        year = date.year + (1 if date.month - month > 6 else -1 if month - date.month > 6 else 0)
    return dt.date(year, month, day), match.group(4) or "", text[match.end():]


def events_block(markdown: str) -> str:
    """리포트 마크다운의 `다가오는 이벤트` 절 본문."""
    match = re.search(rf"^## {EVENTS_TITLE}\s*\n(.*?)(?=^## |\Z)", markdown, flags=re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def event_items(markdown: str, date: dt.date) -> list[tuple[dt.date, str, str]]:
    """절 안의 이벤트마다 (발표일, 이름, 소제목부터 다음 소제목 앞까지의 마크다운)."""
    items = []
    for chunk in re.split(r"^(?=### )", events_block(markdown), flags=re.MULTILINE):
        if not chunk.startswith("### "):
            continue
        heading, _, rest = chunk.partition("\n")
        parsed = event_day(heading[4:].strip(), date)
        if parsed:
            items.append((parsed[0], LEVEL_RE.sub("", parsed[2]).strip(), chunk))
    return items


def report_path(vault: Path, day: dt.date, index: str) -> Path:
    return vault / f"routine/invest/{day:%Y-%m}/{day}/{index}/report.md"


def tree_issues(report: Path) -> dict[str, dict]:
    """리포트 폴더 사안 나무에서 id가 있는 사안을 이름마다 하나씩."""
    tree = report.with_name("tree.json")
    issues = json.loads(tree.read_text(encoding="utf-8")).get("issues", []) if tree.is_file() else []
    return {issue["name"]: issue for issue in issues if issue.get("id")}


def realized(vault: Path, index: str, source: Path, name: str, day: dt.date, date: dt.date) -> dict | None:
    """`source` 리포트의 사안 나무에서 이벤트의 사안을 찾고, 발표일 다음 날부터 리포트 날짜까지의
    사안 나무 `resolved`에서 그 id의 항목을 찾는다. 항목의 `branch`는 `source` 나무의 갈래 이름으로 바꿔 돌려준다.
    아직 적히지 않았으면 None이다."""
    issue = tree_issues(source).get(name)
    if issue is None:
        return None
    names = {branch["id"]: branch["name"] for branch in issue.get("branches", [])}
    for offset in range(1, (date - day).days + 1):
        tree = report_path(vault, day + dt.timedelta(days=offset), index).with_name("tree.json")
        if not tree.is_file():
            continue
        for entry in json.loads(tree.read_text(encoding="utf-8")).get("resolved", []):
            if entry.get("id") == issue["id"]:
                if "branch" in entry:
                    entry["branch"] = names.get(entry["branch"], entry["branch"])
                return entry
    return None


def past_events(vault: Path, index: str, date: dt.date) -> tuple[str, dict[str, dict]]:
    """리포트 날짜 전 `PAST_DAYS`일 동안 발표된 이벤트의 마크다운과, 이벤트 이름마다 `resolved` 항목.

    발표일마다 그날 이벤트를 예측한 가장 최근 리포트의 소제목과 표를 그 리포트의 순서대로 쓴다.
    리포트 날짜의 리포트가 같은 사안 id로 적은 이벤트는 뺀다.
    """
    first = date - dt.timedelta(days=PAST_DAYS)
    current = report_path(vault, date, index)
    issues = tree_issues(current)
    shown = {issues[name]["id"] for _, name, _ in event_items(current.read_text(encoding="utf-8"), date)
             if name in issues}
    found: dict[dt.date, list[tuple[Path, str, str]]] = {}
    for back in range(1, LOOKBACK + 1):
        source = report_path(vault, date - dt.timedelta(days=back), index)
        if not source.is_file():
            continue
        latest: dict[dt.date, list[tuple[Path, str, str]]] = {}
        for day, name, chunk in event_items(source.read_text(encoding="utf-8"), date):
            if first <= day < date and day not in found:
                latest.setdefault(day, []).append((source, name, chunk))
        found.update(latest)
    blocks, branches = [], {}
    for day in sorted(found):
        for source, name, chunk in found[day]:
            if tree_issues(source).get(name, {}).get("id") in shown:
                continue
            entry = realized(vault, index, source, name, day, date)
            blocks.append(chunk.rstrip() + "\n")
            if entry:
                branches[name] = entry
    return "\n".join(blocks), branches


def phase(announced: str) -> str:
    """뉴욕 시각 `YYYY-MM-DD HH:MM`의 발표가 정규장 앞·안·뒤 가운데 어디인가."""
    moment = announced[11:16]
    return "장전" if moment < REGULAR_OPEN else "장중" if moment < REGULAR_CLOSE else "장후"


def when_label(announced: str) -> str:
    """제목 위에 적는 발표 시각. 기본값 시각이면 장 구분만, 아니면 `10/29(목) 03:00 KST` 꼴이다."""
    if announced[11:16] in PLACEHOLDER_TIMES:
        return phase(announced)
    moment = dt.datetime.fromisoformat(announced).replace(tzinfo=NEW_YORK).astimezone(SEOUL)
    return f"{moment:%m/%d}({'월화수목금토일'[moment.weekday()]}) {moment:%H:%M} KST"


def timings(vault: Path, index: str, date: dt.date) -> dict[tuple[str, str], str]:
    """(발표일, 이벤트 이름)마다 제목 위 발표 시각(`when_label`). 이름이 빈 키에는 그날 발표가 모두 같은 장 구분일 때만 그 구분을 둔다.

    리포트 날짜 앞뒤 `LOOKBACK`일의 사안 나무에서 발표 시각을 읽고, 같은 사안은 가장 늦은 나무의 시각을 쓴다.
    """
    announced_at: dict[tuple[str, str], str] = {}
    for offset in range(LOOKBACK, -LOOKBACK - 1, -1):
        tree = report_path(vault, date + dt.timedelta(days=offset), index).with_name("tree.json")
        if not tree.is_file():
            continue
        for issue in json.loads(tree.read_text(encoding="utf-8")).get("issues", []):
            announced = issue.get("announced")
            if announced:
                announced_at.setdefault((announced[:10], issue["name"]), announced)
    found = {key: when_label(announced) for key, announced in announced_at.items()}
    days: dict[str, set[str]] = {}
    for (day, _), announced in announced_at.items():
        days.setdefault(day, set()).add(phase(announced))
    found.update({(day, ""): values.pop() for day, values in days.items() if len(values) == 1})
    return found


def change_mark(change: int | str) -> str:
    """갈래 변화(`change`)를 확률 칸 아래에 붙일 작은 글씨로 바꾼다."""
    if change == "new":
        return '<small class="delta flat">신규</small>'
    if change == "redefined":
        return '<small class="delta flat">재정의</small>'
    if change > 0:
        return f'<small class="delta up">▲{change}%p</small>'
    if change < 0:
        return f'<small class="delta down">▼{-change}%p</small>'
    return '<small class="delta flat">–</small>'


def mark_changes(table: str, upcoming: list[dict]) -> str:
    """분기 이름이 모두 한 사안의 갈래 이름인 표에서 갈래마다 확률 칸 아래에 어제 대비 변화를 붙인다."""
    names = {html.unescape(name) for name in re.findall(r'<td class="branch">(.*?)</td>', table, flags=re.DOTALL)}
    issue = next((issue for issue in upcoming
                  if names and names <= {branch["name"] for branch in issue.get("branches", [])}), None)
    if issue is None:
        return table
    for branch in issue["branches"]:
        cell = f'<td class="branch">{html.escape(branch["name"], quote=False)}</td><td class="chance">'
        start = table.find(cell)
        if start >= 0:
            stop = table.index("</td>", start + len(cell))
            table = table[:stop] + "<br>" + change_mark(branch["change"]) + table[stop:]
    return table


def mark_days(body: str, date: dt.date, branches: dict[str, dict], timing: dict[tuple[str, str], str],
              upcoming: list[dict]) -> str:
    """`다가오는 이벤트` 절의 소제목에 발표일(`data-day`)을 달고 제목에서 날짜를 지운다.

    발표 시각은 제목 앞 `when` 이름표로 단다. `timing`에 그 이벤트가 없으면 소제목의 장 구분을, 그것도 없으면 그날의 장 구분을 쓴다.
    소제목의 중요도 표식은 `data-level`로도 단다.
    리포트 날짜 전 이벤트의 표에는 `judged`를, 실제 갈래 줄에는 `hit`을 달고 그 줄의 전개 예상 뒤에 실제 전개를 붙인다.
    리포트 날짜와 그 뒤 이벤트의 표에는 `upcoming`(`display.json`의 `next`)의 갈래 변화를 붙인다.
    """
    head = re.search(rf'<h2 id="[^"]*">{EVENTS_TITLE}</h2>', body)
    if not head:
        return body
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end
    section = body[head.end():end]

    def heading(match: re.Match) -> str:
        attrs, inner = match.group(1), match.group(2)
        parsed = event_day(inner, date)
        if not parsed:
            raise SystemExit(f"발표일이 없는 이벤트 소제목: {inner}")
        day, when, rest = parsed
        name = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<code>.*?</code>", "", rest))).strip()
        when = timing.get((f"{day}", name)) or when or timing.get((f"{day}", ""), "")
        label = f'<span class="when">{when}</span>' if when else ""
        tag = re.search(r"<code>중요도 ([^<]*)</code>", rest)
        level = LEVELS.get(tag.group(1)) if tag else None
        mark = f' data-level="{level}"' if level else ""
        return f'<h3{attrs} data-day="{day}"{mark}>{label}{rest}</h3>'

    section = re.sub(r"<h3([^>]*)>(.*?)</h3>", heading, section, flags=re.DOTALL)

    def judge(match: re.Match) -> str:
        day, title, table = match.group(1), match.group(2), match.group(3)
        if dt.date.fromisoformat(day) >= date:
            return match.group(0)[:match.start(3) - match.start(0)] + mark_changes(table, upcoming)
        name = re.sub(r"<[^>]+>", "", re.sub(r"<code>.*?</code>", "", title)).strip()
        entry = branches.get(html.unescape(name), {})
        table = table.replace('<table class="events">', '<table class="events judged">', 1)
        if entry.get("branch"):
            cell = f'<tr><td class="branch">{html.escape(entry["branch"], quote=False)}</td>'
            start = table.find(cell)
            if start >= 0:
                stop = table.index("</td></tr>", start)
                outcome = entry.get("outcome")
                tail = f' <span class="outcome">→ {html.escape(outcome, quote=False)}</span>' if outcome else ""
                table = (table[:start] + '<tr class="hit">' + table[start + 4:stop] + tail + table[stop:])
        return match.group(0)[:match.start(3) - match.start(0)] + table

    section = re.sub(r'<h3[^>]* data-day="([^"]+)"(?: data-level="[^"]*")?>(?:<span class="when">[^<]*</span>)?(.*?)</h3>\s*(<table class="events">.*?</table>)',
                     judge, section, flags=re.DOTALL)
    return body[:head.end()] + section + body[end:]


def build(date: str, index: str, vault: Path, out: Path) -> str:
    source = vault / f"routine/invest/{date[:7]}/{date}/{index}/report.md"
    if not source.is_file():
        raise SystemExit(f"리포트가 없다: {source}")
    key = f"{date.replace('-', '')}-{index}"
    target = out / "r" / key
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    markdown = public_markdown(source.read_text(encoding="utf-8"), vault, target, f"r/{key}")
    day = dt.date.fromisoformat(date)
    past, branches = past_events(vault, index, day)
    if past:
        markdown = re.sub(rf"^## {EVENTS_TITLE}\s*\n", lambda m: m.group(0) + "\n" + past + "\n", markdown,
                          count=1, flags=re.MULTILINE)
    title = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), key)
    markdown = re.sub(r"^# .*\n", "", markdown, count=1, flags=re.MULTILINE)
    body = subprocess.run(["pandoc", "-f", "gfm", "-t", "html5", "--wrap=none"], input=markdown,
                          capture_output=True, text=True, check=True).stdout
    body = TABLE_RE.sub(lambda m: mark_events(m.group(0)), body)
    display = source.parent / "system" / "display.json"
    upcoming = json.loads(display.read_text(encoding="utf-8"))["next"] if display.is_file() else []
    body = mark_days(body, day, branches, timings(vault, index, day), upcoming)
    (target / "report.html").write_text(body, encoding="utf-8")

    listing = out / "r" / "index.json"
    entries = json.loads(listing.read_text(encoding="utf-8")) if listing.exists() else {}
    heading = TITLE_RE.match(html.unescape(title))
    if not heading:
        raise SystemExit(f"제목 끝에 날짜가 없다: {title}")
    written = entries.get(key, {}).get("written") or dt.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
    entries[key] = {"title": heading.group(1), "day": heading.group(2), "written": written, "date": date, "index": index}
    if (move := moves(vault, index, date)):
        entries[key]["moves"] = move
    listing.write_text(json.dumps(dict(sorted(entries.items(), reverse=True)), ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
    rewind(index, vault, out)
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description="판단 리포트 공개본을 `invest-reports` 미니 앱 조각으로 만든다")
    parser.add_argument("--date", required=True, help="리포트 날짜 YYYY-MM-DD")
    parser.add_argument("--index", required=True, help="지수 폴더 이름 (nasdaq, biotech)")
    parser.add_argument("--vault", default=str(Path.home() / "obsidian-vault"))
    parser.add_argument("--out", default=str(ROOT))
    args = parser.parse_args()
    print(build(args.date, args.index, Path(args.vault).expanduser(), Path(args.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
