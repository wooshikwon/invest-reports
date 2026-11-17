#!/usr/bin/env python3
"""build — 판단 리포트 공개본을 `invest-reports` `invest-reports` 미니 앱(`app.html`)이 읽는 HTML 조각으로 만든다. `run-with-notify.sh`의 `publish_miniapp`이 만든 조각을 게시한다.

사용법: python3 build.py --date 2026-10-19 --index nasdaq [--vault ~/obsidian-vault] [--out .] [--stage pre|running]

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
이벤트 소제목마다 발표가 주가에 닿는 뉴욕 정규장 거래일(`scenario_tree.reaction_session`)을 `data-day`로, 뉴욕 발표일을 `data-announced`로 달고
제목에서는 날짜를 지운다. `invest-reports` 미니 앱은 `data-day`로 날짜 띠를 그리고 같은 거래일 이벤트를 한 장에 모은다.
일정과 예측 카드도 같은 거래일에 일정을 두므로, 두 그림의 날짜가 같다. 제목 위에는 사안 나무의 발표 시각(`announced`)을 한국 시각(KST)으로 적는다.
발표 시각이 수집기가 채운 기본값(`PLACEHOLDER_TIMES`)이거나 사안 나무에 없으면 장전·장중·장후만 적고,
뉴욕 발표일이 거래일과 다르면 그 앞에 `12/09(수) 장후`처럼 발표일을 붙인다.
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
`invest-reports` 미니 앱은 그 이슈 상자에 외곽선을 두르고 외곽선 위쪽 왼쪽에 "10월 CPI 결과"처럼 이벤트 이름표를 단다.
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

`r/index.json`에는 리포트마다 제목, 날짜 줄(`day`), 본 리포트를 처음 만든 시각(`written`, 서울 시각)을 적는다.
앞 날짜 리포트의 이슈가 뒤 리포트 이슈의 히스토리에 들면, 앞 날짜 리포트 항목의 `later`에 그 이슈 번호를 키로 히스토리를 가진
가장 늦은 리포트의 `리포트 키/이슈 번호`를 적는다. 미니 앱의 "자세히 보기" 단추는 이 값으로 이슈의 가장 늦은 히스토리를 연다. `invest-reports` 미니 앱은 제목 위
작은 글씨로 날짜 줄을 그린다. 같은 리포트를 다시 만들어도 처음 만든 시각은 그대로 둔다.
`invest-reports` 미니 앱의 달력은 같은 목록에서 그 지수의 리포트 날짜를 찾아 흰 글자로 쓰고, 날짜 아래에 `moves`의 `session`을 적는다.
달력 위 `나스닥 | 바이오` 단추로 지수를 바꾸면 달력은 그 지수의 리포트 날짜로 다시 그려지고, 날짜를 누르면 그 날짜의 그 지수 리포트가 열린다.
`moves`에는 리포트 날짜 전날 정규장 종가의 앞 세션 종가 대비 등락률(`session`, %)과 기준 가격의 기준 가격 날짜 종가 대비
등락률(`after`, %), 기준 가격 날짜의 환산 종가(`close`, 달러)와 기준 가격(`base`, 달러)을 적는다. 전날이 휴장일이면 `session`은 `null`이다.
두 등락률과 두 가격은 `path-bands.json`의 ^NDX·^NBI 환산 가격과 `reference.db` 환산 종가로 재므로 12M + Predictions 그림의 종가 선, 기준 가격과 같은 눈금이다.

`r/market.json`의 `map`에는 지수마다 비중 상위 20종목(나스닥 100, 나스닥 바이오테크놀로지)의 한글 이름, 주식 수, 날짜별 종가를 적는다(`market`, `index_map`).
날짜별 애프터장 마지막 체결가도 적는다. 마지막 날짜의 값은 그날 애프터장이 끝난 뒤(20:00 ET) 받고, 앞 날짜의 값은 앞서 쓴 `r/market.json`에서 옮긴다(`after_prices`).
`invest-reports` 미니 앱의 시장 페이지는 리포트 지수의 값으로 맨 위 `나스닥 한 눈에 보기`·`바이오 한 눈에 보기` 절에 시가총액을 칸 넓이로, 전 거래일 대비 등락률을 칸 색으로 쓴 지도를 그리고,
슬라이더로 지난 한 달의 리포트 날짜를 고르면 그 날짜 전날의 종가로 지도를 다시 그린다. 그 날짜 전날의 애프터장 값이 있으면 절 제목 오른쪽의
`정규장 | 애프터장` 단추로 칸 값과 색을 애프터장 체결가와 정규장 종가 대비 등락률로 바꾼다.
`r/premarket.json`에는 지수마다 서울 날짜와 같은 뉴욕 날짜를 키로 그날 프리장의 마지막 체결가를 적는다(`premarket`). 값은 지수 ETF의
정규장 종가 대비 비율(`ratio`), 지도 종목마다의 체결가(`stocks`), 값을 받은 시각(`time`)과 앞 세션 날짜(`session`)다. cron이 프리장 동안 10분마다
부르고, 프리장이 닫힌 뒤에는 마지막 값을 그대로 둔다. 미니 앱은 그 날짜 리포트의 머리 상자 아래 줄을 프리마켓 값으로 바꾸고,
지도의 단추를 `정규장 | 다음날 프리장`으로 바꿔 애프터장 값 자리에 프리장 체결가와 정규장 종가 대비 등락률을 쓴다.
요약 절의 주가와 예측 카드와 종목 상세 페이지의 주가 카드도 같은 값으로 위 줄 오른쪽에 `정규장 | 애프터장`이나 `정규장 | 프리장` 단추를 두고,
정규장 다음 단추를 고르면 값과 등락률을 회색으로 쓰고 그림에 그 체결가를 점선으로 잇는다. 지도와 두 카드는 처음에 가장 늦은 세션을 고른다.
지도 칸을 누르면 칸 위 말풍선에 종목 이름, 종가와 등락률, 설명 첫 문장을 적고, 말풍선의 `자세히 보기` 단추는 `?stock=심볼` 종목 상세 페이지를 연다.
종목 상세 페이지는 지도에서 고른 세션(`session`)을 받아 같은 세션으로 연다.
`r/stocks/{심볼}.json`에는 종목 상세 페이지의 값으로 한글 이름, 업종, 설명, 지도 지수와 그 지수 안 시가총액 순위, 1년 종가, 공시 카드 세 장(실적·매출 구성·최근 공시),
대표 이미지 한~세 장의 주소와 사진 설명을 적는다(`stock_pages`). 대표 이미지는 `STOCK_IMAGES`의 `{심볼}-{순번}.webp`를 `r/stocks/`로 복사한다.
종목 상세 페이지는 맨 위에 대표 이미지를 싣고, 이슈 상세 페이지의 틀로 주가 카드와 기업 설명을 그리고, `공시 상세` 절에 공시 카드를 탭 세 개로 그린다.

`system/simulation.json`의 `quantiles`에 5% 값이 있는 리포트는 요약 절 세 그림을 그림 파일 대신 값으로 그린다.
그런 리포트의 공개본에서는 12M + Predictions·Montecarlo·권장 추종 배율 그림을 빼고, `report.html` 끝에 카드 값을
`<script type="application/json" id="cards">`로 붙인다. 카드 값은 `PRICE_YEARS`년 종가와 날짜, 지난 리포트가 예측한 25거래일 뒤 가격,
그날 25·50·75% 가격, 10~90% 수익률 분위수와 사안 일정, 체류 적분 밀도를 담는다(`summary_cards`). 종가와 가격은 예측을 계산한
ETF 눈금을 지수 눈금으로 늘려 적는다(`card_scale`). 공개본이 있는 그 지수 리포트
가운데 가장 늦은 날짜에서 `REWIND_DAYS`일 안의 카드 값 리포트는 되감기 날짜가 되고, `r/rewind-{지수}/cards.json`에 날짜마다
같은 판단 값과 그날 기준 가격 뒤의 실제 종가 수익률(%)을 쓴다. `invest-reports` 미니 앱은 카드 값으로 그림 카드를
그리고, 슬라이더를 옮기면 그날 판단 값으로 세 카드를 다시 그린다.

`--stage pre`는 판단 배치가 돌기 전에 그날 리포트 키로 사전 리포트를 만든다. 사전 리포트는 그 지수의 가장 늦은 본 리포트 공개본에서
`1개월 지수 방향 예측` 절의 본문과 카드 값을 빼고, 이슈 소제목의 `data-new`를 지우고 `data-age`를 그날 기준으로 다시 단다.
`미국 거시 지표` 카드 값은 그 시각까지 `reference.db`에 적재한 값으로 판단 배치와 같은 `render_inputs.py` 함수가 만든 입력에서 다시 뽑고,
지표 소제목 뒤의 해설은 지운다.
카드 값은 `pre`를 참으로 두고 전날까지 `PRICE_YEARS`년 종가와 앞 리포트들이 예측한 25거래일 뒤 가격(`past_cards`)을 담는다.
`invest-reports` 미니 앱은 주가 카드 한 장만 종가 선과 지난 예측 범위로 그리고, 그날 종가의 등락률을 등락 색으로 적는다.
되감기 슬라이더는 앞 날짜의 판단과 사전 리포트의 종가를 고르게 하고, 일정·권장 배율 카드와 머리 상자의 애프터마켓 줄은 두지 않는다. 이벤트 캘린더와 이슈 그림은 앞 리포트의 것을 그대로 쓴다.
`r/index.json` 항목에는 `stage: "pre"`와 전날 정규장 `session`·`close`만 적은 `moves`를 쓰고, 앞 날짜의 사전 리포트 항목과 폴더는 지운다.
전날이 뉴욕 정규장 세션이 아니면 종료 코드 3, 그날 본 리포트가 이미 있으면 종료 코드 4로 끝내고 아무것도 쓰지 않는다. 전날 세션의 종가가 `reference.db`에 아직 없으면 실패로 끝낸다.
`--stage running`은 그날 사전 리포트 항목의 `stage`를 `running`으로 바꾸고, 판단 배치가 애프터장이 끝난 뒤 시작하므로 `r/market.json`을 다시 써서 전날 애프터장 값을 단다. 본 리포트를 만들면 같은 키의 항목을 새로 쓰므로 `stage`가 없어지고,
`invest-reports` 미니 앱은 `stage`가 없는 항목을 분석 완료로 그리고, 그 옆에 `written`의 시각을 적는다.
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

import exchange_calendars
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
# 사안 나무에 발표 시각이 없는 이벤트를 소제목의 장 구분으로 거래일에 둘 때 쓰는 뉴욕 시각. `PLACEHOLDER_TIMES`의 장 구분 시각이다.
PHASE_TIMES = {"장전": "08:00", "장중": "12:00", "장후": "16:00"}
REGULAR_OPEN, REGULAR_CLOSE = "09:30", "16:00"  # 뉴욕 정규장 시각. 발표 시각을 장전·장중·장후로 나눈다
# 발표 시각을 모를 때 채우는 뉴욕 시각. 실적의 장전(bmo)·장후(amc) 단서는 `calendar_store.py`가 08:00·16:05로,
# 장중(dmh)은 `render_inputs.py`가 12:00으로 채우고, 단서가 없는 발표는 16:00으로 적는다. 이 시각은 장 구분만 적는다.
PLACEHOLDER_TIMES = {"08:00", "12:00", "16:00", "16:05"}
NEW_YORK, SEOUL = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")
# 리포트 제목 끝의 날짜 줄. `나스닥 리포트 2026-10-22 (목)` 꼴이다.
TITLE_RE = re.compile(r"^(.*\S)\s+(\d{4}-\d{2}-\d{2} \([^)]*\))$")
REWIND_DAYS = 30  # 되감기 슬라이더가 거슬러 가는 날짜 범위
CARD_QUANTILES = (10, 25, 50, 75, 90)  # 일정과 예측 카드가 그리는 수익률 분위수
PRICE_YEARS = 3  # 주가와 예측 카드가 그리는 종가 기간(년)
# 시장 페이지의 지수 지도가 되감기 날짜의 첫날보다 앞서 종가를 받는 날 수다. 첫날의 앞 두 세션이 들도록 일주일을 더 받는다.
MAP_LEAD_DAYS = 7
STOCK_DAYS = 366  # 종목 상세 페이지의 주가 카드가 그리는 종가 기간(일)
AFTER_CLOSE = dt.time(20)  # 뉴욕 애프터장이 끝나는 시각. 지도의 애프터장 값은 이 시각까지의 마지막 체결가다
PREMARKET_OPEN, PREMARKET_CLOSE = dt.time(4), dt.time(9, 30)  # 뉴욕 프리장이 열리고 닫히는 시각. 지도와 머리 상자의 프리장 값은 닫히는 시각까지의 마지막 체결가다
STOCK_IMAGES = Path.home() / "data" / "invest-reports" / "stock-images"  # invest-stock-profile 스킬이 고르고 `profile_store.py --draw`가 그린 대표 이미지
TICK_STEP = 5  # 일정과 예측 카드 가로축 날짜의 거래일 간격
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


def scenario_tree(vault: Path):
    sys.path.insert(0, str(vault / "agent/skills/tool/invest-report/scripts"))
    import scenario_tree as module
    return module


def render_inputs(vault: Path):
    sys.path.insert(0, str(vault / "agent/skills/tool/invest-report/scripts"))
    import render_inputs as module
    return module


def versioned(path: Path, out: Path) -> str:
    return f"{path.relative_to(out).as_posix()}?v={hashlib.sha256(path.read_bytes()).hexdigest()[:10]}"


def actual_returns(db: Path, ticker: str, days: list[str], base: float, scale: float, until: str) -> list[float]:
    """기준 가격 날짜 뒤 `until`까지의 거래일마다 기준 가격 대비 종가 수익률(%). 첫 값은 출발점 0이고 종가가 있는 날까지 잇는다.

    `base`는 `scale`을 곱한 눈금의 기준 가격이고, 종가에도 `scale`을 곱해 같은 눈금에서 나눈다.

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
        values.append(round((closes[day] * scale / base - 1) * 100, 3))
    return values


def card_scale(index: str, vault: Path) -> float:
    """주가와 예측 카드가 ETF 환산 종가에 곱해 지수 눈금으로 늘리는 배율. 마지막으로 겹치는 날의 `observation` 지수 종가 ÷ `market_price` 환산 종가다.

    `market_price`의 QQQ·IBB 행은 지수 수익률을 ETF 눈금으로 환산한 값이라, 이 배율은 날짜와 관계없이 일정하다.
    """
    bands = predictions_chart(vault).path_bands
    con = sqlite3.connect(f"file:{bands.REFERENCE_DB_PATH}?mode=ro", uri=True)
    try:
        return con.execute(
            "SELECT o.value / p.close FROM observation o JOIN market_price p ON p.price_date = o.period "
            "WHERE p.ticker = ? AND o.series_id = ? AND o.value IS NOT NULL ORDER BY o.period DESC, o.retrieved_at DESC LIMIT 1",
            (bands.SECTOR_DB_TICKERS[index], f"close:{bands.SECTOR_INDEX_TICKERS[index]}")).fetchone()[0]
    finally:
        con.close()


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


def card_frame(date: str, folder: Path, scale: float) -> dict | None:
    """그날 판단의 그림 카드 값. `system/simulation.json`의 `quantiles`에 5% 값이 없는 리포트는 `None`이다.

    `base`는 기준 가격에 `scale`(`card_scale`)을 곱한 값이다.
    `days`는 기준 가격 날짜에서 시작하는 거래일, `predict`는 그 거래일마다 25·50·75% 가격, `tree`는 수익률 분위수(%)와 발표일이 같은 사안의 묶음·가로축 날짜,
    `chart`는 체류 적분 밀도다. 가로축의 첫 날짜는 기준 가격 날짜가 아니라 리포트 날짜로 적는다.
    """
    path = folder / "system" / "simulation.json"
    simulation = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    quantiles = simulation.get("quantiles") or {}
    if "q5" not in quantiles:
        return None
    base = float(json.loads((folder / "path-bands.json").read_text(encoding="utf-8"))["price_base"]) * scale
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


def past_cards(index: str, date: str, dates: list[str], reach: int, scale: float, vault: Path, skip: str | None = None) -> list[list[float]]:
    """리포트 날짜 `date` 앞 리포트들이 예측한 25거래일 뒤 가격을 `[가로 위치, 25·50·75% 가격]` 줄로 가로 위치 순서에 둔다.

    가로 위치는 종가 날짜 `dates`의 번호로 센다. 줄은 12M + Predictions 그림과 같은 줄을 고르고, 가격에는 `card_scale`의 `scale`을 곱한다.
    기준 가격 날짜가 `dates`에 없거나 `skip`인 줄과 가로 위치가 `reach`보다 오른쪽인 줄은 뺀다.
    """
    chart = predictions_chart(vault)
    past = {}
    for base_date, (base, ahead, values) in chart.past_judgments(
            chart.read_ledger(chart.LEDGER_DIR / f"predictions-{index}.jsonl"), date).items():
        if base_date in dates and base_date != skip and dates.index(base_date) + ahead <= reach:
            past[dates.index(base_date) + ahead] = [round(base * scale * (1 + v), 2) for v in values]
    return [[x, *values] for x, values in sorted(past.items())]


def summary_cards(index: str, date: str, folder: Path, vault: Path) -> dict | None:
    """요약 절 그림 카드 값. `card_frame`이 `None`인 리포트는 `None`이다.

    카드 값은 그날 판단(`card_frame`)에 기준 가격 날짜까지 `PRICE_YEARS`년 종가와 날짜, 기준 가격의 가로 거리,
    지난 리포트가 예측한 25거래일 뒤 가격(`past`, `past_cards`)을 더한다. 종가에는 `card_scale`을 곱한다. 지난 예측에서는 오늘 판단과 같은
    기준 가격 날짜의 줄과 오늘 판단의 끝보다 오른쪽 줄을 뺀다.
    """
    scale = card_scale(index, vault)
    frame = card_frame(date, folder, scale)
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
    past = past_cards(index, date, dates, len(dates) - 1 + len(frame["predict"]["q50"]) - 1, scale, vault, frame["base_date"])
    return {"start_offset": chart.START_OFFSET, "dates": dates, "history": [round(c * scale, 2) for _, c in history], "past": past, **frame}


def rewind(index: str, vault: Path, out: Path) -> Path | None:
    """`r/rewind-{지수}/`에 되감기 날짜마다 요약 절 카드 값(`cards.json`)과 지표 카드 값(`indicators.json`)을 쓴다.

    한쪽 값이 하나도 없으면 그 파일을 지우고, 두 파일이 모두 없으면 폴더를 지운다.
    """
    target = out / "r" / f"rewind-{index}"
    published = sorted(dt.date.fromisoformat(f"{p.name[:4]}-{p.name[4:6]}-{p.name[6:8]}")
                       for p in (out / "r").glob(f"*-{index}") if p.name[:8].isdigit())
    days = [day for day in published if published[-1] - day < dt.timedelta(days=REWIND_DAYS)]
    scale = card_scale(index, vault)
    frames = [frame for day in days
              if (frame := card_frame(day.isoformat(), vault / f"routine/invest/{day:%Y-%m}/{day}/{index}", scale))]
    if frames:
        chart = predictions_chart(vault)
        until = frames[-1]["base_date"]
        for frame in frames:
            frame["tree"]["actual"] = actual_returns(chart.path_bands.REFERENCE_DB_PATH, chart.path_bands.SECTOR_DB_TICKERS[index],
                                                     frame["days"], frame["base"], scale, until)
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


def observed(con: sqlite3.Connection, series_id: str, column: str, since: str = "") -> dict:
    """`reference.db` 계열의 기간 → 가장 늦게 받은 값. `since`보다 앞 기간은 뺀다."""
    return dict(con.execute(
        f"SELECT period, {column} FROM observation o WHERE series_id = ? AND {column} IS NOT NULL AND period >= ? AND retrieved_at = "
        "(SELECT MAX(retrieved_at) FROM observation WHERE series_id = o.series_id AND period = o.period)",
        (series_id, since)).fetchall())


def index_map(con: sqlite3.Connection, cm, index: str, start: str) -> dict:
    """`index` 지수 지도의 날짜와 종목마다 심볼, 한글 이름, 업종, 설명, 주식 수, 날짜별 정규장 종가.

    종목은 그 지수의 이익 추정 종목(`collect_market.eps_symbols`)이고, 같은 회사의 두 종류주는 GOOGL 하나로 센다. 이름은 토스 한글 종목명에서
    종류주 글자와 `(ADR)`을 뗀다. 주식 수는 마지막 이익 추정 스냅샷의 시가총액 ÷ 주가이고, GOOGL의 시가총액은 두 종류주를 합친 회사 전체다.
    종가는 야후 원 종가이고, 야후에 없는 날은 토스 종가로 메운다. 날짜는 `start`부터 어느 종목이든 종가가 있는 날이고, 그 종목의 종가가 없는 날은 null이다.
    업종과 설명은 invest-stock-profile 스킬이 쓴 `stock_profile` 표에서 읽고, 설명이 아직 없는 종목은 두 값을 빈 글자로 둔다.
    이름이나 주식 수가 없는 종목은 뺀다.
    """
    roster = cm.anchor_store.connect()
    try:
        symbols = cm.eps_symbols(roster, index)
    finally:
        roster.close()
    profiles = {}
    if con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'stock_profile'").fetchone():
        profiles = {symbol: (sector, about) for symbol, sector, about in con.execute("SELECT symbol, sector, about FROM stock_profile")}
    names = {symbol: re.sub(r"\s*\(ADR\)$| [A-Z]$", "", name) for symbol, name in observed(con, cm.TOSS_NAMES, "value_text").items()}
    stocks = []
    for symbol in symbols:
        snapshot = {key: value for key, value in observed(con, cm.eps_id(symbol), "value").items() if key in ("marketCap", "price")}
        if symbol not in names or len(snapshot) < 2:
            continue
        closes = {**observed(con, cm.toss_id(symbol), "value", start), **observed(con, cm.breadth_id(symbol), "value", start)}
        sector, about = profiles.get(symbol, ("", ""))
        stocks.append({"symbol": symbol, "name": names[symbol], "sector": sector, "about": about,
                       "shares": round(snapshot["marketCap"] / snapshot["price"]), "closes": closes})
    dates = sorted({day for stock in stocks for day in stock["closes"]})
    for stock in stocks:
        stock["closes"] = [round(stock["closes"][day], 2) if day in stock["closes"] else None for day in dates]
    return {"dates": dates, "stocks": stocks}


def after_prices(board: dict, previous: dict, price_source) -> None:
    """지도(`board`)의 종목마다 날짜별 애프터장 마지막 체결가 `after`를 `closes`와 같은 순서로 단다.

    날짜별 값은 앞서 쓴 `r/market.json`의 지도(`previous`)에서 옮기고, 적힌 값이 없는 날짜는 null이다. 지도의 마지막 날짜에 적힌 값이 없고
    그날 애프터장이 끝났으면(`AFTER_CLOSE`) 그 시각까지의 마지막 체결가를 토스 1분봉에서, 답하지 않으면 야후 1분봉에서 받는다
    (`price_source.batch_time_price`). 애프터장 체결이 없거나 두 출처가 모두 답하지 않은 종목은 null로 두고 다음 빌드에서 다시 받는다.
    """
    kept = {stock["symbol"]: dict(zip(found["dates"], stock.get("after", [])))
            for found in previous.values() for stock in found["stocks"]}
    for found in board.values():
        last = found["dates"][-1]
        end = dt.datetime.combine(dt.date.fromisoformat(last), AFTER_CLOSE, NEW_YORK)
        for stock in found["stocks"]:
            own = kept.setdefault(stock["symbol"], {})
            if own.get(last) is None and dt.datetime.now(NEW_YORK) >= end:
                try:
                    own[last] = round(price_source.batch_time_price(stock["symbol"], last, end.isoformat())["price"], 2)
                except RuntimeError as error:
                    print(f"애프터장 체결가를 받지 못함: {error}", file=sys.stderr)
            stock["after"] = [own.get(day) for day in found["dates"]]


def stock_pages(con: sqlite3.Connection, cm, board: dict, start: str, folder: Path, out: Path) -> dict:
    """지도 종목 → 종목 상세 페이지의 값. 심볼, 한글 이름, 업종, 설명, 지도 지수와 그 지수 안 시가총액 순위, `start`부터의 [날짜, 정규장 종가],
    공시 카드 세 장, 대표 이미지다.

    시가총액은 지도의 주식 수 × 마지막 종가다. 종가는 지도와 같이 야후 원 종가에 토스 종가를 메운다. 공시 카드는 invest-stock-profile 스킬이
    `stock_detail` 표에 쓴 값이고, 카드가 아직 없는 종목은 빈 목록으로 둔다. 대표 이미지는 `stock_image` 표의 그린 묶음(`images`)에서
    그림 파일이 있는 그림마다 `folder`로 복사한 파일의 `app.html` 기준 주소, 폭과 높이, 사진 설명이고, 그린 묶음이 없는 종목은 빈 목록으로 둔다.
    """
    tables = {name for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    cards = {symbol: json.loads(text) for symbol, text in con.execute("SELECT symbol, cards FROM stock_detail")} if "stock_detail" in tables else {}
    drawn = ({symbol: json.loads(text) for symbol, text in con.execute("SELECT symbol, images FROM stock_image WHERE images IS NOT NULL")}
             if "stock_image" in tables else {})

    def pictures(symbol: str) -> list[dict]:
        found = []
        for k, image in enumerate(drawn.get(symbol, []), 1):
            source = STOCK_IMAGES / f"{symbol}-{k}.webp"
            if not source.is_file():
                continue
            shutil.copy2(source, folder / source.name)
            with Image.open(source) as picture:
                width, height = picture.size
            found.append({"src": versioned(folder / source.name, out), "width": width, "height": height, "caption": image["caption"]})
        return found

    pages = {}
    for index, found in board.items():
        cap = lambda stock: stock["shares"] * next((close for close in reversed(stock["closes"]) if close is not None), 0)
        for rank, stock in enumerate(sorted(found["stocks"], key=cap, reverse=True), 1):
            if stock["symbol"] in pages:
                continue
            closes = {**observed(con, cm.toss_id(stock["symbol"]), "value", start), **observed(con, cm.breadth_id(stock["symbol"]), "value", start)}
            pages[stock["symbol"]] = {key: stock[key] for key in ("symbol", "name", "sector", "about")} | {
                "index": index, "rank": rank, "closes": [[day, round(closes[day], 2)] for day in sorted(closes)], "cards": cards.get(stock["symbol"], []),
                "images": pictures(stock["symbol"])}
    return pages


def market(vault: Path, out: Path) -> Path:
    """`r/market.json`의 `map`에 지수마다 지도의 값(`index_map`)과 애프터장 값(`after_prices`)을 쓰고, `r/stocks/{심볼}.json`에 지도 종목마다
    종목 상세 페이지의 값(`stock_pages`)을, `r/stocks/{심볼}-{순번}.webp`에 대표 이미지를 쓴다.

    지도 날짜는 공개본이 있는 가장 늦은 리포트 날짜에서 `REWIND_DAYS`일과 `MAP_LEAD_DAYS`일을 거슬러 간 날부터다.
    종목 상세 페이지의 종가는 그 날짜에서 `STOCK_DAYS`일을 거슬러 간 날부터다. 지도에서 내려간 종목의 파일과 페이지가 싣지 않는 그림 파일은 지운다.
    """
    published = sorted(p.name[:8] for p in (out / "r").glob("*-*") if p.name[:8].isdigit())
    latest = dt.date.fromisoformat(f"{published[-1][:4]}-{published[-1][4:6]}-{published[-1][6:]}")
    con = sqlite3.connect(f"file:{predictions_chart(vault).path_bands.REFERENCE_DB_PATH}?mode=ro", uri=True)
    try:
        cm = render_inputs(vault).cm
        start = (latest - dt.timedelta(days=REWIND_DAYS + MAP_LEAD_DAYS)).isoformat()
        board = {index: index_map(con, cm, index, start) for index in cm.ROSTER_INDEX}
        target = out / "r" / "market.json"
        after_prices(board, json.loads(target.read_text(encoding="utf-8"))["map"] if target.exists() else {}, render_inputs(vault).price_source)
        folder = out / "r" / "stocks"
        folder.mkdir(exist_ok=True)
        pages = stock_pages(con, cm, board, (latest - dt.timedelta(days=STOCK_DAYS)).isoformat(), folder, out)
    finally:
        con.close()
    target.write_text(json.dumps({"map": board}, ensure_ascii=False) + "\n", encoding="utf-8")
    shown = {f"{symbol}.json" for symbol in pages} | {image["src"].split("?")[0].rsplit("/", 1)[1] for page in pages.values() for image in page["images"]}
    for page in folder.iterdir():
        if page.name not in shown:
            page.unlink()
    for symbol, page in pages.items():
        (folder / f"{symbol}.json").write_text(json.dumps(page, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def premarket(vault: Path, out: Path) -> Path | None:
    """`r/premarket.json`에 지수마다 오늘 뉴욕 프리장의 지금까지 마지막 체결가를 오늘 날짜를 키로 쓴다.

    값은 지수 ETF(`SECTOR_DB_TICKERS`)의 앞 세션 정규장 종가 대비 비율(`ratio`)과 `r/market.json` 지도 종목마다의 체결가(`stocks`)이고,
    앞 세션 날짜(`session`)와 체결가를 받은 끝 시각(`time`, 뉴욕 시각)을 함께 적는다. 체결가는 그 시각까지의 마지막 체결가를 토스 1분봉에서,
    답하지 않으면 야후 1분봉에서 받는다(`price_source.batch_time_price`). 마지막 체결이 오늘 `PREMARKET_OPEN` 전이면 프리장 체결이 없으므로 null이다.
    끝 시각은 지금과 정규장이 열리는 `PREMARKET_CLOSE` 가운데 이른 쪽이라, 정규장이 열린 뒤에는 프리장 마지막 체결가가 남는다.
    오늘이 뉴욕 정규장 세션이 아니거나, 지금이 `PREMARKET_OPEN` 전이거나, 오늘 값을 `PREMARKET_CLOSE`까지 이미 받았으면 쓰지 않고 `None`이다.
    지도의 첫 날짜보다 앞선 날짜의 값은 지운다.
    """
    now = dt.datetime.now(NEW_YORK)
    today = now.date()
    xnys = exchange_calendars.get_calendar("XNYS")
    if not xnys.is_session(today.isoformat()) or now.time() < PREMARKET_OPEN:
        return None
    board = json.loads((out / "r" / "market.json").read_text(encoding="utf-8"))["map"]
    target = out / "r" / "premarket.json"
    kept = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    end = min(now, dt.datetime.combine(today, PREMARKET_CLOSE, NEW_YORK)).replace(second=0, microsecond=0)
    if all(kept.get(index, {}).get(today.isoformat(), {}).get("time") == end.isoformat() for index in board):
        return None
    session = xnys.previous_session(today.isoformat()).date().isoformat()
    opened = dt.datetime.combine(today, PREMARKET_OPEN, NEW_YORK)
    source, etfs = render_inputs(vault).price_source, predictions_chart(vault).path_bands.SECTOR_DB_TICKERS

    @functools.cache
    def trade(symbol: str) -> dict | None:
        try:
            found = source.batch_time_price(symbol, session, end.isoformat())
        except RuntimeError as error:
            print(f"프리장 체결가를 받지 못함: {error}", file=sys.stderr)
            return None
        return found if dt.datetime.fromisoformat(found["time"]) > opened else None

    for index, found in board.items():
        etf = trade(etfs[index])
        own = kept.setdefault(index, {})
        own[today.isoformat()] = {"session": session, "time": end.isoformat(), "ratio": etf and round(etf["ratio"], 6),
                                  "stocks": {stock["symbol"]: (got := trade(stock["symbol"])) and round(got["price"], 2) for stock in found["stocks"]}}
        for day in [day for day in own if day < found["dates"][0]]:
            del own[day]
    target.write_text(json.dumps(kept, ensure_ascii=False) + "\n", encoding="utf-8")
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


def announcements(vault: Path, index: str, date: dt.date) -> dict[tuple[str, str], str]:
    """(뉴욕 발표일, 이벤트 이름)마다 사안 나무의 발표 시각(`announced`). 이름이 빈 키에는 그날 발표가 모두 같은 장 구분일 때만
    그 장 구분의 시각(`PHASE_TIMES`)을 둔다.

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
    days: dict[str, set[str]] = {}
    for (day, _), announced in announced_at.items():
        days.setdefault(day, set()).add(phase(announced))
    return announced_at | {(day, ""): f"{day} {PHASE_TIMES[values.pop()]}" for day, values in days.items() if len(values) == 1}


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


def mark_days(body: str, date: dt.date, branches: dict[str, dict], moments: dict[tuple[str, str], str],
              upcoming: list[dict], reaction) -> str:
    """`이벤트 캘린더` 절의 소제목에 발표가 주가에 닿는 거래일(`data-day`)과 뉴욕 발표일(`data-announced`)을 달고 제목에서 날짜를 지운다.

    발표 시각은 `moments`(`announcements`)의 그 이벤트 시각, 소제목의 장 구분 시각(`PHASE_TIMES`), 그날의 장 구분 시각 순으로 찾는다.
    거래일은 발표 시각을 `reaction`(`scenario_tree.reaction_session`)에 넣어 얻고, 발표 시각이 없으면 발표일 0시로 넣는다.
    발표 시각은 제목 앞 `when` 이름표(`when_label`)로 단다. 이름표가 한국 시각이 아니고 발표일이 거래일과 다르면 앞에 발표일을 붙인다.
    소제목의 중요도 표식은 `data-level`로도 단다.
    리포트 날짜 전에 발표한 이벤트의 표에는 `judged`를, 실제 갈래 줄에는 `hit`을 달고 그 줄의 전개 예상 뒤에 실제 전개를 붙인다.
    결과를 다룬 이슈가 있으면 실제 갈래 줄에 `data-result`로 단다.
    리포트 날짜와 그 뒤에 발표하는 이벤트의 표에는 `upcoming`(`display.json`의 `next`)의 갈래 변화를 붙인다.
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
        announced = (moments.get((f"{day}", name)) or (f"{day} {PHASE_TIMES[when]}" if when else None)
                     or moments.get((f"{day}", "")))
        session = reaction(announced or f"{day} 00:00")
        when = when_label(announced) if announced else ""
        if not when.endswith("KST") and session != f"{day}":
            when = f"{day:%m/%d}({'월화수목금토일'[day.weekday()]}) {when}".strip()
        label = f'<span class="when">{when}</span>' if when else ""
        tag = re.search(r"<code>중요도 ([^<]*)</code>", rest)
        level = LEVELS.get(tag.group(1)) if tag else None
        mark = f' data-level="{level}"' if level else ""
        return f'<h3{attrs} data-day="{session}" data-announced="{day}"{mark}>{label}{rest}</h3>'

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

    section = re.sub(r'<h3[^>]* data-announced="([^"]+)"(?: data-level="[^"]*")?>(?:<span class="when">[^<]*</span>)?(.*?)</h3>\s*(<table class="events">.*?</table>)',
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


def stored_data(vault: Path, index: str) -> tuple[dict, dict]:
    """지금까지 `reference.db`에 적재한 값으로 만든 (`market-data.json`, `macro-data.json`) 내용. 판단 배치의 입력 준비와 같은 `render_inputs.py` 함수로 만든다."""
    inputs = render_inputs(vault)
    store = inputs.store
    con = store.connect(store.DB_PATH)
    try:
        source = inputs.Source(con, store.as_cutoff(dt.datetime.now(SEOUL).isoformat(timespec="seconds")))
        return inputs.render_market(source, index, store.DB_PATH), inputs.render_macro(source, store.DB_PATH)
    finally:
        con.close()


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
    `help`는 카드 이름 뒤의 물음표 단추가 띄우는 설명 상자의 문단 목록이고, 지표를 무엇으로 계산하는지와 값을 읽는 법을 쓴다.
    `asof`는 출처와 기준일이고, 기준일은 한국 날짜이므로 날짜 뒤에 KST를 붙인다."""
    when = f"{month_day(date)} KST"
    if name == "공포·탐욕 지수":
        score = value["score"]
        guide = ["CNN이 지표 7개를 합쳐 미국 주식시장의 투자 심리를 0점에서 100점 사이로 매긴 점수예요.",
                 "25 이하면 극단 공포, 75를 넘으면 극단 탐욕이에요. 점수가 낮을수록 투자자는 주식을 팔고 안전자산을 사요."]
        return {"tab": "공포·탐욕", "help": guide, "asof": f"CNN · {when}", "value": f"{score:g}", "state": zone(FEAR_GREED_ZONES, score),
                "figure": {"type": "semi", "min": 0, "max": 100, "zones": FEAR_GREED_ZONES, "value": score, "ends": ["공포", "탐욕"]}}
    if name == "하이일드 스프레드":
        level = value["value"]
        guide = ["신용등급이 낮은 미국 회사채의 금리에서 미국 국채의 금리를 뺀 값이에요. 투자자가 경기를 나쁘게 볼수록 스프레드가 커져요.",
                 "1년 상위 3%면 지난 1년 가운데 오늘보다 스프레드가 높았던 날이 3%뿐이에요."]
        top = math.ceil(max(item["value"] for _, item in weeks) + 0.3)
        return {"tab": "신용", "help": guide, "asof": f"FRED · {when}", "value": f"{level:.2f}", "unit": "%",
                "state": year_rank(value["pct_1y"]),
                "figure": {"type": "columns", "bars": [[month_day(day), item["value"], f"{item['value']:.2f}%"] for day, item in weeks],
                           "max": top, "lines": [[step, f"{step}%"] for step in range(1, top + 1)]}}
    if name == "WTI 유가":
        level = value["value"]
        guide = ["미국 텍사스산 원유(WTI) 1배럴의 선물 정산가를 달러로 적은 값이에요.",
                 "유가가 오르면 물가가 올라요. 물가가 오르면 연준이 기준금리를 내리기 어려워져요. 1년 상위 %는 지난 1년 가운데 오늘보다 유가가 높았던 날의 비율이에요."]
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
    guide = ["앞으로 열리는 연준 회의 세 번마다 시장이 예상하는 기준금리의 누적 변화예요. 예상치는 연방기금 금리 선물에서 계산해요.",
             f"다음 회의까지 +{RATE_MOVE_BP / 100:g}%p 이상이면 인상 예상, −{RATE_MOVE_BP / 100:g}%p 이하면 인하 예상, 그 사이면 동결 예상이에요. "
             "인상 예상은 기업의 차입 비용을 키우므로 주가에 부정적이에요."]
    return {"tab": "금리 경로", "help": guide, "asof": f"연방기금 선물 · {when}", "value": signed(move / 100, 2), "unit": "%p", "state": state,
            "figure": {"type": "diverge", "rows": rows, "max": RATE_RANGE_BP, "step": RATE_STEP_BP}}


def indicator_cards(vault: Path, index: str, date: dt.date, current: tuple[dict, dict] | None = None) -> dict[str, dict]:
    """그날 리포트의 지표 이름마다 카드 값. 앞 `WEEKS`주 리포트의 값을 기준일마다 모아 주마다 마지막 값을 함께 넘긴다.

    `current`를 받으면 그날 지수 폴더의 JSON 대신 그 값을 그날 값으로 쓴다.
    """
    current = current or batch_data(vault, index, date)
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
    """`미국 거시 지표` 절의 소제목 가운데 `cards`에 있는 지표에 카드 값(`data-card`)을 단다. 소제목에 이미 있던 카드 값은 지운다."""
    head = re.search(rf'<h2 id="[^"]*">{INDICATORS_TITLE}</h2>', body)
    if not head:
        return body
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end

    def heading(match: re.Match) -> str:
        name = html.unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip()
        attrs = re.sub(r'\s+data-card="[^"]*"', "", match.group(1))
        if name not in cards:
            return f'<h3{attrs}>{match.group(2)}</h3>'
        card = html.escape(json.dumps(cards[name], ensure_ascii=False))
        return f'<h3{attrs} data-card="{card}">{match.group(2)}</h3>'

    section = re.sub(r"<h3([^>]*)>(.*?)</h3>", heading, body[head.end():end], flags=re.DOTALL)
    return body[:head.end()] + section + body[end:]



def mark_issue_ids(body: str, bundles: Path, events: dict[int, list[tuple[str, str | None]]], day: dt.date) -> str:
    """`상세 이슈 해설` 절의 번호 붙은 이슈 소제목에 `system/issues.json`의 그 번호 `id`를 `data-issue`로 단다.
    이슈 해설을 쓴 날짜를 `data-written`으로 함께 달고, 그 이슈를 새로 썼으면(`rewrite`) `data-new`를,
    앞 리포트에서 옮겨 왔으면(`carry`) 처음 쓴 날짜부터 리포트 날짜까지의 날 수를 `data-age`로 단다.
    `events`에 그 번호가 있으면 결과를 다룬 이벤트 이름을 `data-event`로 함께 달고, 그 이벤트가 모두 중요도 낮음이면 `data-event-level="low"`도 단다."""
    head = re.search(rf'<h2 id="[^"]*">{ISSUES_TITLE}</h2>', body)
    if not head or not bundles.is_file():
        return body
    marked = {bundle["issue"]: bundle for bundle in json.loads(bundles.read_text(encoding="utf-8"))["issues"]}
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end

    def heading(match: re.Match) -> str:
        number = re.match(r"(\d+)\.\s", html.unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip())
        bundle = marked.get(int(number.group(1))) if number else None
        if not bundle:
            return match.group(0)
        written = dt.date.fromisoformat(bundle["carry"]["date"]) if "carry" in bundle else day
        state = f' data-written="{written}"' + (" data-new" if "rewrite" in bundle else "")
        if "carry" in bundle:
            state += f' data-age="{(day - written).days}"'
        found = events.get(int(number.group(1)), [])
        event = f' data-event="{html.escape(" · ".join(name for name, _ in found))}"' if found else ""
        if found and all(level == "low" for _, level in found):
            event += ' data-event-level="low"'
        return f'<h3{match.group(1)} data-issue="{html.escape(bundle["id"])}"{state}{event}>{match.group(2)}</h3>'

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


def mark_issue_carry(body: str, bundles: Path, index: str, out: Path) -> str:
    """앞 리포트에서 옮겨 온 이슈(`system/issues.json`의 `carry`)는 소제목 뒤 내용을 처음 쓴 리포트 공개본의 그 번호 이슈 조각으로 바꿔,
    그날의 그림과 그래프를 그대로 보인다. 처음 쓴 리포트의 공개본이 없으면 그대로 둔다."""
    if not bundles.is_file():
        return body
    origins = {bundle["id"]: bundle["carry"] for bundle in json.loads(bundles.read_text(encoding="utf-8"))["issues"] if "carry" in bundle}
    parts, last = [], 0
    for start, stop in issue_segments(body):
        segment = body[start:stop]
        issue = re.match(r'<h3[^>]*data-issue="([^"]*)"', segment)
        origin = origins.get(html.unescape(issue.group(1))) if issue else None
        page = out / "r" / f"{origin['date'].replace('-', '')}-{index}" / "report.html" if origin else None
        if not page or not page.is_file():
            continue
        earlier = HISTORY_RE.sub("", page.read_text(encoding="utf-8"))
        found = next((earlier[at:end] for at, end in issue_segments(earlier)
                      if re.match(rf"{origin['issue']}\.\s", html.unescape(re.sub(r"<[^>]+>", "", earlier[at:earlier.find("</h3>", at)])).strip())), None)
        if found is None:
            continue
        cut = segment.find("</h3>") + len("</h3>")
        parts += [body[last:start], segment[:cut], re.sub(r'\sid="[^"]*"', "", found[found.find("</h3>") + len("</h3>"):])]
        last = stop
    return "".join(parts) + body[last:]


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
    """오늘 이슈 `id`마다, 그 `id`를 노드로 묶은 앞 날짜 이슈의 날짜와 이슈 번호와 공개본 이슈 조각을 날짜 순으로.
    앞 리포트에서 옮겨 온 앞 날짜 이슈는 처음 쓴 날짜의 이슈와 같은 조각이므로 넣지 않고, 오늘 옮겨 온 이슈는 처음 쓴 날짜의 이슈를 넣지 않는다."""
    bundles = report_path(vault, day, index).parent / "system" / "issues.json"
    if not bundles.is_file():
        return {}
    today = json.loads(bundles.read_text(encoding="utf-8"))["issues"]
    history = {bundle["id"]: [] for bundle in today}
    carried = {bundle["id"]: bundle["carry"]["date"] for bundle in today if "carry" in bundle}
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
            if "carry" in bundle:
                continue
            for issue in history:
                if issue in bundle["nodes"] and bundle["id"] in segments and carried.get(issue) != name:
                    history[issue].append((past, bundle["issue"], segments[bundle["id"]]))
    return history


def mark_issue_history(body: str, history: dict[str, list[tuple[dt.date, int, str]]], day: dt.date) -> str:
    """번호 붙은 이슈 뒤에 앞 날짜 이슈 조각과 날짜마다 이슈 해설 소제목을 담은 `issue-history` 템플릿을 넣는다.
    마지막 항목은 오늘 이슈이고, 그 항목의 날짜는 이슈 해설을 쓴 날짜(`data-written`)다."""
    parts, last = [], 0
    for start, stop in issue_segments(body):
        segment = body[start:stop]
        issue = re.match(r'<h3[^>]*data-issue="([^"]*)"', segment)
        past = history.get(html.unescape(issue.group(1)), []) if issue else []
        if not past:
            continue
        days = [(when, explainer_title(chunk), re.sub(r'\sid="[^"]*"', "", chunk)) for when, _, chunk in past]
        written = re.match(r'<h3[^>]*data-written="([^"]*)"', segment)
        days.append((dt.date.fromisoformat(written.group(1)) if written else day, explainer_title(segment), ""))
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
    body = mark_days(body, day, branches, announcements(vault, index, day), upcoming,
                     functools.cache(scenario_tree(vault).reaction_session))
    body = mark_indicators(body, indicator_cards(vault, index, day))
    body = mark_issue_ids(body, source.parent / "system" / "issues.json", issue_events(vault, index, day), day)
    body = mark_issue_images(body, source.parent / "assets", source.parent / "system" / "issue-images.json", target, out)
    body = mark_issue_charts(body, source.parent / "system" / "issue-charts.json")
    body = mark_issue_carry(body, source.parent / "system" / "issues.json", index, out)
    history = issue_history(vault, index, day, out)
    body = mark_issue_history(body, history, day)
    if card:
        data = json.dumps(card, ensure_ascii=False).replace("</", "<\\/")
        body += f'<script type="application/json" id="cards">{data}</script>\n'
    (target / "report.html").write_text(body, encoding="utf-8")

    entries = published_entries(out)
    heading = TITLE_RE.match(html.unescape(title))
    if not heading:
        raise SystemExit(f"제목 끝에 날짜가 없다: {title}")
    written = entries.get(key, {}).get("written") or dt.datetime.now(SEOUL).strftime("%Y-%m-%d %H:%M")
    later = entries.get(key, {}).get("later")
    entries[key] = {"title": heading.group(1), "day": heading.group(2), "written": written, "date": date, "index": index}
    if later:
        entries[key]["later"] = later
    if (move := moves(vault, index, date)):
        entries[key]["moves"] = move
    link_later(entries, key, history, source.parent / "system" / "issues.json")
    write_entries(out, entries)
    rewind(index, vault, out)
    market(vault, out)
    return key


def published_entries(out: Path) -> dict:
    listing = out / "r" / "index.json"
    return json.loads(listing.read_text(encoding="utf-8")) if listing.exists() else {}


def write_entries(out: Path, entries: dict) -> None:
    (out / "r" / "index.json").write_text(json.dumps(dict(sorted(entries.items(), reverse=True)), ensure_ascii=False, indent=1) + "\n",
                                         encoding="utf-8")


def pre_issues(body: str, day: dt.date) -> str:
    """`상세 이슈 해설` 절의 이슈 소제목에서 `data-new`를 지우고, 이슈 해설을 쓴 날짜(`data-written`)부터 `day`까지의 날 수를 `data-age`로 다시 단다.
    `issue-history` 템플릿 안의 앞 날짜 이슈는 그대로 둔다."""
    head = re.search(rf'<h2 id="[^"]*">{ISSUES_TITLE}</h2>', body)
    if not head:
        return body
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end

    def heading(match: re.Match) -> str:
        if match.group(1):
            return match.group(1)
        attrs = re.sub(r'\s+data-(?:new|age="[^"]*")(?=\s|$)', "", match.group(2))
        written = re.search(r'data-written="([^"]*)"', attrs)
        if written:
            attrs += f' data-age="{(day - dt.date.fromisoformat(written.group(1))).days}"'
        return f"<h3{attrs}>"

    section = re.sub(r'(<template class="issue-history">.*?</template>)|<h3([^>]*)>', heading, body[head.end():end], flags=re.DOTALL)
    return body[:head.end()] + section + body[end:]


def pre_indicators(body: str) -> str:
    """`미국 거시 지표` 절에서 소제목만 남기고 소제목 뒤의 해설을 지운다. 첫 소제목 앞의 노드는 그대로 둔다."""
    head = re.search(rf'<h2 id="[^"]*">{INDICATORS_TITLE}</h2>', body)
    if not head:
        return body
    end = body.find("<h2", head.end())
    end = len(body) if end < 0 else end
    section = body[head.end():end]
    first = section.find("<h3")
    if first < 0:
        return body
    headings = "".join(f"{h3}\n" for h3 in re.findall(r"<h3[^>]*>.*?</h3>", section[first:], flags=re.DOTALL))
    return body[:head.end()] + section[:first] + headings + body[end:]


def pre(date: str, index: str, vault: Path, out: Path) -> str:
    """리포트 날짜 `date`의 사전 리포트를 그 지수의 가장 늦은 본 리포트 공개본으로 만든다. 목록 항목의 `stage`는 `pre`이고,
    이미 `running`으로 바꾼 사전 리포트를 다시 만들면 `running`을 그대로 둔다.

    전날이 뉴욕 정규장 세션이 아니면 만들지 않고 종료 코드 3으로 끝낸다. 그날 본 리포트가 이미 있으면 종료 코드 4로 끝낸다.
    전날 세션의 종가가 `reference.db`에 아직 없으면 실패로 끝낸다.
    """
    day = dt.date.fromisoformat(date)
    key = f"{date.replace('-', '')}-{index}"
    entries = published_entries(out)
    if key in entries and "stage" not in entries[key]:
        print(f"본 리포트가 이미 있다: {key}", file=sys.stderr)
        sys.exit(4)
    session = day - dt.timedelta(days=1)
    if not exchange_calendars.get_calendar("XNYS").is_session(session.isoformat()):
        print(f"전날 뉴욕 정규장이 열리지 않았다: {session}", file=sys.stderr)
        sys.exit(3)
    chart = predictions_chart(vault)
    con = sqlite3.connect(f"file:{chart.path_bands.REFERENCE_DB_PATH}?mode=ro", uri=True)
    try:
        history = con.execute(
            "SELECT price_date, close FROM market_price WHERE ticker=? AND price_date BETWEEN ? AND ? ORDER BY price_date",
            (chart.path_bands.SECTOR_DB_TICKERS[index], (day - dt.timedelta(days=round(365.25 * PRICE_YEARS) + 1)).isoformat(),
             session.isoformat())).fetchall()
    finally:
        con.close()
    if not history or history[-1][0] != session.isoformat():
        raise SystemExit(f"전날 정규장 종가가 reference.db에 없다: {index} 마지막 종가 {history[-1][0] if history else '없음'}")
    for name in [name for name, entry in entries.items()
                 if entry["index"] == index and entry.get("stage") and entry["date"] < date]:
        del entries[name]
        shutil.rmtree(out / "r" / name, ignore_errors=True)
    previous = max((name for name, entry in entries.items()
                    if entry["index"] == index and "stage" not in entry and entry["date"] < date), default=None)
    if not previous:
        raise SystemExit(f"앞 본 리포트가 없다: {index}")

    body = (out / "r" / previous / "report.html").read_text(encoding="utf-8")
    body = re.sub(r'<script type="application/json" id="cards">.*?</script>\n?', "", body, flags=re.DOTALL)
    outlook = re.search(r'<h2 id="[^"]*">1개월 지수 방향 예측</h2>', body)
    if outlook:
        end = body.find("<h2", outlook.end())
        body = body[:outlook.end()] + "\n" + body[end if end >= 0 else len(body):]
    body = pre_issues(body, day)
    body = mark_indicators(pre_indicators(body), indicator_cards(vault, index, day, stored_data(vault, index)))
    scale = card_scale(index, vault)
    closes = [round(close * scale, 2) for _, close in history]
    dates = [d for d, _ in history]
    card = {"pre": True, "start_offset": chart.START_OFFSET, "dates": dates, "history": closes,
            "past": past_cards(index, date, dates, len(dates) - 1 + chart.path_bands.PATH_BAND_HORIZON, scale, vault),
            "day": date, "base_date": history[-1][0], "base": closes[-1]}
    body += f'<script type="application/json" id="cards">{json.dumps(card, ensure_ascii=False)}</script>\n'
    target = out / "r" / key
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    (target / "report.html").write_text(body, encoding="utf-8")

    close, before = history[-1][1], history[-2][1]
    entries[key] = {"title": entries[previous]["title"], "day": f"{date} ({'월화수목금토일'[day.weekday()]})", "date": date,
                    "index": index, "stage": entries.get(key, {}).get("stage", "pre"),
                    "moves": {"session": round((close / before - 1) * 100, 2) + 0.0, "after": None, "close": round(close, 2), "base": None}}
    write_entries(out, entries)
    market(vault, out)
    return key


def running(date: str, index: str, vault: Path, out: Path) -> str | None:
    """리포트 날짜 `date`의 사전 리포트 목록 항목의 `stage`를 `running`으로 바꾸고, 시장 페이지의 지도와 종목 상세 페이지의 값(`market`)을
    다시 써서 지도에 전날 애프터장 값을 단다. 사전 리포트가 없으면 `None`이다."""
    key = f"{date.replace('-', '')}-{index}"
    entries = published_entries(out)
    if entries.get(key, {}).get("stage") != "pre":
        return None
    market(vault, out)
    entries[key]["stage"] = "running"
    write_entries(out, entries)
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description="판단 리포트 공개본을 `invest-reports` 미니 앱 조각으로 만든다")
    parser.add_argument("--date", help="리포트 날짜 YYYY-MM-DD")
    parser.add_argument("--index", help="지수 폴더 이름 (nasdaq, biotech)")
    parser.add_argument("--vault", default=str(Path.home() / "obsidian-vault"))
    parser.add_argument("--out", default=str(ROOT))
    parser.add_argument("--stage", choices=("pre", "running"), help="본 리포트 대신 사전 리포트를 만들거나(pre) 사전 리포트를 분석 중으로 바꾼다(running)")
    parser.add_argument("--premarket", action="store_true", help="리포트 대신 오늘 프리장 값(`r/premarket.json`)만 쓴다")
    args = parser.parse_args()
    vault, out = Path(args.vault).expanduser(), Path(args.out)
    if args.premarket:
        print(premarket(vault, out) or "")
        return 0
    if not (args.date and args.index):
        parser.error("--premarket이 아니면 --date와 --index가 필요하다")
    if args.stage == "pre":
        print(pre(args.date, args.index, vault, out))
    elif args.stage == "running":
        print(running(args.date, args.index, vault, out) or "")
    else:
        print(build(args.date, args.index, vault, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
