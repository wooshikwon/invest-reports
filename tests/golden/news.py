"""종목 뉴스 화면의 동작 시험. 리포트 화면의 "상세 이슈 해설 | 종목 뉴스" 탭, 뉴스 상세, 종목 상세의 주요뉴스 절을 `fixtures.NEWS`의 SAMPLE 기사로 연다.

    python3 tests/golden/news.py --data ~/repos/invest-reports-news --shots /tmp/sn-u8/shots

`--data`는 2026-11-19 나스닥·바이오 리포트와 `r/market.json` 지도, `r/stocks/NVDA.json`이 있는 리포트 자료다. 기사 그림은 그 자료의 `r/stocks/{종목}-{순번}.webp`를 쓴다.
뉴스 Worker 응답은 `capture.Server`가 `fixtures.news_answer`로 지어내고, 무응답은 `Server.news_down`으로 요청을 abort해 만든다.
화면 시각은 `fixtures.NOW`(11/19 23:45 KST)다. 기대값은 SAMPLE 기사의 회차 시작 시각으로 손으로 셈한 제목이다.
"""
import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import capture
import fixtures

NASDAQ = "20261119-nasdaq"
BIOTECH = "20261119-biotech"
TITLES = [title for _, _, _, title, _ in fixtures.NEWS]
# 나스닥 리포트의 종목 뉴스 탭이 처음 보이는 3일 치(11/16 23:45 KST 뒤 회차)와 더 보기 뒤 7일 치(11/12 23:45 KST 뒤 회차) 기사 제목.
NASDAQ_3 = TITLES[0:6]
NASDAQ_7 = TITLES[0:9]
BIOTECH_7 = TITLES[15:18]
# NVDA를 단 기사 제목을 최신순으로 열 편까지 적는다.
NVDA = [TITLES[k] for k in (0, 2, 4, 6, 8, 9, 10, 11, 12, 13)]
FAILS = []

LIST = "() => [...document.querySelectorAll('.news-box .pick h3')].filter((h) => h.offsetParent).map((h) => h.firstChild.textContent.trim())"
ROWS = "() => [...document.querySelectorAll('.headlines .entry')].filter((row) => row.offsetParent).map((row) => row.querySelector('.title').textContent.trim())"
BAR = """() => { const bar = document.querySelector('h2.tabbed .bar').getBoundingClientRect(), on = document.querySelector('h2.tabbed .tabline > button.on');
  const box = on.getBoundingClientRect(); return { tab: on.textContent, bar: [bar.left, bar.width, bar.bottom], on: [box.left, box.width, box.bottom] }; }"""
# 보이는 뉴스 상세 문단. 제목, 종목 스티커, 그림 수, 이슈 해설 말머리 뒤 글(머리 줄은 목록에만 있어 비어야 한다), 소제목, 그려진 그래프 카드 수, 용어 단추 수, 이전·다음 칸 제목.
PAGE = """() => { const page = document.querySelector('.issue-page.on'), h3 = page.querySelector(':scope > h3'), lead = page.querySelector(':scope > h4');
  const cell = (side) => page.querySelector(`nav.step .${side} .title`)?.textContent.trim() ?? null;
  return { title: h3.firstChild.textContent.trim(), tickers: [...h3.querySelectorAll('.tags code')].map((c) => c.textContent), bar: document.getElementById('issue-bar').textContent,
    photos: page.querySelectorAll(':scope > figure.issue-image figure.photo').length, mark: lead?.querySelector('mark')?.textContent,
    headline: lead ? [...lead.childNodes].filter((n) => n.nodeName !== 'MARK').map((n) => n.textContent).join('').trim() : null,
    h5: [...page.querySelectorAll(':scope > h5')].map((h) => h.textContent.trim()), charts: page.querySelectorAll(':scope > figure.issue-chart svg').length,
    terms: page.querySelectorAll('button.term').length, prev: cell('prev'), next: cell('next'), search: location.search }; }"""


def check(name: str, ok: bool, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILS.append(name)


def near(a: list, b: list) -> bool:
    return all(abs(x - y) <= 1 for x, y in zip(a, b))


def open_news(run, key: str):
    page = run.open(f"?r={key}")
    capture.turn(page, "이슈")
    page.locator("h2.tabbed .tabline > button", has_text="종목 뉴스").click()
    capture.settle(page, 800)
    return page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--shots", required=True)
    args = parser.parse_args()
    shots = Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    server = capture.Server(capture.REPO, Path(args.data))
    with sync_playwright() as p:
        browser = capture.launch(p)
        run = capture.Run(browser, server)

        # 탭 줄과 막대, 지수별 목록, 더 보기
        page = run.open(f"?r={NASDAQ}")
        capture.turn(page, "이슈")
        before = page.evaluate(BAR)
        page.locator("h2.tabbed .tabline > button", has_text="종목 뉴스").click()
        capture.settle(page, 800)
        after = page.evaluate(BAR)
        check("처음에는 상세 이슈 해설 탭을 고르고 막대가 그 탭 아래에 있다", before["tab"] == "상세 이슈 해설" and near(before["bar"][:2], before["on"][:2]), str(before))
        check("탭을 바꾸면 막대가 고른 탭 아래로 옮겨 간다", after["tab"] == "종목 뉴스" and near(after["bar"][:2], after["on"][:2])
              and after["bar"][0] > before["bar"][0] + 20, str(after))
        hidden = page.evaluate("() => [document.querySelector('.issue-box').hidden, document.querySelector('.news-box').hidden]")
        check("종목 뉴스 탭은 이슈 목록을 감추고 기사 목록을 보인다", hidden == [True, False], str(hidden))
        shown = page.evaluate(LIST)
        check("나스닥 리포트는 3일 안의 나스닥 기사만 최신순으로 보인다", shown == NASDAQ_3, " | ".join(shown))
        check("나스닥 리포트에서 바이오 종목 기사가 보이지 않는다", not set(shown) & set(BIOTECH_7))
        parts = page.evaluate("() => ['.news-box .pick', '.news-box .pick code', '.news-box .pick .thumb', '.news-box .pick .age'].map((q) => document.querySelectorAll(q).length)")
        check("기사 블록마다 회차 시각이 있고 종목 스티커와 썸네일은 없다", parts[1] == parts[2] == 0 and parts[3] == parts[0] > 0, str(parts))
        stamp = page.evaluate("() => document.querySelector('.news-box > .issue-asof')?.textContent")
        check("종목 뉴스 탭 첫 줄에 가장 최근 회차의 마지막 업데이트 시각이 있다", bool(stamp and re.fullmatch(r"마지막 업데이트 \d{1,2}/\d{1,2} \d\d:\d\d KST", stamp)), str(stamp))
        page.evaluate("scrollTo(0, 0)")
        capture.settle(page, 300)
        page.screenshot(path=str(shots / "news-tab.png"))
        page.locator(".news-box button.more").click()
        capture.settle(page, 600)
        shown = page.evaluate(LIST)
        check("더 보기를 누르면 7일 치 기사가 보이고 더 보기 단추가 사라진다", shown == NASDAQ_7 and not page.locator(".news-box button.more").is_visible(), " | ".join(shown))
        page.locator("h2.tabbed .tabline > button", has_text="상세 이슈 해설").click()
        capture.settle(page, 600)
        back = page.evaluate(BAR)
        check("상세 이슈 해설 탭으로 돌아오면 막대도 돌아온다", back["tab"] == "상세 이슈 해설" and near(back["bar"][:2], before["bar"][:2]), str(back))
        run.close()

        page = open_news(run, BIOTECH)
        shown = page.evaluate(LIST)
        check("바이오 리포트는 바이오 기사만 보인다", shown == BIOTECH_7, " | ".join(shown))
        run.close()

        # 종목 뉴스 탭에서 연 뉴스 상세
        page = open_news(run, NASDAQ)
        page.locator(".news-box .pick", has_text=TITLES[2]).click()
        capture.settle(page)
        found = page.evaluate(PAGE)
        check("종목 뉴스 탭에서 연 뉴스 상세의 앞뒤 기사는 지수 목록의 앞뒤 기사다", found["title"] == TITLES[2] and found["prev"] == TITLES[1] and found["next"] == TITLES[3], str(found))
        page.locator("button.back").click()
        capture.settle(page)
        state = page.evaluate("() => [document.querySelector('h2.tabbed .tabline > button.on')?.textContent, location.search]")
        check("뉴스 상세에서 뒤로 가면 종목 뉴스 탭을 고른 리포트 화면으로 돌아온다", state == ["종목 뉴스", f"?r={NASDAQ}"], str(state))
        run.close()

        # 뉴스 상세의 모양
        page = run.open(f"?r={NASDAQ}&news={fixtures.news()[0]['id']}")
        found = page.evaluate(PAGE)
        check("뉴스 상세는 제목, 종목 스티커, 그림, 이슈 해설 말머리, 소제목, 그래프 카드, 용어 밑줄을 그리고 머리 줄은 그리지 않는다",
              found["title"] == TITLES[0] and found["tickers"] == ["엔비디아"] and found["bar"] == TITLES[0] and found["photos"] == 2
              and found["mark"] == "이슈 해설" and found["headline"] == "" and found["h5"] == ["공급사 수율이 오른 덕분", "주가는 장 마감 뒤 올라"]
              and found["charts"] == 1 and found["terms"] == 1 and found["prev"] is None and found["next"] == TITLES[1], str(found))
        page.screenshot(path=str(shots / "news-detail.png"))
        run.close()

        # 종목 상세의 주요뉴스와 그 종목 목록의 다음 기사
        page = run.open(f"?r={NASDAQ}&stock=NVDA")
        order = page.evaluate("() => [...document.querySelectorAll('#report > h2')].map((h) => h.textContent.trim())")
        check("주요뉴스 절은 공시 상세 절 위에 있다", order[-2:] == ["주요뉴스", "공시 상세"], str(order))
        rows = page.evaluate(ROWS)
        check("주요뉴스 절에는 기사 제목이 세 개 보인다", rows == NVDA[:3], " | ".join(rows))
        capture.top(page, page.locator("#report > h2", has_text="주요뉴스"), 60)
        page.screenshot(path=str(shots / "stock-headlines.png"))
        page.locator(".headlines button.unfold").click()
        capture.settle(page, 400)
        rows = page.evaluate(ROWS)
        check("주요뉴스 절을 펼치면 기사 제목이 열 개 보인다", rows == NVDA, f"{len(rows)}개")
        page.locator(".headlines .entry", has_text=NVDA[1]).click()
        capture.settle(page)
        found = page.evaluate(PAGE)
        check("종목 상세에서 연 뉴스 상세의 다음 기사는 그 종목의 다음 기사다", found["title"] == NVDA[1] and found["prev"] == NVDA[0] and found["next"] == NVDA[2], str(found))
        page.locator(".issue-page.on nav.step button.next").click()
        capture.settle(page)
        moved = page.evaluate(PAGE)
        check("다음 기사 칸을 누르면 그 기사로 넘기고 주소의 기사 ID를 바꾼다", moved["title"] == NVDA[2] and moved["bar"] == NVDA[2] and moved["next"] == NVDA[3]
              and f"news={fixtures.news()[4]['id']}" in moved["search"] and "ticker=NVDA" in moved["search"], str(moved))
        page.locator("button.back").click()
        capture.settle(page)
        state = page.evaluate("() => [location.search, document.querySelectorAll('.headlines .entry').length]")
        check("종목 상세에서 연 뉴스 상세에서 뒤로 가면 종목 상세로 돌아온다", state[0] == f"?r={NASDAQ}&stock=NVDA" and state[1] == 10, str(state))
        run.close()

        check("페이지 오류와 바깥 요청이 없다", not server.errors and not server.escaped, f"{server.errors[:3]} {server.escaped[:3]}")

        # Worker 무응답. 요청을 abort하므로 브라우저가 적는 요청 실패 로그는 오류로 세지 않는다.
        server.news_down = True
        page = open_news(run, NASDAQ)
        empty = page.evaluate("() => document.querySelector('.news-box .empty')?.textContent")
        check("Worker가 응답하지 않으면 종목 뉴스 탭에 빈 상태 문구가 보인다", empty == "종목 뉴스를 불러오지 못했다.", str(empty))
        page.locator("h2.tabbed .tabline > button", has_text="상세 이슈 해설").click()
        capture.settle(page, 400)
        picks = page.locator(".issue-list .pick").filter(visible=True).count()
        check("Worker가 응답하지 않아도 상세 이슈 해설 탭은 그대로 보인다", picks > 0, f"이슈 상자 {picks}개")
        run.close()
        page = run.open(f"?r={NASDAQ}&stock=NVDA")
        empty = page.evaluate("() => document.querySelector('.headlines .empty')?.textContent")
        check("Worker가 응답하지 않으면 주요뉴스 절에 빈 상태 문구가 보인다", empty == "주요뉴스를 불러오지 못했다.", str(empty))
        run.close()
        browser.close()
    print(f"{len(FAILS)} FAIL" if FAILS else "ALL PASS", f"· 스크린숏 {shots}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
