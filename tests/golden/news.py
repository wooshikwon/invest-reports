"""종목 뉴스 화면의 동작 시험. 리포트 화면의 "주요 이슈 해설 | 종목별 뉴스" 탭, 뉴스 상세, 종목 상세의 주요 뉴스 절을 `fixtures.NEWS`의 SAMPLE 기사로 연다.

    python3 tests/golden/news.py --data ~/repos/invest-reports-news --shots /tmp/sn-u8/shots

`--data`는 2026-11-19 나스닥·바이오 리포트와 `r/market.json` 지도, `r/stocks/NVDA.json`이 있는 리포트 자료다. 기사 그림은 그 자료의 `r/stocks/{종목}-{순번}.webp`를 쓴다.
뉴스 Worker 응답은 `capture.Server`가 `fixtures.news_answer`로 지어내고, 무응답은 `Server.news_down`으로 요청을 abort해 만든다.
화면 시각은 `fixtures.NOW`(11/19 23:45 KST)다. 기대값은 SAMPLE 기사의 회차 시작 시각으로 손으로 셈한 제목이다.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import capture
import fixtures

NASDAQ = "20261119-nasdaq"
BIOTECH = "20261119-biotech"
TITLES = [title for _, _, _, title, _ in fixtures.NEWS]
# 나스닥 리포트의 종목별 뉴스 목록에 오는 최신 회차(11/19 18:00) 기사 제목을 첫 종목의 변동률 순서로 적는다.
NASDAQ_LATEST = [TITLES[k] for k in (18, 0, 19, 20, 1, 21, 22)]
# 나스닥 기사 전체를 늦은 회차부터 적는다. 최신 회차 뒤의 회차는 회차마다 기사가 한 편이다.
NASDAQ_ALL = NASDAQ_LATEST + [title for _, _, title in sorted(((name, k, title) for k, (name, index, _, title, _) in enumerate(fixtures.NEWS)
                                                                     if index == "nasdaq" and name != fixtures.NEWS_ROUND), key=lambda row: (row[0], -row[1]), reverse=True)]
# 종목별 뉴스 목록 칸의 차례. 날짜 구분선은 "day:{날짜}", 기사는 "pick:{제목}:{위 선 두께}"다.
ORDER = """(box) => [...box.querySelector('.issue-list').children].map((n) => n.matches('.day-line') ? `day:${n.textContent}`
  : `pick:${n.querySelector('h3').textContent}:${getComputedStyle(n).borderTopWidth}`)"""
WEEKDAY = "월화수목금토일"


def day_label(title: str) -> str:
    """SAMPLE 기사 제목의 회차 날짜를 "11월 19일 (목)"으로 쓴다."""
    name = next(name for name, _, _, found, _ in fixtures.NEWS if found == title)
    day = dt.date.fromisoformat(name[:10])
    return f"{day.month}월 {day.day}일 ({WEEKDAY[day.weekday()]})"


def expected_order(titles: list[str]) -> list[str]:
    """제목 차례대로 놓은 목록의 칸 차례. 첫 날짜 뒤 날짜가 바뀌는 자리에 날짜 구분선이 오고, 첫 기사와 구분선 바로 아래 기사는 위 선이 없다."""
    out, last = [], None
    for title in titles:
        day = day_label(title)
        if last and day != last:
            out.append(f"day:{day}")
        out.append(f"pick:{title}:{'0px' if day != last else '1px'}")
        last = day
    return out
BIOTECH_TITLES = [title for name, index, _, title, _ in fixtures.NEWS if index == "biotech"]
# NVDA를 단 기사 제목을 최신순으로 적는다. 11월 기사 열한 편 뒤에 10월 기사 스무 편이 온다.
NVDA = [TITLES[k] for k in (0, 2, 4, 6, 8, 9, 10, 11, 12, 13, 14)] + [f"엔비디아 10월 {day}일 SAMPLE 기사" for day in range(20, 0, -1)]
FAILS = []

LIST = "() => [...document.querySelectorAll('.news-box .pick h3')].filter((h) => h.offsetParent).map((h) => h.firstChild.textContent.trim())"
# 목록 블록마다 그림이 있는지와 글 칸의 자식 차례.
BLOCKS = """() => [...document.querySelectorAll('.news-box .pick')].filter((pick) => pick.offsetParent).map((pick) => [!!pick.querySelector('img'),
  [...pick.querySelector('.text').children].map((n) => n.matches('img.cover') ? 'image' : n.matches('h3') ? 'title' : n.matches('p') ? 'headline' : n.matches('.age') ? 'age' : n.tagName)])"""
# 주요 뉴스 절에서 화면 안에 보이는 장의 기사 제목과 번호 줄(보이는 번호, 고른 번호, 앞·다음 꺾쇠를 누를 수 있는지).
ROWS = "() => [...document.querySelectorAll('.headlines .pick h3')].filter((h) => { const r = h.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; }).map((h) => h.textContent.trim())"
PAGER = """() => { const pager = document.querySelector('.headlines .pager'); return pager && { numbers: [...pager.querySelectorAll('.numbers button')].map((b) => b.textContent),
  on: pager.querySelector('.numbers button.on')?.textContent, prev: !pager.querySelector('.prev').disabled, next: !pager.querySelector('.next').disabled }; }"""
BAR = """() => { const bar = document.querySelector('h2.tabbed .bar').getBoundingClientRect(), on = document.querySelector('h2.tabbed .tabline > button.on');
  const box = on.getBoundingClientRect(); return { tab: on.textContent, bar: [bar.left, bar.width, bar.bottom], on: [box.left, box.width, box.bottom] }; }"""
# 보이는 뉴스 상세 문단. 제목, 제목 안의 종목 스티커(없어야 한다), 소제목 줄과 그 글자 굵기, 제목·소제목 줄·그림·말머리의 차례, 그림 수, 이슈 해설 말머리 뒤 글(비어야 한다), 본문 소제목,
# 그려진 그래프 카드 수, 용어 단추 수, 이전·다음 칸 제목.
PAGE = """() => { const page = document.querySelector('.issue-page.on'), h3 = page.querySelector(':scope > h3'), lead = page.querySelector(':scope > h4');
  const cell = (side) => page.querySelector(`nav.step .${side} .title`)?.textContent.trim() ?? null;
  const lines = [...page.querySelectorAll(':scope > ul.subheads > li')];
  const order = [...page.children].map((n) => n.matches('h3') ? 'h3' : n.matches('ul.subheads') ? 'subheads' : n.matches('figure.issue-image') ? 'image' : n.matches('h4') ? 'h4' : null).filter(Boolean);
  return { title: h3.firstChild.textContent.trim(), tickers: [...h3.querySelectorAll('code')].map((c) => c.textContent), bar: document.getElementById('issue-bar').textContent,
    subheads: lines.map((li) => li.textContent), weights: lines.map((li) => getComputedStyle(li).fontWeight), order,
    photos: page.querySelectorAll(':scope > figure.issue-image figure.photo').length, photo: page.querySelector(':scope > figure.issue-image img')?.getAttribute('src'), mark: lead?.querySelector('mark')?.textContent,
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
    page.locator("h2.tabbed .tabline > button", has_text="종목별 뉴스").click()
    capture.settle(page, 800)
    return page


def swipe(page, dx, x0=None):
    """상세 이슈 해설 절의 탭 줄 아래를 손가락으로 가로로 민다(CDP 터치 이벤트). `dx`가 음수이면 왼쪽으로 민다. `x0`를 주면 그 자리에서 시작한다."""
    box = page.locator("h2.tabbed").first.bounding_box()
    x0, y = 195 - dx / 2 if x0 is None else x0, box["y"] + box["height"] + 60
    cdp = page.context.new_cdp_session(page)
    point = lambda x: [{"x": x, "y": y, "id": 1}]
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": point(x0)})
    for i in range(1, 11):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": point(x0 + dx * i / 10)})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    capture.settle(page, 600)


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

        # 머리 상자의 지수 드롭다운과 지수 페이지 이름
        page = run.open(f"?r={NASDAQ}")
        capture.turn(page, "지수")
        head = page.evaluate("() => [document.getElementById('page-name').textContent, document.querySelector('.index-pick').textContent, document.querySelector('.index-menu').hidden]")
        check("지수 페이지의 이름은 지수이고, 지수 단추는 지금 지수 이름을 쓴 알약이며 메뉴는 닫혀 있다", head == ["지수", "나스닥", True], str(head))
        page.locator(".index-pick").click()
        menu = page.evaluate("() => [...document.querySelectorAll('.index-menu .item')].map((item) => [item.querySelector('.name').textContent, item.querySelector('.sub').textContent, !!item.querySelector('.check')])")
        check("지수 단추를 누르면 지수마다 이름과 전체 이름을 쓴 메뉴를 펼치고 지금 지수에 체크를 단다",
              menu == [["나스닥", "나스닥 100", True], ["바이오", "나스닥 바이오테크", False]] and page.locator(".index-menu").is_visible(), str(menu))
        lefts = page.evaluate("() => [...document.querySelectorAll('.index-menu .item')].map((item) => ['.name', '.sub'].map((q) => Math.round(item.querySelector(q).getBoundingClientRect().left)))")
        check("메뉴 줄마다 지수 이름끼리, 지수 전체 이름끼리 왼쪽 끝이 같다", len(lefts) == 2 and lefts[0] == lefts[1], str(lefts))
        page.screenshot(path=str(shots / "index-menu.png"))
        page.mouse.click(30, 500)
        capture.settle(page, 300)
        check("메뉴 밖을 누르면 메뉴를 닫는다", not page.locator(".index-menu").is_visible())
        page.locator(".index-pick").click()
        page.locator(".index-menu .item", has_text="바이오").click()
        capture.settle(page, 1200)
        moved = page.evaluate("() => [location.search, document.querySelector('.index-pick').textContent]")
        check("메뉴에서 다른 지수를 고르면 그 지수의 리포트를 연다", "biotech" in moved[0] and moved[1] == "바이오", str(moved))
        run.close()

        # 탭 줄과 막대, 지수별 목록, 큰 블록
        page = run.open(f"?r={NASDAQ}")
        capture.turn(page, "이슈")
        before = page.evaluate(BAR)
        page.locator("h2.tabbed .tabline > button", has_text="종목별 뉴스").click()
        capture.settle(page, 800)
        after = page.evaluate(BAR)
        check("처음에는 상세 이슈 해설 탭을 고르고 막대가 그 탭 아래에 있다", before["tab"] == "주요 이슈 해설" and near(before["bar"][:2], before["on"][:2]), str(before))
        check("탭을 바꾸면 막대가 고른 탭 아래로 옮겨 간다", after["tab"] == "종목별 뉴스" and near(after["bar"][:2], after["on"][:2])
              and after["bar"][0] > before["bar"][0] + 20, str(after))
        hidden = page.evaluate("() => [document.querySelector('.issue-box').hidden, document.querySelector('.news-box').hidden]")
        check("종목 뉴스 탭은 이슈 목록을 감추고 기사 목록을 보인다", hidden == [True, False], str(hidden))
        shown = page.evaluate(LIST)
        check("나스닥 리포트는 첫 장에 나스닥 기사 열 편을 늦은 회차부터, 같은 회차 안에서는 첫 종목의 변동률 순서로 보인다", shown == NASDAQ_ALL[:10], " | ".join(shown))
        check("나스닥 리포트에서 바이오 종목 기사가 보이지 않는다", not set(shown) & set(BIOTECH_TITLES))
        blocks = page.evaluate(BLOCKS)
        check("기사 블록은 그림 없이 제목, 머리 줄, 회차 시각 차례다", blocks == [[False, ["title", "headline", "age"]]] * len(shown), str(blocks))
        moves = page.evaluate("""() => [...document.querySelectorAll('.news-box .pick')].filter((pick) => pick.offsetParent).map((pick) => {
          const age = pick.querySelector('.age'), move = age.querySelector('.move');
          return move ? [move.textContent, Math.round(age.getBoundingClientRect().right - move.getBoundingClientRect().right), getComputedStyle(move).color] : null; })""")
        check("기사 아래 줄 오른쪽 끝에 첫 종목의 변동률을 회색 '변동률 지수 : N%'로 쓰고, 변동률이 없는 기사는 쓰지 않는다",
              [m and m[0] for m in moves] == ["변동률 지수 : 6.50%", "변동률 지수 : 4.10%", "변동률 지수 : 3.00%", "변동률 지수 : 3.00%", "변동률 지수 : 1.20%",
                                             "변동률 지수 : 0.80%", None, None, None, None] and all(m[1] == 0 for m in moves if m), str(moves))
        parts = page.evaluate("() => ['.news-box .pick', '.news-box .pick code', '.news-box .pick .thumb', '.news-box .pick .age'].map((q) => document.querySelectorAll(q).length)")
        stickers = page.evaluate("() => [...document.querySelectorAll('.news-box .pick .age')].map((age) => [age.firstChild.textContent, [...age.querySelectorAll('.ticker')].map((t) => t.textContent)])")
        expected = [next(list(tickers) for _, _, tickers, title, _ in fixtures.NEWS if title == shown_title) for shown_title in shown]
        lead = page.locator(".news-box .pick", has_text=TITLES[0]).locator(".text > p").text_content()
        check("목록 블록의 머리 줄은 첫 소제목이다", lead == fixtures.NEWS_SUBHEADS[0], str(lead))
        check("기사 블록마다 회차 시각이 있고 제목 스티커와 썸네일은 없다", parts[1] == parts[2] == 0 and parts[3] == parts[0] > 0, str(parts))
        check("회차 시각 오른쪽에 기사가 다룬 종목마다 티커 스티커가 있다",
              [found for _, found in stickers] == expected and all(re.fullmatch(r"\d{1,2}/\d{1,2} \d\d:\d\d", clock) for clock, _ in stickers), str(stickers))
        asof = page.evaluate("() => document.querySelector('h2.tabbed + .issue-asof')?.textContent.trim()")
        found = re.fullmatch(r"마지막 업데이트 (\d{1,2})/(\d{1,2}) \((.)\) \d\d:\d\d KST", asof or "")
        check("주요 이슈 해설 탭 첫 줄의 마지막 업데이트 시각에 그 날짜의 요일이 붙는다",
              bool(found) and "월화수목금토일"[dt.date(2026, int(found.group(1)), int(found.group(2))).weekday()] == found.group(3), str(asof))
        stamp = page.evaluate("() => document.querySelector('.news-box > .issue-asof')?.textContent")
        check("종목 뉴스 탭 첫 줄에 가장 최근 회차의 요일을 붙인 마지막 업데이트 시각이 있다", stamp == "마지막 업데이트 11/19 (목) 18:00 KST", str(stamp))
        news = page.locator(".news-box").filter(visible=True).first
        order = news.evaluate(ORDER)
        check("목록은 맨 위가 아닌, 회차 날짜가 바뀌는 자리에만 날짜 구분선을 두고, 구분선 바로 아래 기사에는 위 선이 없다",
              order == expected_order(NASDAQ_ALL[:10]), " | ".join(order))
        check("첫 장 열 편 아래에 더 보기 단추가 있다", news.locator(".more").is_visible())
        page.evaluate("scrollTo(0, 0)")
        capture.settle(page, 300)
        page.screenshot(path=str(shots / "news-tab.png"))
        news.locator(".more").click()
        capture.settle(page, 800)
        shown = page.evaluate(LIST)
        check("더 보기를 누르면 다음 열 편이 목록 아래에 이어 붙는다", shown == NASDAQ_ALL[:20] and news.evaluate(ORDER) == expected_order(NASDAQ_ALL[:20]), " | ".join(shown))
        news.locator(".more").click()
        capture.settle(page, 800)
        news.locator(".more").click()
        capture.settle(page, 800)
        shown = page.evaluate(LIST)
        check("기사를 모두 받으면 더 보기 단추가 사라진다", shown == NASDAQ_ALL and not news.locator(".more").is_visible(), f"{len(shown)}편")
        page.locator(".news-box .pick", has_text=NASDAQ_ALL[12]).click()
        capture.settle(page)
        found = page.evaluate(PAGE)
        check("더 보기로 받은 기사의 뉴스 상세 앞뒤 기사는 그 기사가 든 열 편 안의 앞뒤 기사다", found["prev"] == NASDAQ_ALL[11] and found["next"] == NASDAQ_ALL[13], str(found))
        page.locator("button.back").click()
        capture.settle(page)
        page.locator("h2.tabbed .tabline > button", has_text="종목별 뉴스").click()
        capture.settle(page, 1200)
        check("뉴스 상세에서 돌아와 종목별 뉴스 탭을 열면 떠나기 전에 받은 만큼 기사를 보인다", page.evaluate(LIST) == NASDAQ_ALL, f"{len(page.evaluate(LIST))}편")
        page.locator("h2.tabbed .tabline > button", has_text="주요 이슈 해설").click()
        capture.settle(page, 600)
        back = page.evaluate(BAR)
        check("상세 이슈 해설 탭으로 돌아오면 막대도 돌아온다", back["tab"] == "주요 이슈 해설" and near(back["bar"][:2], before["bar"][:2]), str(back))
        # 절 안에서 가로로 밀면 탭을 넘긴다
        swipe(page, -160)
        check("절 안에서 왼쪽으로 밀면 종목 뉴스 탭으로 넘어간다", page.evaluate(BAR)["tab"] == "종목별 뉴스", page.evaluate(BAR))
        swipe(page, 160)
        check("절 안에서 오른쪽으로 밀면 상세 이슈 해설 탭으로 돌아온다", page.evaluate(BAR)["tab"] == "주요 이슈 해설", page.evaluate(BAR))
        # 화면 좌우 끝에서 밀면 바로가기 탭을 넘기고, 절 안의 탭은 넘기지 않는다
        swipe(page, -160, 382)
        on = page.evaluate("() => document.querySelector('nav.jump button.on')?.textContent")
        check("오른쪽 끝에서 왼쪽으로 밀면 다음 바로가기 탭(시장)을 연다", on == "시장" and page.evaluate(BAR)["tab"] == "주요 이슈 해설", on)
        swipe(page, 160, 8)
        on = page.evaluate("() => document.querySelector('nav.jump button.on')?.textContent")
        check("왼쪽 끝에서 오른쪽으로 밀면 앞 바로가기 탭(이슈)으로 돌아온다", on == "이슈" and page.evaluate(BAR)["tab"] == "주요 이슈 해설", on)
        run.close()

        # 적힌 탭이 없는 가장 늦은 리포트는 분석 완료 시각과 가장 최근 회차 시각 가운데 늦은 쪽의 탭으로 연다.
        listing = json.loads((Path(args.data) / "r" / "index.json").read_text(encoding="utf-8"))
        latest = max(key for key, entry in listing.items() if key.endswith("-nasdaq") and isinstance(entry, dict))
        page = run.open(f"?r={latest}")
        capture.turn(page, "이슈")
        capture.settle(page, 600)
        check("분석 완료 시각이 최근 회차보다 늦으면 상세 이슈 해설 탭으로 연다", page.evaluate(BAR)["tab"] == "주요 이슈 해설", listing[latest]["written"])
        # 분석 완료 시각을 SAMPLE 기사의 가장 최근 회차(11/19 18:00 KST)보다 이르게 바꾼 목록으로 다시 연다.
        earlier = {**listing, latest: {**listing[latest], "written": "2026-11-19 10:00"}}
        page.route("**/r/index.json*", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(earlier)))
        page.evaluate("history.replaceState(null, '')")  # 미니 앱을 새로 연 것처럼 적힌 탭을 지운다
        page.reload(wait_until="networkidle")
        capture.settle(page)
        capture.turn(page, "이슈")
        capture.settle(page, 600)
        auto = page.evaluate(BAR)
        check("최근 회차가 분석 완료 시각보다 늦으면 종목 뉴스 탭으로 연다", auto["tab"] == "종목별 뉴스" and near(auto["bar"][:2], auto["on"][:2]), str(auto))
        run.close()

        page = open_news(run, BIOTECH)
        found = page.evaluate("""() => { const box = [...document.querySelectorAll('.news-box')].find((node) => node.offsetParent);
          return [[...box.querySelectorAll('.pick h3')].map((h) => h.textContent), !!box.querySelector('.more:not([hidden])'), box.querySelector(':scope > .issue-asof')?.textContent]; }""")
        check("바이오 리포트는 지난 회차의 바이오 기사도 늦은 회차부터 보이고, 남은 기사가 없으면 더 보기 단추가 없으며, 마지막 업데이트는 최신 회차 시각이다",
              found == [BIOTECH_TITLES, False, "마지막 업데이트 11/19 (목) 18:00 KST"], str(found))
        run.close()

        # 종목 뉴스 탭에서 연 뉴스 상세
        page = open_news(run, NASDAQ)
        page.locator(".news-box .pick", has_text=NASDAQ_LATEST[2]).click()
        capture.settle(page)
        found = page.evaluate(PAGE)
        check("종목 뉴스 탭에서 연 뉴스 상세의 앞뒤 기사는 지수 목록의 앞뒤 기사다",
              found["title"] == NASDAQ_LATEST[2] and found["prev"] == NASDAQ_LATEST[1] and found["next"] == NASDAQ_LATEST[3], str(found))
        check("소제목 줄 없이 올린 기사의 뉴스 상세에는 소제목 목록이 없다", found["subheads"] == [] and found["order"] == ["h3", "image", "h4"], str(found["order"]))
        page.locator("button.back").click()
        capture.settle(page)
        state = page.evaluate("() => [document.querySelector('h2.tabbed .tabline > button.on')?.textContent, location.search]")
        check("뉴스 상세에서 뒤로 가면 리포트 화면의 처음 탭(상세 이슈 해설)으로 돌아온다", state == ["주요 이슈 해설", f"?r={NASDAQ}"], str(state))
        run.close()

        # 뉴스 상세의 모양
        page = run.open(f"?r={NASDAQ}&news={fixtures.news()[0]['id']}")
        found = page.evaluate(PAGE)
        check("뉴스 상세는 제목, 본문 그림 한 장, 이슈 해설 말머리, 소제목, 그래프 카드, 용어 밑줄을 그리고 종목 스티커와 머리 줄은 그리지 않는다",
              found["title"] == TITLES[0] and found["tickers"] == [] and found["bar"] == TITLES[0] and found["photos"] == 1 and found["photo"].endswith("sample-NVDA-1.webp")
              and found["mark"] == "이슈 해설" and found["headline"] == "" and found["h5"] == ["공급사 수율이 오른 덕분", "주가는 장 마감 뒤 올라"]
              and found["charts"] == 1 and found["terms"] == 1 and found["prev"] == NASDAQ_LATEST[0] and found["next"] == NASDAQ_LATEST[2], str(found))
        check("뉴스 상세는 제목 아래, 그림 위에 소제목 세 줄을 굵지 않은 불릿으로 그린다",
              found["subheads"] == fixtures.NEWS_SUBHEADS and found["order"] == ["h3", "subheads", "image", "h4"]
              and all(int(weight) < 600 for weight in found["weights"]), f"{found['order']} {found['weights']}")
        page.screenshot(path=str(shots / "news-detail.png"))
        capture.settle(page, 300)
        links = page.evaluate("() => [...document.querySelectorAll('.issue-page.on button.stock')].map((b) => [b.textContent, b.dataset.stock, b.parentElement.tagName, !!b.querySelector('svg.lens')])")
        check("본문에서 종목마다 처음 나오는 이름만 돋보기 단추로 감싸고, 제목·소제목과 다른 낱말 속 이름은 감싸지 않는다",
              links == [["엔비디아", "NVDA", "P", True], ["AMD", "AMD", "P", True], ["인텔", "INTC", "P", True]], str(links))
        capture.top(page, page.locator(".issue-page.on button.stock[data-stock='AMD']"), 200)
        page.screenshot(path=str(shots / "news-stock-links.png"))
        page.locator(".issue-page.on button.stock[data-stock='AMD']").click()
        capture.settle(page, 800)
        opened = page.evaluate("() => [location.search, document.querySelector('#report .stock-name, #report h2')?.textContent ?? '']")
        check("종목 이름 단추를 누르면 그 종목의 종목 상세를 연다", "stock=AMD" in opened[0], str(opened))
        run.close()

        # 종목 상세의 주요 뉴스와 그 종목 목록의 다음 기사
        page = run.open(f"?r={NASDAQ}&stock=NVDA")
        order = page.evaluate("() => [...document.querySelectorAll('#report > h2')].map((h) => h.textContent.trim())")
        check("주요 뉴스 절은 공시 상세 절 위에 있다", order[-2:] == ["주요 뉴스", "공시 상세"], str(order))
        rows = page.evaluate(ROWS)
        blocks = page.evaluate("""() => [document.querySelectorAll('.headlines .history, .headlines .unfold').length,
          [...document.querySelector('.headlines .pick .text').children].map((n) => n.tagName), document.querySelectorAll('.headlines .move, .headlines .ticker').length]""")
        check("주요 뉴스 절은 상자와 펼치기 없이 제목과 회차 시각만 쓴 블록을 첫 장에 다섯 편 쓴다",
              rows == NVDA[:5] and blocks == [0, ["H3", "DIV"], 0], f"{' | '.join(rows)} {blocks}")
        check("번호 줄은 1~5를 보이고 1을 고르며 앞 꺾쇠는 누를 수 없다",
              page.evaluate(PAGER) == {"numbers": ["1", "2", "3", "4", "5"], "on": "1", "prev": False, "next": True}, str(page.evaluate(PAGER)))
        capture.top(page, page.locator("#report > h2", has_text="주요 뉴스"), 60)
        page.screenshot(path=str(shots / "stock-headlines.png"))
        tall = page.evaluate("() => document.querySelector('.headlines .carousel').offsetHeight")
        page.locator(".headlines .pager .next").click()
        capture.settle(page, 900)
        check("다음 꺾쇠를 누르면 둘째 장의 다섯 편으로 넘긴다", page.evaluate(ROWS) == NVDA[5:10] and page.evaluate(PAGER)["on"] == "2", str(page.evaluate(PAGER)))
        page.locator(".headlines .pager .numbers button", has_text="5").click()
        capture.settle(page, 900)
        pager = page.evaluate(PAGER)
        check("번호를 누르면 그 장으로 넘기고, 번호 줄은 고른 장을 가운데에 둔 다섯 개를 보인다",
              page.evaluate(ROWS) == NVDA[20:25] and pager == {"numbers": ["3", "4", "5", "6", "7"], "on": "5", "prev": True, "next": True}, str(pager))
        page.evaluate("(() => { const track = document.querySelector('.headlines .carousel .track'); track.scrollLeft = track.scrollWidth; })()")
        capture.settle(page, 900)
        pager = page.evaluate(PAGER)
        check("마지막 장까지 밀어 넘기면 남은 한 편이 보이고 다음 꺾쇠는 누를 수 없다",
              page.evaluate(ROWS) == NVDA[30:] and pager == {"numbers": ["3", "4", "5", "6", "7"], "on": "7", "prev": True, "next": False}, str(pager))
        last = page.evaluate("() => document.querySelector('.headlines .carousel').offsetHeight")
        check("기사가 한 편뿐인 마지막 장으로 넘겨도 주요 뉴스 묶음의 높이가 줄지 않는다", last == tall and tall > 0, f"첫 장 {tall}px, 마지막 장 {last}px")
        page.locator(".headlines .pager .numbers button", has_text="3").click()
        capture.settle(page, 900)
        page.locator(".headlines .pager .prev").click()
        capture.settle(page, 900)
        page.locator(".headlines .pager .prev").click()
        capture.settle(page, 900)
        page.locator(".headlines .pick", has_text=NVDA[1]).click()
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
        state = page.evaluate("() => [location.search, document.querySelectorAll('.headlines .pick').length]")
        check("종목 상세에서 연 뉴스 상세에서 뒤로 가면 종목 상세로 돌아온다", state[0] == f"?r={NASDAQ}&stock=NVDA" and state[1] == len(NVDA), str(state))
        run.close()

        check("페이지 오류와 바깥 요청이 없다", not server.errors and not server.escaped, f"{server.errors[:3]} {server.escaped[:3]}")

        # Worker 무응답. 요청을 abort하므로 브라우저가 적는 요청 실패 로그는 오류로 세지 않는다.
        server.news_down = True
        page = open_news(run, NASDAQ)
        empty = page.evaluate("() => document.querySelector('.news-box .empty')?.textContent")
        check("Worker가 응답하지 않으면 종목 뉴스 탭에 빈 상태 문구가 보인다", empty == "종목 뉴스를 불러오지 못했다.", str(empty))
        page.locator("h2.tabbed .tabline > button", has_text="주요 이슈 해설").click()
        capture.settle(page, 400)
        picks = page.locator(".issue-list .pick").filter(visible=True).count()
        check("Worker가 응답하지 않아도 상세 이슈 해설 탭은 그대로 보인다", picks > 0, f"이슈 상자 {picks}개")
        run.close()
        page = run.open(f"?r={NASDAQ}&stock=NVDA")
        empty = page.evaluate("() => document.querySelector('.headlines .empty')?.textContent")
        check("Worker가 응답하지 않으면 주요 뉴스 절에 빈 상태 문구가 보인다", empty == "주요 뉴스를 불러오지 못했다.", str(empty))
        run.close()
        browser.close()
    print(f"{len(FAILS)} FAIL" if FAILS else "ALL PASS", f"· 스크린숏 {shots}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
