#!/usr/bin/env python3
"""build — 판단 리포트 공개본을 텔레그램 미니 앱(`app.html`)이 읽는 HTML 조각으로 만든다.

사용법: python3 build.py --date 2026-10-19 --index nasdaq [--vault ~/obsidian-vault] [--out .]

`r/{YYYYMMDD}-{지수}/`에 `report.html`과 그림을 쓰고 `r/index.json`의 목록을 갱신한다. 미니 앱은
`start_param`으로 받은 `{YYYYMMDD}-{지수}`를 열어 그 조각을 그린다.

공개본이 끝나는 자리와 공개본에 남으면 안 되는 말은 invest-report `report_pdf.py`의 값을 그대로 쓴다.
PDF와 미니 앱이 같은 자리에서 자르므로, 공개 채널로 나가는 두 판본의 내용이 같다.

`다가오는 이벤트` 표는 분기·확률·전개 예상 세 열이다. 휴대폰 폭에서 분기 이름이 접히지 않게 열마다
폭과 정렬을 정하는 이름표를 단다.
"""
import argparse
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


def report_pdf(vault: Path):
    sys.path.insert(0, str(vault / "agent/skills/tool/invest-report/scripts"))
    import report_pdf as module
    return module


def public_markdown(text: str, vault: Path, out_dir: Path, base: str) -> str:
    """공개본 마크다운. 그림은 `out_dir`로 복사하고 `app.html` 기준 상대 경로로 바꾼다."""
    pdf = report_pdf(vault)
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = pdf.PUBLIC_CUT_RE.split(text, maxsplit=1)[0]
    pdf.check_public(text)
    text = re.sub(r"^(#{1,6} .*)\n---\s*$", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r'^<div style="height:[^"]*"></div>\s*$', "", text, flags=re.MULTILINE)

    def embed(match: re.Match) -> str:
        source = vault / match.group(1).strip()
        shutil.copy2(source, out_dir / source.name)
        return f"![]({base}/{source.name})"

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
    title = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), key)
    markdown = re.sub(r"^# .*\n", "", markdown, count=1, flags=re.MULTILINE)
    body = subprocess.run(["pandoc", "-f", "gfm", "-t", "html5"], input=markdown,
                          capture_output=True, text=True, check=True).stdout
    body = TABLE_RE.sub(lambda m: mark_events(m.group(0)), body)
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
