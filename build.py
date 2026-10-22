#!/usr/bin/env python3
"""build — 판단 리포트 공개본을 텔레그램 미니 앱(`app.html`)이 읽는 HTML 조각으로 만든다.

사용법: python3 build.py --date 2026-10-19 --index nasdaq [--vault ~/obsidian-vault] [--out .]

`r/{YYYYMMDD}-{지수}/`에 `report.html`과 그림을 쓰고 `r/index.json`의 목록을 갱신한다. 미니 앱은
`start_param`으로 받은 `{YYYYMMDD}-{지수}`를 열어 그 조각을 그린다.

공개본이 끝나는 자리와 공개본에 남으면 안 되는 말은 invest-report `report_pdf.py`의 값을 그대로 쓴다.
PDF와 미니 앱이 같은 자리에서 자르므로, 공개 채널로 나가는 두 판본의 내용이 같다.

`다가오는 이벤트` 표는 분기·확률·전개 예상 세 열이다. 휴대폰 폭에서 분기 이름이 접히지 않게 열마다
폭과 정렬을 정하는 이름표를 단다.

`다가오는 이벤트` 절에는 리포트 날짜 전 이틀 동안 발표된 이벤트도 넣는다. 표는 그 이벤트를 예측한 가장 최근
리포트의 표를 쓰고, 그 뒤 사안 나무(`tree.json`)의 `resolved`에 적힌 실제 갈래 줄에 `hit` 이름표를 단다.
실제 갈래 줄의 전개 예상 뒤에는 `resolved`의 실제 전개(`outcome`)를 화살표와 함께 붙인다.
이벤트 소제목마다 발표일을 `data-day`로 달고 제목에서는 날짜를 지운다. 미니 앱은 이 값으로 날짜 띠를 그리고
같은 날 이벤트를 한 장에 모은다. 소제목에 장전·장중·장후가 없으면 사안 나무의 발표 시각(`announced`)으로 정한다.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
TABLE_RE = re.compile(r"<table>.*?</table>", re.DOTALL)
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
CELL_RE = re.compile(r"<t([hd])\b[^>]*>(.*?)</t\1>", re.DOTALL)
EVENT_HEADER = ["분기", "확률", "전개 예상"]
EVENTS_TITLE = "다가오는 이벤트"
# 이벤트 소제목 앞의 발표일. `2026-10-21(수)`, `2026-10-21(수)~10-28(수)`, `10/26(월) 장전` 꼴이다.
EVENT_DAY_RE = re.compile(r"^(?:(\d{4})-)?(\d{1,2})[-/](\d{1,2})\([^)]*\)(?:~\S+)?\s*(?:(장전|장중|장후)\s+)?")
LEVEL_RE = re.compile(r"\s*`중요도 [^`]*`")
PAST_DAYS = 2  # 리포트 날짜 전 며칠 동안 발표된 이벤트를 넣는지
LOOKBACK = 7  # 지난 이벤트의 표를 찾을 때 거슬러 보는 리포트 날짜 수
REGULAR_OPEN, REGULAR_CLOSE = "09:30", "16:00"  # 뉴욕 정규장 시각. 발표 시각을 장전·장중·장후로 나눈다


def report_pdf(vault: Path):
    sys.path.insert(0, str(vault / "agent/skills/tool/invest-report/scripts"))
    import report_pdf as module
    return module


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


def realized(vault: Path, index: str, name: str, day: dt.date, date: dt.date) -> dict | None:
    """발표일 다음 날부터 리포트 날짜까지의 사안 나무 `resolved`에서 그 이벤트의 항목을 찾는다. 아직 적히지 않았으면 None이다."""
    for offset in range(1, (date - day).days + 1):
        tree = report_path(vault, day + dt.timedelta(days=offset), index).with_name("tree.json")
        if not tree.is_file():
            continue
        for entry in json.loads(tree.read_text(encoding="utf-8")).get("resolved", []):
            if entry.get("name") == name:
                return entry
    return None


def past_events(vault: Path, index: str, date: dt.date) -> tuple[str, dict[str, dict]]:
    """리포트 날짜 전 `PAST_DAYS`일 동안 발표된 이벤트의 마크다운과, 이벤트 이름마다 `resolved` 항목.

    발표일마다 그날 이벤트를 예측한 가장 최근 리포트의 소제목과 표를 그 리포트의 순서대로 쓰고, 소제목의 중요도 표식은 뺀다.
    발표가 옮겨진 이벤트는 넣지 않는다.
    """
    first = date - dt.timedelta(days=PAST_DAYS)
    found: dict[dt.date, list[tuple[str, str]]] = {}
    for back in range(1, LOOKBACK + 1):
        source = report_path(vault, date - dt.timedelta(days=back), index)
        if not source.is_file():
            continue
        latest: dict[dt.date, list[tuple[str, str]]] = {}
        for day, name, chunk in event_items(source.read_text(encoding="utf-8"), date):
            if first <= day < date and day not in found:
                latest.setdefault(day, []).append((name, LEVEL_RE.sub("", chunk, count=1)))
        found.update(latest)
    blocks, branches = [], {}
    for day in sorted(found):
        for name, chunk in found[day]:
            entry = realized(vault, index, name, day, date)
            if entry and "postponed" in entry:
                continue
            blocks.append(chunk.rstrip() + "\n")
            if entry:
                branches[name] = entry
    return "\n".join(blocks), branches


def phase(announced: str) -> str:
    """뉴욕 시각 `YYYY-MM-DD HH:MM`의 발표가 정규장 앞·안·뒤 가운데 어디인가."""
    moment = announced[11:16]
    return "장전" if moment < REGULAR_OPEN else "장중" if moment < REGULAR_CLOSE else "장후"


def phases(vault: Path, index: str, date: dt.date) -> dict[tuple[str, str], str]:
    """(발표일, 이벤트 이름)마다 장 구분. 이름이 빈 키에는 그날 발표가 모두 같은 장 구분일 때만 그 구분을 둔다.

    리포트 날짜 앞뒤 `LOOKBACK`일의 사안 나무에서 발표 시각을 읽고, 같은 사안은 가장 늦은 나무의 시각을 쓴다.
    """
    found: dict[tuple[str, str], str] = {}
    for offset in range(LOOKBACK, -LOOKBACK - 1, -1):
        tree = report_path(vault, date + dt.timedelta(days=offset), index).with_name("tree.json")
        if not tree.is_file():
            continue
        for issue in json.loads(tree.read_text(encoding="utf-8")).get("issues", []):
            announced = issue.get("announced")
            if announced:
                found.setdefault((announced[:10], issue["name"]), phase(announced))
    days: dict[str, set[str]] = {}
    for (day, _), value in found.items():
        days.setdefault(day, set()).add(value)
    found.update({(day, ""): values.pop() for day, values in days.items() if len(values) == 1})
    return found


def mark_days(body: str, date: dt.date, branches: dict[str, dict], timing: dict[tuple[str, str], str]) -> str:
    """`다가오는 이벤트` 절의 소제목에 발표일(`data-day`)을 달고 제목에서 날짜를 지운다.

    발표 시간대는 제목 앞 `when` 이름표로 남긴다. 소제목에 시간대가 없으면 `timing`에서 찾는다.
    리포트 날짜 전 이벤트의 표에는 `judged`를, 실제 갈래 줄에는 `hit`을 달고 그 줄의 전개 예상 뒤에 실제 전개를 붙인다.
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
        if not when:
            name = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<code>.*?</code>", "", rest))).strip()
            when = timing.get((f"{day}", name)) or timing.get((f"{day}", ""), "")
        label = f'<span class="when">{when}</span>' if when else ""
        return f'<h3{attrs} data-day="{day}">{label}{rest}</h3>'

    section = re.sub(r"<h3([^>]*)>(.*?)</h3>", heading, section, flags=re.DOTALL)

    def judge(match: re.Match) -> str:
        day, title, table = match.group(1), match.group(2), match.group(3)
        if dt.date.fromisoformat(day) >= date:
            return match.group(0)
        name = re.sub(r"<[^>]+>", "", title).strip()
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

    section = re.sub(r'<h3[^>]* data-day="([^"]+)">(?:<span class="when">[^<]*</span>)?(.*?)</h3>\s*(<table class="events">.*?</table>)',
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
    body = mark_days(body, day, branches, phases(vault, index, day))
    (target / "report.html").write_text(body, encoding="utf-8")

    listing = out / "r" / "index.json"
    entries = json.loads(listing.read_text(encoding="utf-8")) if listing.exists() else {}
    entries[key] = {"title": html.unescape(title), "date": date, "index": index}
    listing.write_text(json.dumps(dict(sorted(entries.items(), reverse=True)), ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description="판단 리포트 공개본을 미니 앱 조각으로 만든다")
    parser.add_argument("--date", required=True, help="리포트 날짜 YYYY-MM-DD")
    parser.add_argument("--index", required=True, help="지수 폴더 이름 (nasdaq, biotech)")
    parser.add_argument("--vault", default=str(Path.home() / "obsidian-vault"))
    parser.add_argument("--out", default=str(ROOT))
    args = parser.parse_args()
    print(build(args.date, args.index, Path(args.vault).expanduser(), Path(args.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
