"""내 투자 그림(U3)의 동작 시험. 단추 순서, 지난 날짜를 골랐을 때의 '현재' 점, 1분 값이 큰 값과 마지막 점을 바꾸는지 연다.

    python3 tests/golden/asset_tab.py --shots /tmp/at-u3

화면 값은 모두 지어낸 값이다. 계좌 요약은 `fixtures.account()`에 최신 날짜 지점의 1분 값(`returns.now`)을 더한 값이다.
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import capture
import fixtures

FAILS = []
NOW_COLOR = "#FF9F1C"
CARDS = ".carousel.asset-cards"


def check(name: str, ok: bool, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILS.append(name)


def sample() -> dict:
    """최신 날짜 지점의 1분 값을 더한 계좌 요약. 마지막 거래일 다음 평일이 최신 날짜 지점이다."""
    account = fixtures.account()
    for sector in account["performance"]["sectors"].values():
        ret = sector["returns"]
        day = dt.date.fromisoformat(ret["days"][-1])
        day += dt.timedelta(days=3 if day.weekday() == 4 else 1)
        ret["now"] = {"day": day.isoformat(), "anchor": ret["anchor"][-1] + 0.004, "realized": ret["realized"][-1] + 0.006}
    return account


def read(page, card: int) -> dict:
    """카드 하나의 큰 값, 집행 선(주황)의 마지막 점, '현재' 점의 가로 위치를 읽는다."""
    return page.evaluate("""([cards, i, color]) => {
      const slide = document.querySelectorAll(cards + ' .slide')[i];
      const path = [...slide.querySelectorAll('svg path')].filter((p) => p.getAttribute('stroke') === color).pop();
      const points = path ? path.getAttribute('d').slice(1).split('L') : [];
      const mark = slide.querySelector('svg circle');
      return { value: slide.querySelector('.val')?.textContent ?? null, last: points.at(-1) ?? null, count: points.length,
               mark: mark ? [+mark.getAttribute('cx'), +mark.getAttribute('cy')] : null };
    }""", [CARDS, card, NOW_COLOR])


def tab(page, i):
    page.locator(f"{CARDS} .tabs button").nth(i).click()
    capture.settle(page, 500)


def drag_back(page, steps: int):
    """기준 날짜 레버를 잡아 왼쪽으로 `steps` 칸 옮긴다."""
    page.locator(f"{CARDS} .rewind .open").first.click()
    capture.settle(page, 300)
    box = page.locator(f"{CARDS} .rewind .grip").first.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    for step in range(1, steps):
        page.mouse.move(x - step * 2, y)
        page.wait_for_timeout(30)
    page.mouse.up()
    capture.settle(page, 600)
    return page.locator(f"{CARDS} .rewind > span").first.text_content()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", default="")
    args = parser.parse_args()
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    account = sample()
    server = capture.Server(capture.REPO, capture.REPO)
    with sync_playwright() as p:
        browser = capture.launch(p)
        context = browser.new_context(viewport={"width": 390, "height": 1000}, device_scale_factor=1, reduced_motion="reduce",
                                      locale="ko-KR", timezone_id="Asia/Seoul", has_touch=True)
        context.clock.set_fixed_time(fixtures.NOW)
        context.add_init_script(capture.mock(1))
        context.add_init_script("try { localStorage.setItem('asset', '1'); } catch {}")
        context.route("**/*", server.handler({}, account))
        page = context.new_page()
        page.on("pageerror", lambda e: server.errors.append(f"pageerror: {str(e)[:300]}"))
        page.on("console", lambda m: m.type == "error" and server.errors.append(f"console: {m.text[:300]}"))
        page.goto(capture.APP, wait_until="networkidle")
        capture.settle(page)
        capture.turn(page, "자산")

        names = page.locator(f"{CARDS} .tabs button").all_text_contents()
        check("A2 단추 순서", names == ["누적 수익률", "초과 수익률", "배율"], names)

        tab(page, 0)
        latest = read(page, 0)
        check("A3 최신 날짜는 마지막 점이 1분 값", latest["count"] == len(account["performance"]["sectors"]["nasdaq"]["returns"]["days"]) + 1, latest)
        if shots:
            page.locator(CARDS).screenshot(path=str(shots / "latest.png"))

        label = drag_back(page, 40)
        past = read(page, 0)
        check("A3 지난 날짜를 골라도 선의 마지막 값은 그대로", past["last"] == latest["last"] and past["count"] == latest["count"], [label, past, latest])
        check("A3 지난 날짜는 '현재' 점만 옮긴다", past["mark"] is not None and latest["mark"] is not None and past["mark"][0] < latest["mark"][0], [past["mark"], latest["mark"]])
        check("A3 지난 날짜의 큰 값이 바뀐다", past["value"] != latest["value"], [past["value"], latest["value"]])
        if shots:
            page.locator(CARDS).screenshot(path=str(shots / "past.png"))

        # 1분 값: 지난 날짜를 고른 채 두면 큰 값이 그 날짜 값이라, 다시 열어 최신 날짜로 읽는다.
        page.reload(wait_until="networkidle")
        capture.settle(page)
        capture.turn(page, "자산")
        tab(page, 0)
        before = read(page, 0)
        ret = account["performance"]["sectors"]["nasdaq"]["returns"]
        ret["now"]["realized"] += 0.02
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        capture.settle(page, 800)
        after = read(page, 0)
        check("A4 1분 값이 큰 값을 바꾼다", after["value"] != before["value"], [before["value"], after["value"]])
        check("A4 1분 값이 마지막 점을 바꾼다", after["last"] != before["last"], [before["last"], after["last"]])
        browser.close()
    check("화면 오류 없음", not server.errors, server.errors[:3])
    print("FAILED" if FAILS else "OK", FAILS)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
