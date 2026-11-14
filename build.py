#!/usr/bin/env python3
"""build — 판단 리포트 공개본을 `invest-reports` `invest-reports` 미니 앱(`app.html`)이 읽는 HTML 조각으로 만든다. `run-with-notify.sh`의 `publish_miniapp`이 만든 조각을 게시한다.

사용법: python3 build.py --date 2026-10-19 --index nasdaq [--vault ~/obsidian-vault] [--out .]

`r/{YYYYMMDD}-{지수}/`에 `report.html`과 그림을 쓰고 `r/index.json`의 목록을 갱신한다. `invest-reports` 미니 앱은
`start_param`으로 받은 `{YYYYMMDD}-{지수}`를 열어 그 조각을 그리고, 키 없이 열리면 목록에서 가장 늦은 나스닥 리포트를 연다.

공개본이 끝나는 자리와 공개본에 남으면 안 되는 말은 invest-report `report_pdf.py`의 값을 그대로 쓴다.
PDF와 `invest-reports` 미니 앱이 같은 자리에서 자르므로, 공개 채널로 나가는 두 판본의 내용이 같다.

`이벤트 캘린더` 표는 분기·확률·전개 예상 세 열이다. 휴대폰 폭에서 분기 이름이 접히지 않게 열마다
폭과 정렬을 정하는 이름표를 단다.

`이벤트 캘린더` 절에는 앞 리포트들이 적은 이벤트 가운데 리포트 날짜 전에 발표된 이벤트를 모두 넣는다. 리포트가 같은 사안 id의 이벤트를 이미
적었으면 리포트의 표만 둔다. 발표일마다 그날 이벤트를 적은 가장 최근 리포트의 소제목과 표를 쓰고, 더 최근 리포트가 다른 날로 옮겨 적은
사안 id의 이벤트는 뺀다. 그 리포트의 사안 나무(`tree.json`)에서 이벤트의 사안 id를 찾아 뒤 사안 나무의 `resolved`가
그 id로 적은 실제 갈래 줄에 `hit` 이름표를 단다. `resolved`의 갈래는 갈래 id이므로, 표를 쓴 리포트의 사안 나무에서
그 id의 갈래 이름을 찾아 표의 줄과 잇는다. 갈래 id가 없는 앞 날짜 나무는 사안마다 나무 순서대로 `b1`부터 번호를 붙여
읽고, 갈래 id가 아닌 `resolved` 갈래는 이름으로 읽는다.
실제 갈래 줄의 전개 예상 뒤에는 `resolved`의 실제 전개(`outcome`)를 화살표와 함께 붙인다.
발표일 뒤 첫 리포트에 그 이벤트의 결과를 다룬 이슈가 있으면 실제 갈래 줄에 `리포트 키/이슈 번호`를 `data-result`로 단다.
결과를 다룬 이슈는 그 리포트 바로 앞 리포트가 이벤트의 사안과 같은 사안으로 보는 노드를 `id`나 노드로 가진 이슈다(`data-event`와 같은 기준).
`invest-reports` 미니 앱은 실제 갈래 줄 아래에 "자세히 보기" 단추를 두고, 누르면 그 이슈를 이은 가장 늦은 리포트의 이슈 화면을 연다.
리포트 날짜와 그 뒤 이벤트의 표는 리포트 폴더 `system/display.json` `next`의 갈래 변화(`change`)를 확률 아래 작은 글씨로
붙인다. 표의 분기 이름이 모두 한 사안의 갈래 이름이면 그 사안의 표로 본다. 오르면 `▲`, 내리면 `▼`와 %p 차이를 쓰고,
변화가 없으면 `–`, 어제 나무에 없던 갈래는 `신규`, 오늘 다시 정의한 갈래는 `재정의`를 쓴다.
이벤트 소제목마다 발표일을 `data-day`로 달고 제목에서는 날짜를 지운다. `invest-reports` 미니 앱은 이 값으로 날짜 띠를 그리고
같은 날 이벤트를 한 장에 모은다. 제목 위에는 사안 나무의 발표 시각(`announced`)을 한국 시각(KST)으로 적는다.
발표 시각이 수집기가 채운 기본값(`PLACEHOLDER_TIMES`)이거나 사안 나무에 없으면 장전·장중·장후만 적는다.
중요도는 `data-level`로 달아 `invest-reports` 미니 앱이 날짜 띠에 점으로 그린다.

`미국 거시 지표` 절의 지표 소제목에는 그날 지수 폴더의 `market-data.json`·`macro-data.json`에서 뽑은 카드 값을 `data-card`로 단다.
하이일드 스프레드는 앞 12주 지수 폴더의 같은 JSON에서 주마다 마지막 값을 함께 뽑아 막대 그림으로 그린다.
유가는 그날 `market-data.json` `market.WTI`의 지난 1년 일별 정산가(`daily_close`)를 선 그림으로 그린다.
정산가를 적지 않은 배치는 `reference.db`의 WTI 종가에서 그 배치 미국 장 날짜까지 1년을 잘라 값·1년 백분위·선 그림을 만든다.
카드 값은 탭 이름, 값과 단위, 상태 이름과 색, 기준일(미국 장이 마감한 한국 날짜), 보조 값을 적은 한 줄, 그림 종류와 그림 입력, 물음표 단추의 설명이다.
값이 없는 지표에는 카드 값을 달지 않는다.
`invest-reports` 미니 앱은 카드 값으로 지표마다 카드를 그려 한 장씩 넘기게 하고, 카드 값이 없는 소제목은 지운다.
공개본이 있는 그 지수 리포트 가운데 가장 늦은 날짜에서 `REWIND_DAYS`일 안의 리포트 날짜마다 같은 카드 값에서 탭 이름과 설명을 뺀 값을
`r/rewind-{지수}/indicators.json`에 쓴다. 미니 앱은 지표 카드의 그림과 해설 사이에 날짜 슬라이더를 두고, 슬라이더를 옮기면
그날 카드 값으로 그 카드의 기준일·값·그림을 다시 그린다. 해설은 리포트 날짜의 해설을 그대로 둔다.

`상세 이슈 해설` 절의 번호 붙은 이슈 소제목에는 리포트 폴더 `system/issues.json`에서 그 번호의 `id`를 `data-issue`로 단다.
`id`는 Main이 그 이슈로 묶은 사안 나무 노드 가운데 반영 정도가 가장 큰 노드의 이름이므로, 날짜가 다른 리포트에서 같은 사안을 다룬 이슈는 같은 값을 갖는다.
바로 앞 리포트의 `이벤트 캘린더` 절이 적은 이벤트 가운데 앞 리포트 날짜부터 리포트 날짜 전날까지 발표된 이벤트의 결과를 다룬 이슈 소제목에는
그 이벤트 이름을 `data-event`로 단다. 이벤트의 사안 id는 앞 리포트 사안 나무에서 이벤트의 사안(`item`)이고, 앞 리포트 `system/issues.json`에서
그 사안을 노드로 묶은 이슈의 노드도 같은 사안으로 본다. 오늘 이슈의 `id`나 노드가 그 사안 가운데 하나이면 그 이벤트의 결과를 다룬 이슈다.
트리거 노드(`trigger:`)는 여러 사안에 걸치므로 사안으로 보지 않는다. 한 이슈에 이벤트가 여럿이면 이름을 ` · `로 잇는다.
그 이벤트가 모두 중요도 낮음이면 `data-event-level="low"`도 단다.
`invest-reports` 미니 앱은 그 이슈 상자에 외곽선을 두르고 외곽선 위쪽 왼쪽에 "10월 CPI 이벤트"처럼 이벤트 이름표를 단다.
외곽선과 이름표는 날짜 띠의 별처럼 중요도 높음·보통 이벤트면 지수색, 낮음 이벤트만이면 회색으로 칠한다.
번호 붙은 이슈 뒤에는 그 `id`를 노드로 묶은 앞 날짜 이슈를 `issue-history` 템플릿으로 넣는다. 앞 날짜 이슈는 그날 `system/issues.json`의
`nodes`에 오늘 `id`가 든 이슈이고, 내용은 그날 공개본 `report.html`의 이슈 조각을 그대로 쓴다. 템플릿에는 오늘을 포함한 모든 날짜의
날짜와 이슈 해설 소제목을 날짜 순으로 적고, 오늘 항목에는 내용을 넣지 않는다. 앞 날짜 이슈가 없는 이슈에는 템플릿을 넣지 않는다.
`invest-reports` 미니 앱은 템플릿으로 이슈 그림과 이슈 해설 사이에 오늘부터 앞 날짜 순으로 히스토리 상자를 그리고, 소제목을 누르면 이슈 문단을 그날의 내용으로 바꾼다.
번호 붙은 이슈 소제목 뒤에는 리포트 폴더 `assets/issue-{번호}-{순번}.webp`가 있는 그림을 순번대로 한 그림 묶음에 넣는다. 그림은 이슈마다 한 장에서 세 장이다.
그림마다 위에 `AI 생성 이미지` 표시를 얹고, `system/issue-images.json`에 그 그림의 사진 설명(`caption`)이 있으면 그림 아래 캡션에 쓴다. 그림은 `run-with-notify.sh`가 ⑨의 이슈 이미지 선정 결과로 만든다. 첫 그림의 정사각을 잘라
`THUMB`px 썸네일 `issue-{번호}-thumb.webp`를 만들어 묶음의 `data-thumb`에 적는다. `invest-reports` 미니 앱은 이슈 목록 상자에 썸네일을 붙이고, 그림이 두 장 이상인 묶음은 넘겨 보는 묶음과 쪽 점으로 그린다.
이슈 해설 말머리 뒤 문단 사이에는 리포트 폴더 `system/issue-charts.json`의 카드 값을 `issue-chart` 그림의 `data-card`로 넣는다.
카드 값은 ⑨의 이슈 그래프 agent가 설계하고 `issue_charts.py fill`이 채우며, 카드 값이 없는 그래프는 넣지 않는다.
그래프는 설계의 `after`번째 문단 다음에 들어가고, 문단이 그보다 적으면 마지막 문단 다음에 들어간다.
`invest-reports` 미니 앱은 카드 값으로 `미국 거시 지표` 카드와 같은 모양의 선 그래프·막대 그래프·표 카드를 그린다.
리포트 폴더 `system/terms.json`이 있으면 마크다운을 공개본으로 바꾸기 전에 그 자리마다 용어 표기를 `term` 단추로 감싸고,
대표 표기를 `data-term`에, 단어표 설명을 `data-desc`에 단다. 자리는 ⑧의 교정 agent가 `glossary.py scan`·`check`로 문맥을 확인해 고른
(절, 묶음 제목, 표기, 묶음 안에서 몇 번째 표기인지)이고, 리포트를 맞춰 보는 방식은 invest-report `glossary.py`의 `mark`를 그대로 쓴다.
리포트가 판정 뒤에 바뀌어 찾지 못한 자리는 감싸지 않고 표준 오류로 알린다. `invest-reports` 미니 앱은 단추에 점선 밑줄을 긋고,
누르면 용어 아래에 대표 표기와 설명을 담은 말풍선을 연다.

`r/index.json`에는 리포트마다 제목, 날짜 줄(`day`), 처음 만든 시각(`written`, 서울 시각)을 적는다.
앞 날짜 리포트의 이슈가 뒤 리포트 이슈의 히스토리에 들면, 앞 날짜 리포트 항목의 `later`에 그 이슈 번호를 키로 히스토리를 가진
가장 늦은 리포트의 `리포트 키/이슈 번호`를 적는다. 미니 앱의 "자세히 보기" 단추는 이 값으로 이슈의 가장 늦은 히스토리를 연다. `invest-reports` 미니 앱은 제목 위
작은 글씨로 날짜 줄을 그린다. 같은 리포트를 다시 만들어도 처음 만든 시각은 그대로 둔다.
`invest-reports` 미니 앱의 달력은 같은 목록에서 그 지수의 리포트 날짜를 찾아 흰 글자로 쓰고, 날짜 아래에 `moves`의 `session`을 적는다.
`moves`에는 리포트 날짜 전날 정규장 종가의 앞 세션 종가 대비 등락률(`session`, %)과 기준 가격의 기준 가격 날짜 종가 대비
등락률(`after`, %), 기준 가격 날짜의 환산 종가(`close`, 달러)와 기준 가격(`base`, 달러)을 적는다. 전날이 휴장일이면 `session`은 `null`이다.
두 등락률과 두 가격은 `path-bands.json`의 ^NDX·^NBI 환산 가격과 `reference.db` 환산 종가로 재므로 12M + Predictions 그림의 종가 선, 기준 가격과 같은 눈금이다.
`invest-reports` 미니 앱은 제목 아래 머리 줄에 지수 이름, 환산 종가, `session` 등락률을 적은 줄과 `장 마감 후`, 기준 가격, `after` 등락률을
적은 줄을 번갈아 보여 준다. 등락률만 오르면 빨강, 내리면 파랑으로 칠하고 `null`은 `—`로 적는다. 화면을 내리면 머리 줄은 화면 위에 붙어 남는다.

`system/simulation.json`의 `quantiles`에 5% 값이 있는 리포트는 요약 절 세 그림을 그림 파일 대신 값으로 그린다.
그런 리포트의 공개본에서는 12M + Predictions·Montecarlo·권장 추종 배율 그림을 빼고, `report.html` 끝에 카드 값을
`<script type="application/json" id="cards">`로 붙인다. 카드 값은 `PRICE_YEARS`년 종가와 날짜, 지난 리포트가 예측한 25거래일 뒤 가격,
그날 25·50·75% 가격, 10~90% 수익률 분위수와 사안 일정, 체류 적분 밀도를 담는다(`summary_cards`). 공개본이 있는 그 지수 리포트
가운데 가장 늦은 날짜에서 `REWIND_DAYS`일 안의 카드 값 리포트는 되감기 날짜가 되고, `r/rewind-{지수}/cards.json`에 날짜마다
같은 판단 값과 그날 기준 가격 뒤의 실제 종가 수익률(%)을 쓴다. `invest-reports` 미니 앱은 카드 값으로 그림 카드를
그리고, 슬라이더를 옮기면 그날 판단 값으로 세 카드를 다시 그린다.
"""
import argparse
import datetime as dt
import functools
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
EVENTS_TITLE = "이벤트 캘린더"
# 이벤트 소제목 앞의 발표일. `2026-10-21(수)`, `2026-10-21(수)~10-28(수)`, `10/26(월) 장전` 꼴이다.
EVENT_DAY_RE = re.compile(r"^(?:(\d{4})-)?(\d{1,2})[-/](\d{1,2})\([^)]*\)(?:~\S+)?\s*(?:(장전|장중|장후)\s+)?")
LEVEL_RE = re.compile(r"\s*`중요도 ([^`]*)`")
LEVELS = {"높음": "high", "보통": "mid", "낮음": "low"}  # 소제목 중요도 표식의 말과 `data-level` 값
LOOKBACK = 7  # 발표 시각을 찾을 때 리포트 날짜 뒤로 보는 리포트 날짜 수
REGULAR_OPEN, REGULAR_CLOSE = "09:30", "16:00"  # 뉴욕 정규장 시각. 발표 시각을 장전·장중·장후로 나눈다
# 발표 시각을 모를 때 채우는 뉴욕 시각. 실적의 장전(bmo)·장후(amc) 단서는 `calendar_store.py`가 08:00·16:05로,
# 장중(dmh)은 `render_inputs.py`가 12:00으로 채우고, 단서가 없는 발표는 16:00으로 적는다. 이 시각은 장 구분만 적는다.
PLACEHOLDER_TIMES = {"08:00", "12:00", "16:00", "16:05"}
NEW_YORK, SEOUL = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")
# 리포트 제목 끝의 날짜 줄. `나스닥 리포트 2026-10-22 (목)` 꼴이다.
TITLE_RE = re.compile(r"^(.*\S)\s+(\d{4}-\d{2}-\d{2} \([^)]*\))$")
REWIND_DAYS = 30  # 되감기 슬라이더가 거슬러 가는 날짜 범위
CARD_QUANTILES = (10, 25, 50, 75, 90)  # Montecarlo 카드가 그리는 수익률 분위수
PRICE_YEARS = 3  # 주가와 예측 카드가 그리는 종가 기간(년)
TICK_STEP = 5  # Montecarlo 카드 가로축 날짜의 거래일 간격
INDICATORS_TITLE = "미국 거시 지표"
ISSUES_TITLE = "상세 이슈 해설"
HISTORY_RE = re.compile(r'<template class="issue-history">.*?</template>\s*', re.DOTALL)
THUMB = 264
UP, DOWN, NEUTRAL = "#ff5c5c", "#5b9bff", "#ffffff"  # 오름·내림·중립 색. 오름·내림 색은 `app.html`의 등락 색과 같다
# 지표 카드의 구간. [구간 끝값, 색, 구간 이름]이고, 지금 값이 든 구간의 이름과 색이 카드의 상태다.
FEAR_GREED_ZONES = [[25, DOWN, "극단 공포"], [45, DOWN, "공포"], [55, NEUTRAL, "중립"], [75, UP, "탐욕"], [100, UP, "극단 탐욕"]]
WEEKS = 12  # 하이일드 스프레드의 막대 그림이 거슬러 그리는 주 수
RATE_MOVE_BP = 12.5  # 다음 회의까지 누적 변화가 이 bp 이상이면 인상 예상, 음수로 이 값 이하면 인하 예상
RATE_STEP_BP = 25  # 연준이 기준금리를 한 번에 바꾸는 폭. 금리 경로 그림은 이 폭의 위아래 높이에 점선 가로선을 긋는다
RATE_RANGE_BP = 100  # 금리 경로 그림의 세로축 상한. 회의 세 번의 누적 변화는 보통 ±1%p 안에 들고, 넘는 막대는 축 끝에서 자른다


def report_pdf(vault: Path):
    sys.path.insert(0, str(vault / "agent/skills/tool/invest-report/scripts"))
    import report_pdf as module
    return module


def glossary(vault: Path):
    sys.path.insert(0, str(vault / "agent/skills/tool/invest-report/scripts"))
    import glossary as module
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
    """리포트 날짜 `date` 전날의 정규장 등락률과 장 마감 뒤 등락률(%), 기준 가격 날짜의 환산 종가와 기준 가격. `path-bands.json`이나 앞 세션 종가가 없으면 `None`."""
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
            "after": round((float(bands["price_base"]) / close - 1) * 100, 2) + 0.0,
            "close": round(close, 2), "base": round(float(bands["price_base"]), 2)}


def card_frame(date: str, folder: Path) -> dict | None:
    """그날 판단의 그림 카드 값. `system/simulation.json`의 `quantiles`에 5% 값이 없는 리포트는 `None`이다.

    `days`는 기준 가격 날짜에서 시작하는 거래일, `predict`는 그 거래일마다 25·50·75% 가격, `tree`는 수익률 분위수(%)와 발표일이 같은 사안의 묶음·가로축 날짜,
    `chart`는 체류 적분 밀도다. 가로축의 첫 날짜는 기준 가격 날짜가 아니라 리포트 날짜로 적는다.
    """
    path = folder / "system" / "simulation.json"
    simulation = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    quantiles = simulation.get("quantiles") or {}
    if "q5" not in quantiles:
        return None
    base = float(json.loads((folder / "path-bands.json").read_text(encoding="utf-8"))["price_base"])
    days = quantiles["days"]
    horizon = len(days) - 1
    same = {}
    for issue in simulation["issues"]:
        if 0 < issue.get("day", 0) <= horizon:
            same.setdefault(issue["day"], []).append(issue["name"])
    density = simulation["density"]
    return {"day": date, "base_date": days[0], "base": base, "days": days,
            "predict": {f"q{q}": [round(base * (1 + v), 2) for v in quantiles[f"q{q}"]] for q in (25, 50, 75)},
            "tree": {"pct": {str(q): [round(v * 100, 2) for v in quantiles[f"q{q}"]] for q in CARD_QUANTILES},
                     "events": [[day, names, month_day(days[day])] for day, names in sorted(same.items())],
                     "ticks": [[t, month_day(days[t] if t else date)] for t in range(0, horizon + 1, TICK_STEP)]},
            "chart": {**{k: density[k] for k in ("low", "high", "points", "mean")},
                      **{k: [round(v, 4) for v in density[k]] for k in ("today", "quiet")}}}


def summary_cards(index: str, date: str, folder: Path, vault: Path) -> dict | None:
    """요약 절 그림 카드 값. `card_frame`이 `None`인 리포트는 `None`이다.

    카드 값은 그날 판단(`card_frame`)에 판단 색, 기준 가격 날짜까지 `PRICE_YEARS`년 종가와 날짜, 기준 가격의 가로 거리,
    지난 리포트가 예측한 25거래일 뒤 가격(`past`, 가로 위치·25·50·75% 가격)을 더한다. 지난 예측은 12M + Predictions 그림과
    같은 줄을 고르고, 오늘 판단과 같은 기준 가격 날짜의 줄과 오늘 판단의 끝보다 오른쪽 줄은 뺀다.
    """
    frame = card_frame(date, folder)
    if not frame:
        return None
    chart = predictions_chart(vault)
    base_date = dt.date.fromisoformat(frame["base_date"])
    con = sqlite3.connect(f"file:{chart.path_bands.REFERENCE_DB_PATH}?mode=ro", uri=True)
    try:
        history = con.execute(
            "SELECT price_date, close FROM market_price WHERE ticker=? AND price_date BETWEEN ? AND ? ORDER BY price_date",
            (chart.path_bands.SECTOR_DB_TICKERS[index], (base_date - dt.timedelta(days=round(365.25 * PRICE_YEARS))).isoformat(),
             frame["base_date"])).fetchall()
    finally:
        con.close()
    dates = [day for day, _ in history]
    x0, horizon = len(dates) - 1, len(frame["predict"]["q50"]) - 1
    past = {}
    for base_date, (base, ahead, values) in chart.past_judgments(
            chart.read_ledger(chart.LEDGER_DIR / f"predictions-{index}.jsonl"), date).items():
        if base_date in dates and base_date != frame["base_date"] and dates.index(base_date) + ahead <= x0 + horizon:
            past[dates.index(base_date) + ahead] = [round(base * (1 + v), 2) for v in values]
    return {"color": chart.chart.JUDGMENT_COLORS.get(index, chart.chart.JUDGMENT_COLORS["nasdaq"])["line"],
            "start_offset": chart.START_OFFSET, "dates": dates, "history": [round(c, 2) for _, c in history],
            "past": [[x, *values] for x, values in sorted(past.items())], **frame}


def rewind(index: str, vault: Path, out: Path) -> Path | None:
    """`r/rewind-{지수}/`에 되감기 날짜마다 요약 절 카드 값(`cards.json`)과 지표 카드 값(`indicators.json`)을 쓴다.

    한쪽 값이 하나도 없으면 그 파일을 지우고, 두 파일이 모두 없으면 폴더를 지운다.
    """
    target = out / "r" / f"rewind-{index}"
    published = sorted(dt.date.fromisoformat(f"{p.name[:4]}-{p.name[4:6]}-{p.name[6:8]}")
                       for p in (out / "r").glob(f"*-{index}") if p.name[:8].isdigit())
    days = [day for day in published if published[-1] - day < dt.timedelta(days=REWIND_DAYS)]
    frames = [frame for day in days
              if (frame := card_frame(day.isoformat(), vault / f"routine/invest/{day:%Y-%m}/{day}/{index}"))]
    if frames:
        chart = predictions_chart(vault)
        until = frames[-1]["base_date"]
        for frame in frames:
            frame["tree"]["actual"] = actual_returns(chart.path_bands.REFERENCE_DB_PATH, chart.path_bands.SECTOR_DB_TICKERS[index],
                                                     frame["days"], frame["base"], until)
    gauges = [{"day": day.isoformat(), "cards": {name: {k: v for k, v in card.items() if k not in ("tab", "help")}
                                                 for name, card in cards.items()}}
              for day in days if (cards := indicator_cards(vault, index, day))]
    target.mkdir(parents=True, exist_ok=True)
    for name, items in (("cards.json", frames), ("indicators.json", gauges)):
        if items:
            (target / name).write_text(json.dumps({"frames": items}, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            (target / name).unlink(missing_ok=True)
    if not frames and not gauges:
        shutil.rmtree(target)
        return None
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


def mark_terms(text: str, terms: Path, vault: Path) -> str:
    """`system/terms.json`의 자리마다 리포트 마크다운의 용어 표기를 `term` 단추로 감싼다. 표 칸을 가르지 않게 속성 값의 `|`도 문자 참조로 바꾼다."""
    if not terms.is_file():
        return text

    def attr(value: str) -> str:
        return html.escape(value).replace("|", "&#124;")

    def wrap(form: str, term: dict) -> str:
        return (f'<button class="term" type="button" data-term="{attr(term["term"])}" '
                f'data-desc="{attr(term["desc"])}">{form}</button>')

    text, missing = glossary(vault).mark(text, json.loads(terms.read_text(encoding="utf-8"))["terms"], wrap)
    for term in missing:
        print(f"용어 자리를 찾지 못했다: {term['section']} · {term['block']} · {term['form']} {term['nth']}", file=sys.stderr)
    return text


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
    """리포트 마크다운의 `이벤트 캘린더` 절 본문."""
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


def reports(vault: Path, index: str, until: dt.date) -> list[Path]:
    """`until` 이전(그날 포함)의 지수 리포트 경로를 늦은 날짜부터."""
    found = (path for path in vault.glob(f"routine/invest/*/*/{index}/report.md") if path.parent.parent.name <= f"{until}")
    return sorted(found, key=lambda path: path.parent.parent.name, reverse=True)


def past_events(vault: Path, index: str, date: dt.date) -> tuple[str, dict[str, dict]]:
    """앞 리포트들이 적은 이벤트 가운데 리포트 날짜 전에 발표된 이벤트의 마크다운과, 이벤트 이름마다 `resolved` 항목.
    `resolved` 항목의 `result`에는 그 이벤트의 결과를 다룬 이슈(`result_issue`)를 적는다.

    발표일마다 그날 이벤트를 적은 가장 최근 리포트의 소제목과 표를 그 리포트의 순서대로 쓴다. 리포트 날짜의 리포트나
    더 최근 리포트가 이미 적은 사안 id의 이벤트는 뺀다.
    """
    current = report_path(vault, date, index)
    issues = tree_issues(current)
    seen = {issues[name]["id"] for _, name, _ in event_items(current.read_text(encoding="utf-8"), date)
            if name in issues}
    found: dict[dt.date, list[tuple[Path, str, str]]] = {}
    for source in reports(vault, index, date - dt.timedelta(days=1)):
        ids = {name: issue["id"] for name, issue in tree_issues(source).items()}
        latest: dict[dt.date, list[tuple[Path, str, str]]] = {}
        for day, name, chunk in event_items(source.read_text(encoding="utf-8"), date):
            if day < date and day not in found and ids.get(name) not in seen:
                latest.setdefault(day, []).append((source, name, chunk))
        found.update(latest)
        seen |= set(ids.values())
    blocks, branches = [], {}
    for day, source, name, chunk in ((day, *item) for day in sorted(found) for item in found[day]):
        entry = realized(vault, index, source, name, day, date)
        blocks.append(chunk.rstrip() + "\n")
        if entry:
            branches[name] = {**entry, "result": result_issue(vault, index, source, name, day, date)}
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

    리포트 날짜 뒤 `LOOKBACK`일까지의 모든 사안 나무에서 발표 시각을 읽고, 같은 사안은 가장 늦은 나무의 시각을 쓴다.
    """
    announced_at: dict[tuple[str, str], str] = {}
    for source in reports(vault, index, date + dt.timedelta(days=LOOKBACK)):
        tree = source.with_name("tree.json")
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
    """`이벤트 캘린더` 절의 소제목에 발표일(`data-day`)을 달고 제목에서 날짜를 지운다.

    발표 시각은 제목 앞 `when` 이름표로 단다. `timing`에 그 이벤트가 없으면 소제목의 장 구분을, 그것도 없으면 그날의 장 구분을 쓴다.
    소제목의 중요도 표식은 `data-level`로도 단다.
    리포트 날짜 전 이벤트의 표에는 `judged`를, 실제 갈래 줄에는 `hit`을 달고 그 줄의 전개 예상 뒤에 실제 전개를 붙인다.
    결과를 다룬 이슈가 있으면 실제 갈래 줄에 `data-result`로 단다.
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
                result = f' data-result="{entry["result"]}"' if entry.get("result") else ""
                table = (table[:start] + f'<tr class="hit"{result}>' + table[start + 4:stop] + tail + table[stop:])
        return match.group(0)[:match.start(3) - match.start(0)] + table

    section = re.sub(r'<h3[^>]* data-day="([^"]+)"(?: data-level="[^"]*")?>(?:<span class="when">[^<]*</span>)?(.*?)</h3>\s*(<table class="events">.*?</table>)',
                     judge, section, flags=re.DOTALL)
    return body[:head.end()] + section + body[end:]


@functools.cache
def oil_closes(vault: Path) -> list[tuple[str, float]]:
    """`reference.db`에 쌓인 WTI 종가를 날짜 순으로. 수집기는 같은 날짜의 종가를 받을 때마다 새로 쌓으므로 날짜마다 마지막으로 받은 값을 정산가로 본다."""
    con = sqlite3.connect(f"file:{predictions_chart(vault).path_bands.REFERENCE_DB_PATH}?mode=ro", uri=True)
    try:
        return con.execute(
            "SELECT period, value FROM observation o WHERE series_id = 'close:CL=F' AND value IS NOT NULL AND retrieved_at = "
            "(SELECT MAX(retrieved_at) FROM observation WHERE series_id = o.series_id AND period = o.period) ORDER BY period").fetchall()
    finally:
        con.close()


def settled_oil(vault: Path, as_of: str) -> dict:
    """미국 장 날짜 `as_of`까지의 WTI 정산가로 만든 `market.WTI` 원값. 값·날짜·1년 백분위·지난 1년 일별 정산가를 수집기와 같은 방식으로 적는다."""
    closes = [(day, value) for day, value in oil_closes(vault) if day <= as_of]
    if not closes:
        return {}
    last, price = closes[-1]
    end = dt.date.fromisoformat(last)
    window = [value for day, value in closes if day >= (end - dt.timedelta(days=365)).isoformat()]
    return {"value": round(price, 2), "date": last, "pct_1y": round(sum(value <= price for value in window) / len(window) * 100),
            "daily_close": [[day, round(value, 2)] for day, value in closes if day > end.replace(year=end.year - 1).isoformat()]}


def batch_data(vault: Path, index: str, day: dt.date) -> tuple[dict, dict] | None:
    """그날 지수 폴더의 (`market-data.json`, `macro-data.json`). `market-data.json`이 없으면 None.

    WTI 일별 정산가(`daily_close`)를 적지 않은 배치는 `market.WTI`를 그 배치 미국 장 날짜(`as_of`)까지의 `reference.db` 정산가로 바꾼다.
    수집기는 2026-11-10 배치부터 정산가를 적었고, 그 전 배치의 WTI 값은 거래 중 시세이기 때문이다.
    """
    folder = report_path(vault, day, index).parent
    market = folder / "market-data.json"
    if not market.is_file():
        return None
    macro = folder / "macro-data.json"
    found = json.loads(market.read_text(encoding="utf-8"))
    prices = found.setdefault("market", {})
    if found.get("as_of") and not (prices.get("WTI") or {}).get("daily_close"):
        prices["WTI"] = settled_oil(vault, found["as_of"])
    return found, json.loads(macro.read_text(encoding="utf-8")) if macro.is_file() else {}


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
        "WTI 유가": (oil.get("date"), oil, "daily_close"),
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


def indicator_card(name: str, date: str, value: dict, weeks: list[tuple[str, dict]]) -> dict:
    """지표 하나의 카드 값. `weeks`는 앞 `WEEKS`주 동안 주마다 마지막 (기준일, 원값)이고 마지막 항목이 오늘 값이다.
    반원 속도계는 작은 값을 왼쪽에, 큰 값을 오른쪽에 둔다.
    주별 막대 그림(`columns`)은 가로축이 시간이므로 지난주를 왼쪽에, 오늘을 오른쪽에 둔다. 연준 금리 경로(`diverge`)도 가로축이 시간이므로 가까운 회의를 왼쪽에 두고, 0 가로선 위에 인상을, 아래에 인하를 둔다.
    금리 경로의 세로축 상한(`max`)은 날마다 같은 `RATE_RANGE_BP`이고, 그림은 금리 한 번 변경 폭(`step`)의 위아래 높이에 점선 가로선을 긋는다.
    유가의 일별 선 그림(`daily`)은 원값의 일별 정산가를 앞 날짜부터 오늘까지 왼쪽에서 오른쪽으로 잇는다. 정산가 날짜도 미국 장의 날짜이므로 하루를 더해 적는다.
    `help`는 카드 이름 뒤의 물음표 단추가 띄우는 설명 상자의 문단 목록이고, 지표를 무엇으로 계산하는지와 값을 읽는 법을 쓴다."""
    when = month_day(date)
    if name == "공포·탐욕 지수":
        score = value["score"]
        guide = ["CNN이 미국 주식시장의 투자 심리를 0점에서 100점 사이로 매긴 점수예요. CNN은 지표 7개를 합쳐 점수를 계산해요: S&P500의 추세, "
                 "52주 신고가와 신저가 종목 수, 상승 종목과 하락 종목의 거래량, 풋옵션과 콜옵션의 거래 비율, VIX, 주식과 국채의 수익률 차이, 정크본드 수요.",
                 "점수가 25 이하면 극단 공포, 45 이하면 공포, 55 이하면 중립, 75 이하면 탐욕, 그보다 크면 극단 탐욕이에요. "
                 "점수가 낮을수록 투자자는 주식을 팔고 국채 같은 안전자산을 더 많이 사요. 시장에서는 극단 공포를 매도가 지나쳤다는 신호로 보기도 해요."]
        return {"tab": "공포·탐욕", "help": guide, "asof": f"CNN · {when}", "value": f"{score:g}", "state": zone(FEAR_GREED_ZONES, score),
                "figure": {"type": "semi", "min": 0, "max": 100, "zones": FEAR_GREED_ZONES, "value": score, "ends": ["공포", "탐욕"]}}
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
                 "카드의 값은 CME가 발표한 그날의 정산가이고, 그림은 지난 1년 동안 날마다의 정산가를 이어 그려요.",
                 "유가가 오르면 기업의 연료비와 운송비가 늘고 소비자 물가도 올라요. 물가가 오르면 연준이 기준금리를 내리기 어려워져 주가에 부정적이에요. "
                 "상태의 1년 상위 %는 지난 1년 가운데 오늘보다 유가가 높았던 날의 비율이에요."]
        points = [[(dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat(), price, f"${price:.2f}"]
                  for day, price in value["daily_close"]]
        return {"tab": "유가", "help": guide, "asof": f"WTI 정산가 · {when}", "value": f"{level:.2f}", "unit": "달러",
                "state": year_rank(value["pct_1y"]),
                "figure": {"type": "daily", "points": points}}
    meetings = value["meetings"][:3]
    first = meetings[0]
    month = f"{int(first['meeting'][5:7])}월"
    move = first["cumulative_bp"]
    state = ([f"{month} 인상 예상", DOWN] if move >= RATE_MOVE_BP else [f"{month} 인하 예상", UP] if move <= -RATE_MOVE_BP
             else [f"{month} 동결 예상", NEUTRAL])
    rows = [[f"{int(item['meeting'][5:7])}월", item["cumulative_bp"], f"{signed(item['cumulative_bp'] / 100, 2)}%p"]
            for item in meetings]
    guide = ["연방기금 금리 선물은 미국 기준금리의 한 달 평균에 거는 계약이에요. 선물 가격에서 시장이 예상하는 기준금리를 계산해요. "
             "카드는 앞으로 열리는 연준 회의 세 번마다 기준금리의 누적 변화를 %p로 보여 줘요. 누적 변화는 지금 기준금리와 그 회의 뒤 예상 기준금리의 차이예요.",
             "값이 +0.25%p면 시장은 그 회의까지 0.25%p 인상 한 번을 예상해요. "
             f"다음 회의까지 누적 변화가 +{RATE_MOVE_BP / 100:g}%p 이상이면 인상 예상, −{RATE_MOVE_BP / 100:g}%p 이하면 인하 예상, 그 사이면 동결 예상이에요. "
             "기준금리가 오르면 기업의 차입 비용이 커져요. 그래서 인상 예상은 주가에 부정적이에요."]
    return {"tab": "금리 경로", "help": guide, "asof": f"연방기금 선물 · {when}", "value": signed(move / 100, 2), "unit": "%p", "state": state,
            "figure": {"type": "diverge", "rows": rows, "max": RATE_RANGE_BP, "step": RATE_STEP_BP}}


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
        cards[name] = indicator_card(name, day, value, list(weekly.values())[-WEEKS:])
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



def mark_issue_ids(body: str, bundles: Path, events: dict[int, list[tuple[str, str | None]]]) -> str:
    """`상세 이슈 해설` 절의 번호 붙은 이슈 소제목에 `system/issues.json`의 그 번호 `id`를 `data-issue`로 단다.
    `events`에 그 번호가 있으면 결과를 다룬 이벤트 이름을 `data-event`로 함께 달고, 그 이벤트가 모두 중요도 낮음이면 `data-event-level="low"`도 단다."""
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
        found = events.get(int(number.group(1)), [])
        event = f' data-event="{html.escape(" · ".join(name for name, _ in found))}"' if found else ""
        if found and all(level == "low" for _, level in found):
            event += ' data-event-level="low"'
        return f'<h3{match.group(1)} data-issue="{html.escape(issue)}"{event}>{match.group(2)}</h3>'

    section = re.sub(r"<h3([^>]*)>(.*?)</h3>", heading, body[head.end():end], flags=re.DOTALL)
    return body[:head.end()] + section + body[end:]


def mark_issue_images(body: str, assets: Path, plan: Path, target: Path, out: Path) -> str:
    """`상세 이슈 해설` 절의 번호 붙은 이슈 소제목 뒤에 `assets/issue-{번호}-{순번}.webp` 그림 묶음과 첫 그림의 썸네일 주소, `system/issue-images.json`의 그림별 사진 설명을 넣는다. 그림이 없는 이슈는 그대로 둔다."""
    head = re.search(rf'<h2 id="[^"]*">{ISSUES_TITLE}</h2>', body)
    if not head:
        return body
    plans = {str(issue["issue"]): issue["images"] for issue in json.loads(plan.read_text(encoding="utf-8"))["issues"]} if plan.is_file() else {}
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end

    def heading(match: re.Match) -> str:
        number = re.match(r"(\d+)\.\s", html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip())
        if not number:
            return match.group(0)
        photos, thumb = [], None
        for k, image in enumerate(plans.get(number.group(1), [{}]), 1):
            source = assets / f"issue-{number.group(1)}-{k}.webp"
            if not source.is_file():
                continue
            shutil.copy2(source, target / source.name)
            with Image.open(source) as picture:
                width, height = picture.size
                if thumb is None:
                    thumb = target / f"issue-{number.group(1)}-thumb.webp"
                    side = min(picture.size)
                    # 가로 그림은 가운데를, 세로 그림은 얼굴이 드는 위쪽을 남기도록 남는 높이의 4분의 1 지점부터 자른다.
                    box = ((width - side) // 2, (height - side) // 4)
                    picture.convert("RGB").crop((*box, box[0] + side, box[1] + side)).resize((THUMB, THUMB), Image.Resampling.LANCZOS).save(thumb, format="WEBP", quality=80)
            caption = image.get("caption", "").strip()
            note = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
            photos.append(f'<figure class="photo"><div class="frame"><img src="{versioned(target / source.name, out)}" width="{width}" height="{height}" alt="">'
                         f'<span class="ai">AI 생성 이미지</span></div>{note}</figure>')
        if not photos:
            return match.group(0)
        return f'{match.group(0)}\n<figure class="issue-image" data-thumb="{versioned(thumb, out)}">{"".join(photos)}</figure>'

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


def linked_nodes(source: Path, item: str) -> set[str]:
    """`source` 리포트에서 사안 `item`과 같은 사안으로 보는 노드. 그 리포트 `system/issues.json`에서 `item`을 노드로 묶은 이슈의 노드를 더하고, 트리거 노드는 뺀다."""
    linked = source.parent / "system" / "issues.json"
    earlier = json.loads(linked.read_text(encoding="utf-8"))["issues"] if linked.is_file() else []
    same = {item}.union(*(bundle["nodes"] for bundle in earlier if item in bundle["nodes"]))
    return {node for node in same if not node.startswith("trigger:")}


def result_issue(vault: Path, index: str, source: Path, name: str, day: dt.date, date: dt.date) -> str | None:
    """`source` 리포트가 적은 이벤트의 결과를 다룬 이슈를 `리포트 키/이슈 번호`로. 발표일 뒤 리포트 날짜까지의 첫 리포트에서,
    그 리포트 바로 앞 리포트가 이벤트의 사안과 같은 사안으로 보는 노드를 `id`나 노드로 가진 이슈다. 그런 리포트나 이슈가 없으면 None이다."""
    item = tree_issues(source).get(name, {}).get("item")
    after = [path for path in reports(vault, index, date) if path.parent.parent.name > f"{day}"]
    if not item or not after:
        return None
    target = after[-1]
    bundles = target.parent / "system" / "issues.json"
    previous = reports(vault, index, dt.date.fromisoformat(target.parent.parent.name) - dt.timedelta(days=1))
    if not bundles.is_file() or not previous:
        return None
    same = linked_nodes(previous[0], item)
    for bundle in json.loads(bundles.read_text(encoding="utf-8"))["issues"]:
        if same & {bundle["id"], *bundle["nodes"]}:
            return f"{target.parent.parent.name.replace('-', '')}-{index}/{bundle['issue']}"
    return None


def issue_events(vault: Path, index: str, day: dt.date) -> dict[int, list[tuple[str, str | None]]]:
    """오늘 이슈 번호마다, 바로 앞 리포트가 적은 이벤트 가운데 두 리포트 사이에 발표되어 그 이슈가 결과를 다룬 이벤트의 이름과 `data-level` 값."""
    bundles = report_path(vault, day, index).parent / "system" / "issues.json"
    previous = reports(vault, index, day - dt.timedelta(days=1))
    if not bundles.is_file() or not previous:
        return {}
    source = previous[0]
    since = dt.date.fromisoformat(source.parent.parent.name)
    items = tree_issues(source)
    found: dict[int, list[tuple[str, str | None]]] = {}
    for when, name, chunk in event_items(source.read_text(encoding="utf-8"), since):
        item = items.get(name, {}).get("item")
        if not item or not since <= when < day:
            continue
        tag = LEVEL_RE.search(chunk.partition("\n")[0])
        level = LEVELS.get(tag.group(1)) if tag else None
        same = linked_nodes(source, item)
        for bundle in json.loads(bundles.read_text(encoding="utf-8"))["issues"]:
            if same & {bundle["id"], *bundle["nodes"]}:
                found.setdefault(bundle["issue"], []).append((name, level))
    return found


def issue_history(vault: Path, index: str, day: dt.date, out: Path) -> dict[str, list[tuple[dt.date, int, str]]]:
    """오늘 이슈 `id`마다, 그 `id`를 노드로 묶은 앞 날짜 이슈의 날짜와 이슈 번호와 공개본 이슈 조각을 날짜 순으로."""
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
                    history[issue].append((past, bundle["issue"], segments[bundle["id"]]))
    return history


def mark_issue_history(body: str, history: dict[str, list[tuple[dt.date, int, str]]], day: dt.date) -> str:
    """번호 붙은 이슈 뒤에 앞 날짜 이슈 조각과 날짜마다 이슈 해설 소제목을 담은 `issue-history` 템플릿을 넣는다."""
    parts, last = [], 0
    for start, stop in issue_segments(body):
        segment = body[start:stop]
        issue = re.match(r'<h3[^>]*data-issue="([^"]*)"', segment)
        past = history.get(html.unescape(issue.group(1)), []) if issue else []
        if not past:
            continue
        days = [(when, explainer_title(chunk), re.sub(r'\sid="[^"]*"', "", chunk)) for when, _, chunk in past]
        days.append((day, explainer_title(segment), ""))
        sections = "".join(f'<section data-day="{when}" data-title="{html.escape(title)}">{chunk}</section>'
                           for when, title, chunk in days)
        parts += [body[last:stop].rstrip(), f'\n<template class="issue-history">{sections}</template>\n']
        last = stop
    return "".join(parts) + body[last:]


def link_later(entries: dict, key: str, history: dict[str, list[tuple[dt.date, int, str]]], bundles: Path) -> None:
    """`key` 리포트 이슈의 히스토리에 든 앞 날짜 이슈마다, 그 리포트 목록 항목의 `later`에 이슈 번호를 키로 `key/이슈 번호`를 적는다.
    이미 더 늦은 리포트를 적은 번호는 그대로 둔다."""
    if not bundles.is_file():
        return
    index = key.split("-")[1]
    numbers = {bundle["id"]: bundle["issue"] for bundle in json.loads(bundles.read_text(encoding="utf-8"))["issues"]}
    for issue, past in history.items():
        for when, number, _ in past:
            earlier = entries.get(f"{when:%Y%m%d}-{index}")
            if earlier is None or issue not in numbers:
                continue
            later = earlier.setdefault("later", {})
            if later.get(str(number), "")[:8] <= key[:8]:
                later[str(number)] = f"{key}/{numbers[issue]}"


def build(date: str, index: str, vault: Path, out: Path) -> str:
    source = vault / f"routine/invest/{date[:7]}/{date}/{index}/report.md"
    if not source.is_file():
        raise SystemExit(f"리포트가 없다: {source}")
    key = f"{date.replace('-', '')}-{index}"
    target = out / "r" / key
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    text = source.read_text(encoding="utf-8")
    card = summary_cards(index, date, source.parent, vault)
    if card:
        text = re.sub(rf"^!\[\[[^\]]*/(?:chart|tree|predict)-{index}\.png\]\]\s*\n", "", text, flags=re.MULTILINE)
    text = mark_terms(text, source.parent / "system" / "terms.json", vault)
    markdown = public_markdown(text, vault, target, f"r/{key}")
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
    # 10/21까지의 `display.json`은 `next`에 이슈 이름만 적어 갈래 값이 없으므로, 갈래를 적은 항목만 갈래 변화 표시에 쓴다.
    upcoming = [issue for issue in json.loads(display.read_text(encoding="utf-8"))["next"] if isinstance(issue, dict)] if display.is_file() else []
    body = mark_days(body, day, branches, timings(vault, index, day), upcoming)
    body = mark_indicators(body, indicator_cards(vault, index, day))
    body = mark_issue_ids(body, source.parent / "system" / "issues.json", issue_events(vault, index, day))
    body = mark_issue_images(body, source.parent / "assets", source.parent / "system" / "issue-images.json", target, out)
    body = mark_issue_charts(body, source.parent / "system" / "issue-charts.json")
    history = issue_history(vault, index, day, out)
    body = mark_issue_history(body, history, day)
    if card:
        data = json.dumps(card, ensure_ascii=False).replace("</", "<\\/")
        body += f'<script type="application/json" id="cards">{data}</script>\n'
    (target / "report.html").write_text(body, encoding="utf-8")

    listing = out / "r" / "index.json"
    entries = json.loads(listing.read_text(encoding="utf-8")) if listing.exists() else {}
    heading = TITLE_RE.match(html.unescape(title))
    if not heading:
        raise SystemExit(f"제목 끝에 날짜가 없다: {title}")
    written = entries.get(key, {}).get("written") or dt.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
    later = entries.get(key, {}).get("later")
    entries[key] = {"title": heading.group(1), "day": heading.group(2), "written": written, "date": date, "index": index}
    if later:
        entries[key]["later"] = later
    if (move := moves(vault, index, date)):
        entries[key]["moves"] = move
    link_later(entries, key, history, source.parent / "system" / "issues.json")
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
