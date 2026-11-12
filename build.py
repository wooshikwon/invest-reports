#!/usr/bin/env python3
"""build — 판단 리포트 공개본을 `invest-reports` `invest-reports` 미니 앱(`app.html`)이 읽는 HTML 조각으로 만든다. `run-with-notify.sh`의 `publish_miniapp`이 만든 조각을 게시한다.

사용법: python3 build.py --date 2026-10-19 --index nasdaq [--vault ~/obsidian-vault] [--out .]

`r/{YYYYMMDD}-{지수}/`에 `report.html`과 그림을 쓰고 `r/index.json`의 목록을 갱신한다. `invest-reports` 미니 앱은
`start_param`으로 받은 `{YYYYMMDD}-{지수}`를 열어 그 조각을 그리고, 키 없이 열리면 목록에서 가장 늦은 나스닥 리포트를 연다.

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

`미국 거시 지표` 절의 지표 소제목에는 그날 지수 폴더의 `market-data.json`·`macro-data.json`에서 뽑은 카드 값을 `data-card`로 단다.
하이일드 스프레드는 앞 12주 지수 폴더의 같은 JSON에서 주마다 마지막 값을 함께 뽑아 막대 그림으로 그린다.
유가는 그날 `market-data.json` `market.WTI`의 주별 정산가(`weekly_close`)를 선 그림으로 그린다.
카드 값은 탭 이름, 값과 단위, 상태 이름과 색, 기준일(미국 장이 마감한 한국 날짜), 보조 값을 적은 한 줄, 그림 종류와 그림 입력, 물음표 단추의 설명이다.
값이 없는 지표에는 카드 값을 달지 않는다.
`invest-reports` 미니 앱은 카드 값으로 지표마다 카드를 그려 한 장씩 넘기게 하고, 카드 값이 없는 소제목은 지운다.

`상세 이슈 해설` 절의 번호 붙은 이슈 소제목에는 리포트 폴더 `system/issues.json`에서 그 번호의 `id`를 `data-issue`로 단다.
`id`는 Main이 그 이슈로 묶은 사안 나무 노드 가운데 반영 정도가 가장 큰 노드의 이름이므로, 날짜가 다른 리포트에서 같은 사안을 다룬 이슈는 같은 값을 갖는다.
번호 붙은 이슈 뒤에는 그 `id`를 노드로 묶은 앞 날짜 이슈를 `issue-history` 템플릿으로 넣는다. 앞 날짜 이슈는 그날 `system/issues.json`의
`nodes`에 오늘 `id`가 든 이슈이고, 내용은 그날 공개본 `report.html`의 이슈 조각을 그대로 쓴다. 템플릿에는 앞 날짜부터 오늘까지
날짜와 이슈 해설 소제목을 날짜 순으로 적고, 오늘 항목에는 내용을 넣지 않는다. 앞 날짜 이슈가 없는 이슈에는 템플릿을 넣지 않는다.
`invest-reports` 미니 앱은 템플릿으로 이슈 그림과 이슈 해설 사이에 지난 해설 상자를 그리고, 소제목을 누르면 이슈 문단을 그날의 내용으로 바꾼다.
번호 붙은 이슈 소제목 뒤에는 리포트 폴더 `assets/issue-{번호}.webp`가 있을 때만 그 그림과
`AI 생성 이미지` 캡션을 넣는다. 그림은 `run-with-notify.sh`가 ⑨의 이슈 이미지 선정 결과로 만든다. 그림마다 가운데를 잘라
`THUMB`px 정사각 썸네일 `issue-{번호}-thumb.webp`를 만들어 그림의 `data-thumb`에 적는다. `invest-reports` 미니 앱은 이슈 목록 상자에 썸네일을 붙인다.
이슈 해설 말머리 뒤 문단 사이에는 리포트 폴더 `system/issue-charts.json`의 카드 값을 `issue-chart` 그림의 `data-card`로 넣는다.
카드 값은 ⑨의 이슈 그래프 agent가 설계하고 `issue_charts.py fill`이 채우며, 카드 값이 없는 그래프는 넣지 않는다.
그래프는 설계의 `after`번째 문단 다음에 들어가고, 문단이 그보다 적으면 마지막 문단 다음에 들어간다.
`invest-reports` 미니 앱은 카드 값으로 `미국 거시 지표` 카드와 같은 모양의 선 그래프·막대 그래프·표 카드를 그린다.

`r/index.json`에는 리포트마다 제목, 날짜 줄(`day`), 처음 만든 시각(`written`, 서울 시각)을 적는다. `invest-reports` 미니 앱은 제목 아래
작은 글씨로 날짜 줄과 처음 만든 시각을 그린다. 같은 리포트를 다시 만들어도 처음 만든 시각은 그대로 둔다.
`invest-reports` 미니 앱의 달력은 같은 목록에서 그 지수의 리포트 날짜를 찾아 흰 글자로 쓰고, 날짜 아래에 `moves`의 `session`을 적는다.
`moves`에는 리포트 날짜 전날 정규장 종가의 앞 세션 종가 대비 등락률(`session`, %)과 기준 가격의 기준 가격 날짜 종가 대비
등락률(`after`, %)을 적는다. 전날이 휴장일이면 `session`은 `null`이다. 두 등락률은 `path-bands.json`의 ^NDX·^NBI 환산 가격과 `reference.db` 환산 종가로 재므로
12M + Predictions 그림의 종가 선과 기준 가격 차이와 같다. `invest-reports` 미니 앱은 날짜 줄 아래 회색 글씨로
`정규장`과 `장 마감 후` 등락률을 적고 등락률만 오르면 빨강, 내리면 파랑으로 칠한다. `null`은 `—`로 적는다.

`r/rewind-{지수}/`에는 지난 판단으로 되감는 슬라이더의 값을 쓴다. 되감기 날짜는 공개본이 있는 그 지수 리포트 가운데
가장 늦은 날짜에서 `REWIND_DAYS`일 안이고, `system/simulation.json`의 `quantiles`와 `system/tree-axes.json`이 있는
날짜다. `predict.png`는 가장 늦은 날짜의 12M + Predictions 그림에서 종가 선과 오늘 판단을 지운 바탕이고
(`predictions_chart.rewind`), `frames.json`은 바탕의 축 위치·종가와 날짜마다 12M + Predictions 범위, 그날 Montecarlo 그림과
축 위치, 그날 기준 가격 뒤의 실제 종가 수익률(%), 그날 권장 추종 배율 그림을 담는다. Montecarlo·권장 추종 배율 그림은
그날 공개본 폴더의 그림을 그대로 가리킨다. `invest-reports` 미니 앱은 슬라이더를 옮길 때 바탕 위에 그날 범위를 그리고,
그날 Montecarlo 그림 위에 실제 종가 선을 그린다.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import math
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

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
LOOKBACK = 7  # 지난 이벤트의 표와 발표 시각을 찾을 때 거슬러 보는 리포트 날짜 수
REGULAR_OPEN, REGULAR_CLOSE = "09:30", "16:00"  # 뉴욕 정규장 시각. 발표 시각을 장전·장중·장후로 나눈다
# 발표 시각을 모를 때 채우는 뉴욕 시각. 실적의 장전(bmo)·장후(amc) 단서는 `calendar_store.py`가 08:00·16:05로,
# 장중(dmh)은 `render_inputs.py`가 12:00으로 채우고, 단서가 없는 발표는 16:00으로 적는다. 이 시각은 장 구분만 적는다.
PLACEHOLDER_TIMES = {"08:00", "12:00", "16:00", "16:05"}
NEW_YORK, SEOUL = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")
# 리포트 제목 끝의 날짜 줄. `나스닥 리포트 2026-10-22 (목)` 꼴이다.
TITLE_RE = re.compile(r"^(.*\S)\s+(\d{4}-\d{2}-\d{2} \([^)]*\))$")
REWIND_DAYS = 30  # 되감기 슬라이더가 거슬러 가는 날짜 범위
INDICATORS_TITLE = "미국 거시 지표"
ISSUES_TITLE = "상세 이슈 해설"
HISTORY_RE = re.compile(r'<template class="issue-history">.*?</template>\s*', re.DOTALL)
THUMB = 264
UP, DOWN, NEUTRAL = "#ff5c5c", "#5b9bff", "#ffffff"  # 오름·내림·중립 색. 오름·내림 색은 `app.html`의 등락 색과 같다
# 지표 카드의 구간. [구간 끝값, 색, 구간 이름]이고, 지금 값이 든 구간의 이름과 색이 카드의 상태다.
FEAR_GREED_ZONES = [[25, DOWN, "극단 공포"], [45, DOWN, "공포"], [55, NEUTRAL, "중립"], [75, UP, "탐욕"], [100, UP, "극단 탐욕"]]
WEEKS = 12  # 하이일드 스프레드의 막대 그림이 거슬러 그리는 주 수
OIL_STEP = 10  # 유가 선 그림의 점선 가로선 간격(달러). 세로축 아래위 끝도 이 간격의 배수로 잡는다
RATE_MOVE_BP = 12.5  # 다음 회의까지 누적 변화가 이 bp 이상이면 인상 예상, 음수로 이 값 이하면 인하 예상
RATE_STEP_BP = 25  # 연준이 기준금리를 한 번에 바꾸는 폭. 금리 경로 그림의 세로축 상한을 이 폭의 배수로 잡고, 이 폭의 위아래 높이에 점선 가로선을 긋는다


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


def batch_data(vault: Path, index: str, day: dt.date) -> tuple[dict, dict] | None:
    """그날 지수 폴더의 (`market-data.json`, `macro-data.json`). `market-data.json`이 없으면 None."""
    folder = report_path(vault, day, index).parent
    market = folder / "market-data.json"
    if not market.is_file():
        return None
    macro = folder / "macro-data.json"
    return (json.loads(market.read_text(encoding="utf-8")),
            json.loads(macro.read_text(encoding="utf-8")) if macro.is_file() else {})


def readings(market: dict, macro: dict) -> dict[str, tuple[str, dict]]:
    """`report-template.md` `미국 거시 지표` 표의 지표 이름마다 (기준일, 원값). 값을 수집하지 못한 지표는 뺀다.

    수집기는 미국 장의 날짜를 적는다. 미국 장은 한국 시각으로 다음 날 아침에 마감하므로 기준일은 그 날짜에 하루를 더한 한국 날짜다.
    """
    as_of = market.get("as_of")
    oil = (market.get("market") or {}).get("WTI") or {}
    high_yield = (macro.get("fred") or {}).get("하이일드 스프레드") or {}
    path = (macro.get("policy") or {}).get("연방기금 선물 내재 경로") or {}
    found = {
        "공포·탐욕 지수": (as_of, macro.get("fear_greed"), "score"),
        "WTI 유가": (oil.get("date"), oil, "weekly_close"),
        "연준 금리 경로": (path.get("date"), path, "meetings"),
        "하이일드 스프레드": (high_yield.get("date"), high_yield, "pct_1y"),
    }
    return {name: ((dt.date.fromisoformat(date) + dt.timedelta(days=1)).isoformat(), value)
            for name, (date, value, key) in found.items()
            if date and isinstance(value, dict) and value.get(key) is not None}


def signed(value: float, digits: int = 1) -> str:
    """부호를 붙인 숫자. 빼기는 `−`로 쓰고, 반올림해 0이 되면 부호를 붙이지 않는다."""
    text = f"{value:+.{digits}f}"
    return text[1:] if float(text) == 0 else text.replace("-", "−")


def zone(zones: list[list], value: float) -> list:
    """`value`가 든 구간의 [이름, 색]."""
    found = next((item for item in zones if value <= item[0]), zones[-1])
    return [found[2], found[1]]


def year_rank(rank: float) -> list:
    """1년 백분위 `rank`를 `1년 상위 N%`·`1년 하위 N%`로 적은 상태. 값이 클수록 하락 쪽인 지표에 쓰므로 상위 20% 안은 파랑, 하위 20% 안은 빨강이다."""
    name = ("1년 최고" if rank >= 100 else "1년 최저" if rank <= 0 else
            f"1년 상위 {100 - rank:g}%" if rank >= 50 else f"1년 하위 {rank:g}%")
    return [name, DOWN if rank >= 80 else UP if rank <= 20 else NEUTRAL]


def month_day(day: str) -> str:
    """`2026-11-06`을 `11/6`으로 적는다."""
    return f"{int(day[5:7])}/{int(day[8:10])}"


def indicator_card(name: str, date: str, value: dict, weeks: list[tuple[str, dict]], before: tuple[str, dict] | None) -> dict:
    """지표 하나의 카드 값. `weeks`는 앞 `WEEKS`주 동안 주마다 마지막 (기준일, 원값)이고 마지막 항목이 오늘 값이다.
    `before`는 오늘 기준일 바로 앞 기준일의 (기준일, 원값)이고, 반원 속도계는 그 값을 연한 회색으로 함께 그린다.
    반원 속도계는 작은 값을 왼쪽에, 큰 값을 오른쪽에 둔다.
    주별 막대 그림(`columns`)은 가로축이 시간이므로 지난주를 왼쪽에, 오늘을 오른쪽에 둔다. 연준 금리 경로(`diverge`)도 가로축이 시간이므로 가까운 회의를 왼쪽에 두고, 0 가로선 위에 인상을, 아래에 인하를 둔다.
    금리 경로의 세로축 상한(`max`)은 가장 큰 누적 변화를 금리 한 번 변경 폭(`RATE_STEP_BP`)의 배수로 올린 값이고, 그림은 그 폭(`step`)의 위아래 높이에 점선 가로선을 긋는다.
    유가의 선 그림(`line`)은 원값의 주별 정산가를 지난주부터 오늘까지 왼쪽에서 오른쪽으로 잇는다. 정산가 날짜도 미국 장의 날짜이므로 하루를 더해 적는다.
    `help`는 카드 이름 뒤의 물음표 단추가 띄우는 설명 상자의 문단 목록이고, 지표를 무엇으로 계산하는지와 값을 읽는 법을 쓴다."""
    when = month_day(date)
    if name == "공포·탐욕 지수":
        score = value["score"]
        guide = ["CNN이 미국 주식시장의 투자 심리를 0점에서 100점 사이로 매긴 점수예요. CNN은 지표 7개를 합쳐 점수를 계산해요: S&P500의 추세, "
                 "52주 신고가와 신저가 종목 수, 상승 종목과 하락 종목의 거래량, 풋옵션과 콜옵션의 거래 비율, VIX, 주식과 국채의 수익률 차이, 정크본드 수요.",
                 "점수가 25 이하면 극단 공포, 45 이하면 공포, 55 이하면 중립, 75 이하면 탐욕, 그보다 크면 극단 탐욕이에요. "
                 "점수가 낮을수록 투자자는 주식을 팔고 국채 같은 안전자산을 더 많이 사요. 시장에서는 극단 공포를 매도가 지나쳤다는 신호로 보기도 해요."]
        return {"tab": "공포·탐욕", "help": guide, "asof": f"CNN · {when}", "value": f"{score:g}", "state": zone(FEAR_GREED_ZONES, score),
                "figure": {"type": "semi", "min": 0, "max": 100, "zones": FEAR_GREED_ZONES, "value": score,
                           "before": before and before[1]["score"], "ends": ["공포", "탐욕"]}}
    if name == "하이일드 스프레드":
        level = value["value"]
        guide = ["미국 하이일드 회사채의 금리에서 만기가 비슷한 미국 국채의 금리를 뺀 값이에요. 하이일드 회사채는 신용등급이 투자 적격 등급보다 낮은 회사채예요. "
                 "스프레드는 채권 투자자가 회사의 부도 위험을 떠안는 대가로 국채보다 더 요구하는 금리예요.",
                 "투자자는 경기가 나빠질 것으로 보면 하이일드 회사채를 팔아요. 그러면 회사채 금리가 올라 스프레드가 커져요. "
                 "상태의 1년 상위 %는 지난 1년 가운데 오늘보다 스프레드가 높았던 날의 비율이에요. 1년 상위 3%면 오늘보다 높았던 날이 3%뿐이에요."]
        top = math.ceil(max(item["value"] for _, item in weeks) + 0.3)
        return {"tab": "신용", "help": guide, "asof": f"FRED · {when}", "value": f"{level:.2f}", "unit": "%",
                "state": year_rank(value["pct_1y"]),
                "figure": {"type": "columns", "bars": [[month_day(day), item["value"], f"{item['value']:.2f}%"] for day, item in weeks],
                           "max": top, "lines": [[step, f"{step}%"] for step in range(1, top + 1)]}}
    if name == "WTI 유가":
        level = value["value"]
        guide = ["미국 텍사스산 원유(WTI)의 선물 가격이에요. 뉴욕상업거래소에서 거래하는 가장 가까운 만기 계약의 1배럴 값을 달러로 적어요. "
                 "카드의 값은 CME가 발표한 그날의 정산가이고, 그림은 지난 12주 동안 주마다 마지막 정산가를 이어 그려요.",
                 "유가가 오르면 기업의 연료비와 운송비가 늘고 소비자 물가도 올라요. 물가가 오르면 연준이 기준금리를 내리기 어려워져 주가에 부정적이에요. "
                 "상태의 1년 상위 %는 지난 1년 가운데 오늘보다 유가가 높았던 날의 비율이에요."]
        prices = [price for _, price in value["weekly_close"]]
        low, high = math.floor(min(prices) / OIL_STEP) * OIL_STEP, math.ceil(max(prices) / OIL_STEP) * OIL_STEP
        points = [[month_day((dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()), price, f"{price:.2f}"]
                  for day, price in value["weekly_close"]]
        return {"tab": "유가", "help": guide, "asof": f"WTI 정산가 · {when}", "value": f"{level:.2f}", "unit": "달러",
                "state": year_rank(value["pct_1y"]),
                "figure": {"type": "line", "points": points, "min": low, "max": high,
                           "lines": [[step, f"{step}달러"] for step in range(low, high + 1, OIL_STEP)]}}
    meetings = value["meetings"][:3]
    first = meetings[0]
    month = f"{int(first['meeting'][5:7])}월"
    move = first["cumulative_bp"]
    state = ([f"{month} 인상 예상", DOWN] if move >= RATE_MOVE_BP else [f"{month} 인하 예상", UP] if move <= -RATE_MOVE_BP
             else [f"{month} 동결 예상", NEUTRAL])
    rows = [[f"{int(item['meeting'][5:7])}월", item["cumulative_bp"], f"{signed(item['cumulative_bp'] / 100, 2)}%p"]
            for item in meetings]
    top = max(2 * RATE_STEP_BP, math.ceil(max(abs(row[1]) for row in rows) / RATE_STEP_BP) * RATE_STEP_BP)
    guide = ["연방기금 금리 선물은 미국 기준금리의 한 달 평균에 거는 계약이에요. 선물 가격에서 시장이 예상하는 기준금리를 계산해요. "
             "카드는 앞으로 열리는 연준 회의 세 번마다 기준금리의 누적 변화를 %p로 보여 줘요. 누적 변화는 지금 기준금리와 그 회의 뒤 예상 기준금리의 차이예요.",
             "값이 +0.25%p면 시장은 그 회의까지 0.25%p 인상 한 번을 예상해요. "
             f"다음 회의까지 누적 변화가 +{RATE_MOVE_BP / 100:g}%p 이상이면 인상 예상, −{RATE_MOVE_BP / 100:g}%p 이하면 인하 예상, 그 사이면 동결 예상이에요. "
             "기준금리가 오르면 기업의 차입 비용이 커져요. 그래서 인상 예상은 주가에 부정적이에요."]
    return {"tab": "금리 경로", "help": guide, "asof": f"연방기금 선물 · {when}", "value": signed(move / 100, 2), "unit": "%p", "state": state,
            "figure": {"type": "diverge", "rows": rows, "max": top, "step": RATE_STEP_BP}}


def indicator_cards(vault: Path, index: str, date: dt.date) -> dict[str, dict]:
    """그날 리포트의 지표 이름마다 카드 값. 앞 `WEEKS`주 리포트의 값을 기준일마다 모아 주마다 마지막 값을 함께 넘긴다."""
    current = batch_data(vault, index, date)
    if not current:
        return {}
    found: dict[str, dict[str, dict]] = {}
    for back in range(WEEKS * 7 + 7, 0, -1):
        past = batch_data(vault, index, date - dt.timedelta(days=back))
        for name, (day, value) in (readings(*past) if past else {}).items():
            found.setdefault(name, {})[day] = value
    cards = {}
    for name, (day, value) in readings(*current).items():
        seen_values = sorted({**found.get(name, {}), day: value}.items())
        weekly = {dt.date.fromisoformat(seen).isocalendar()[:2]: (seen, item) for seen, item in seen_values}
        earlier = [(seen, item) for seen, item in seen_values if seen < day]
        cards[name] = indicator_card(name, day, value, list(weekly.values())[-WEEKS:], earlier[-1] if earlier else None)
    return cards


def mark_indicators(body: str, cards: dict[str, dict]) -> str:
    """`미국 거시 지표` 절의 소제목 가운데 `cards`에 있는 지표에 카드 값(`data-card`)을 단다."""
    head = re.search(rf'<h2 id="[^"]*">{INDICATORS_TITLE}</h2>', body)
    if not head:
        return body
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end

    def heading(match: re.Match) -> str:
        name = html.unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip()
        if name not in cards:
            return match.group(0)
        card = html.escape(json.dumps(cards[name], ensure_ascii=False))
        return f'<h3{match.group(1)} data-card="{card}">{match.group(2)}</h3>'

    section = re.sub(r"<h3([^>]*)>(.*?)</h3>", heading, body[head.end():end], flags=re.DOTALL)
    return body[:head.end()] + section + body[end:]



def mark_issue_ids(body: str, bundles: Path) -> str:
    """`상세 이슈 해설` 절의 번호 붙은 이슈 소제목에 `system/issues.json`의 그 번호 `id`를 `data-issue`로 단다."""
    head = re.search(rf'<h2 id="[^"]*">{ISSUES_TITLE}</h2>', body)
    if not head or not bundles.is_file():
        return body
    ids = {bundle["issue"]: bundle["id"] for bundle in json.loads(bundles.read_text(encoding="utf-8"))["issues"]}
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end

    def heading(match: re.Match) -> str:
        number = re.match(r"(\d+)\.\s", html.unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip())
        issue = ids.get(int(number.group(1))) if number else None
        if not issue:
            return match.group(0)
        return f'<h3{match.group(1)} data-issue="{html.escape(issue)}">{match.group(2)}</h3>'

    section = re.sub(r"<h3([^>]*)>(.*?)</h3>", heading, body[head.end():end], flags=re.DOTALL)
    return body[:head.end()] + section + body[end:]


def mark_issue_images(body: str, assets: Path, target: Path, out: Path) -> str:
    """`상세 이슈 해설` 절의 번호 붙은 이슈 소제목 뒤에 `assets/issue-{번호}.webp` 그림과 썸네일 주소를 넣는다. 그림이 없는 이슈는 그대로 둔다."""
    head = re.search(rf'<h2 id="[^"]*">{ISSUES_TITLE}</h2>', body)
    if not head:
        return body
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end

    def heading(match: re.Match) -> str:
        number = re.match(r"(\d+)\.\s", html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip())
        image = assets / f"issue-{number.group(1)}.webp" if number else None
        if not image or not image.is_file():
            return match.group(0)
        shutil.copy2(image, target / image.name)
        thumb = target / f"{image.stem}-thumb.webp"
        with Image.open(image) as picture:
            side = min(picture.size)
            box = ((picture.width - side) // 2, (picture.height - side) // 2)
            picture.convert("RGB").crop((*box, box[0] + side, box[1] + side)).resize((THUMB, THUMB), Image.Resampling.LANCZOS).save(thumb, format="WEBP", quality=80)
        return (f'{match.group(0)}\n<figure class="issue-image" data-thumb="{versioned(thumb, out)}">'
                f'<img src="{versioned(target / image.name, out)}" alt="">'
                f"<figcaption>AI 생성 이미지</figcaption></figure>")

    section = re.sub(r"<h3[^>]*>(.*?)</h3>", heading, body[head.end():end], flags=re.DOTALL)
    return body[:head.end()] + section + body[end:]


def mark_issue_charts(body: str, plan: Path) -> str:
    """`상세 이슈 해설` 절의 번호 붙은 이슈마다 `system/issue-charts.json`의 카드 값을 이슈 해설 말머리 뒤 `after`번째 문단 다음에 넣는다."""
    head = re.search(rf'<h2 id="[^"]*">{ISSUES_TITLE}</h2>', body)
    if not head or not plan.is_file():
        return body
    cards = {chart["card"]["issue"]: chart["card"] for chart in json.loads(plan.read_text(encoding="utf-8")).get("charts", [])
             if "card" in chart}
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end
    section = body[head.end():end]
    starts = [match.start() for match in re.finditer(r"<h3[^>]*>", section)] + [len(section)]
    parts = [section[:starts[0]]]
    for start, stop in zip(starts, starts[1:]):
        issue = section[start:stop]
        number = re.match(r"(\d+)\.\s", html.unescape(re.sub(r"<[^>]+>", "", issue[:issue.find("</h3>")])).strip())
        lead = issue.find("</h4>")
        card = cards.get(int(number.group(1))) if number else None
        if card and lead >= 0:
            closes = [match.end() for match in re.finditer(r"</p>", issue[lead:])]
            if closes:
                at = lead + closes[min(card["after"], len(closes)) - 1]
                figure = f'\n<figure class="issue-chart" data-card="{html.escape(json.dumps(card, ensure_ascii=False))}"></figure>'
                issue = issue[:at] + figure + issue[at:]
        parts.append(issue)
    return body[:head.end()] + "".join(parts) + body[end:]


def issue_segments(body: str) -> list[tuple[int, int]]:
    """`상세 이슈 해설` 절에서 이슈 소제목마다 소제목부터 다음 소제목 앞까지의 위치."""
    head = re.search(rf'<h2 id="[^"]*">{ISSUES_TITLE}</h2>', body)
    if not head:
        return []
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end
    starts = [match.start() for match in re.compile(r"<h3[^>]*>").finditer(body, head.end(), end)] + [end]
    return list(zip(starts, starts[1:]))


def explainer_title(segment: str) -> str:
    """이슈 조각의 이슈 해설 말머리 뒤 소제목."""
    title = re.search(r"<h4[^>]*><mark>이슈 해설</mark>(.*?)</h4>", segment, re.DOTALL)
    return html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else ""


def issue_history(vault: Path, index: str, day: dt.date, out: Path) -> dict[str, list[tuple[dt.date, str]]]:
    """오늘 이슈 `id`마다, 그 `id`를 노드로 묶은 앞 날짜 이슈의 날짜와 공개본 이슈 조각을 날짜 순으로."""
    bundles = report_path(vault, day, index).parent / "system" / "issues.json"
    if not bundles.is_file():
        return {}
    history = {bundle["id"]: [] for bundle in json.loads(bundles.read_text(encoding="utf-8"))["issues"]}
    for source in sorted(vault.glob(f"routine/invest/*/*/{index}/system/issues.json")):
        name = source.parent.parent.parent.name
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", name) or (past := dt.date.fromisoformat(name)) >= day:
            continue
        page = out / "r" / f"{past:%Y%m%d}-{index}" / "report.html"
        if not page.is_file():
            continue
        body = HISTORY_RE.sub("", page.read_text(encoding="utf-8"))
        segments = {}
        for start, stop in issue_segments(body):
            issue = re.match(r'<h3[^>]*data-issue="([^"]*)"', body[start:stop])
            if issue:
                segments[html.unescape(issue.group(1))] = body[start:stop]
        for bundle in json.loads(source.read_text(encoding="utf-8"))["issues"]:
            for issue in history:
                if issue in bundle["nodes"] and bundle["id"] in segments:
                    history[issue].append((past, segments[bundle["id"]]))
    return history


def mark_issue_history(body: str, history: dict[str, list[tuple[dt.date, str]]], day: dt.date) -> str:
    """번호 붙은 이슈 뒤에 앞 날짜 이슈 조각과 날짜마다 이슈 해설 소제목을 담은 `issue-history` 템플릿을 넣는다."""
    parts, last = [], 0
    for start, stop in issue_segments(body):
        segment = body[start:stop]
        issue = re.match(r'<h3[^>]*data-issue="([^"]*)"', segment)
        past = history.get(html.unescape(issue.group(1)), []) if issue else []
        if not past:
            continue
        days = [(when, explainer_title(chunk), re.sub(r'\sid="[^"]*"', "", chunk)) for when, chunk in past]
        days.append((day, explainer_title(segment), ""))
        sections = "".join(f'<section data-day="{when}" data-title="{html.escape(title)}">{chunk}</section>'
                           for when, title, chunk in days)
        parts += [body[last:stop].rstrip(), f'\n<template class="issue-history">{sections}</template>\n']
        last = stop
    return "".join(parts) + body[last:]


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
    body = mark_indicators(body, indicator_cards(vault, index, day))
    body = mark_issue_ids(body, source.parent / "system" / "issues.json")
    body = mark_issue_images(body, source.parent / "assets", target, out)
    body = mark_issue_charts(body, source.parent / "system" / "issue-charts.json")
    body = mark_issue_history(body, issue_history(vault, index, day, out), day)
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
