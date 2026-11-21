"""내 투자 그림(U3)의 동작 시험. 단추 순서, 그림을 눌러 날짜를 골랐을 때의 '현재' 점, 1분 값이 큰 값과 마지막 점을 바꾸는지 연다.

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
NOW_COLOR = "#C9CDD3"
CARDS = ".carousel.asset-cards"


def check(name: str, ok: bool, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILS.append(name)


def sample() -> dict:
    """최신 날짜 지점의 1분 값을 더한 계좌 요약. 마지막 거래일 다음 평일이 최신 날짜 지점이다.
    Worker처럼 1분 값을 셈한 체결가 시각(`live.time`)을 요약 시각 30분 뒤로 적는다."""
    account = fixtures.account()
    account["live"] = {"time": (dt.datetime.fromisoformat(account["time"]) + dt.timedelta(minutes=30)).isoformat()}
    for sector in account["performance"]["sectors"].values():
        ret = sector["returns"]
        day = dt.date.fromisoformat(ret["days"][-1])
        day += dt.timedelta(days=3 if day.weekday() == 4 else 1)
        ret["now"] = {"day": day.isoformat(), "anchor": ret["anchor"][-1] + 0.004, "target": ret["target"][-1] + 0.005, "realized": ret["realized"][-1] + 0.006}
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


def tap_at(page, card: int, fraction: float):
    """카드 하나의 그림에서 가로 `fraction` 자리(0~1)를 누른다. 누른 뒤 카드가 다시 그려지길 기다린다."""
    box = page.locator(f"{CARDS} .slide").nth(card).locator("svg").first.bounding_box()
    page.mouse.click(box["x"] + box["width"] * fraction, box["y"] + box["height"] * 0.5)
    capture.settle(page, 400)


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

        # 총 자산 단추: 모든 보유 종목과 원화·달러 현금을 원화로 더한 값을 쓰고, 고른 상태를 기기에 남긴다.
        sum_text = lambda: page.locator(".asset-sum b:not(.veiled)").first.text_content()
        sector_sum = sum_text()
        page.locator(".asset-head .whole").click()
        capture.settle(page, 600)
        rate = account["rate"]
        won = lambda v, c: v * rate if c == "USD" else v
        expected = sum(won(it["value"], it["currency"]) for it in account["items"]) + sum(won(a["cash"], c) for c, a in account["accounts"].items())
        whole_sum = sum_text()
        check("A1 총 자산 단추를 켜면 모든 보유 종목과 현금의 합계를 쓴다",
              whole_sum != sector_sum and abs(int(whole_sum.replace(",", "").replace("원", "")) - round(expected)) <= 1, [sector_sum, whole_sum, round(expected)])
        page.reload(wait_until="networkidle")
        capture.settle(page)
        capture.turn(page, "자산")
        check("A1 총 자산 단추를 켠 상태가 다시 열어도 남는다", page.locator(".asset-head .whole.on").count() == 1 and sum_text() == whole_sum, sum_text())
        page.locator(".asset-head .whole").click()
        capture.settle(page, 600)
        check("A1 다시 누르면 보고 있는 지수 종목의 합계로 돌아간다", sum_text() == sector_sum, sum_text())

        # 판단 보기 단추: 두 수익률 카드의 판단 선(지수색)을 함께 감추고 보이며, 상태를 기기에 남긴다.
        judged = lambda: page.evaluate("""(cards) => [...document.querySelectorAll(cards + ' .slide')].slice(0, 2)
          .map((slide) => slide.querySelectorAll('svg path[stroke="url(#index-ink)"]').length)""", CARDS)
        check("A1 판단 선이 처음에는 보인다", judged() == [1, 1], judged())
        page.locator(f"{CARDS} .slide").first.locator("button.aim").click()
        capture.settle(page, 500)
        check("A1 판단 보기 단추를 끄면 두 카드의 판단 선이 함께 사라진다", judged() == [0, 0] and page.locator(f"{CARDS} button.aim.on").count() == 0, judged())
        check("A1 판단 보기 상태를 기기에 남긴다", page.evaluate("JSON.parse(localStorage.getItem('asset-view')).judge") is False)
        page.locator(f"{CARDS} .slide").first.locator("button.aim").click()
        capture.settle(page, 500)
        check("A1 다시 켜면 판단 선이 돌아온다", judged() == [1, 1], judged())

        names = page.locator(f"{CARDS} .tabs button").all_text_contents()
        check("A2 단추 순서", names == ["누적 수익률", "초과 수익률", "배율"], names)
        on = lambda: page.evaluate("(cards) => [...document.querySelectorAll(cards + ' .tabs button')].findIndex((b) => b.classList.contains('on'))", CARDS)
        tab(page, 2)
        capture.turn(page, "예측")
        capture.turn(page, "자산")
        check("A2 바로가기 탭을 옮기고 돌아오면 누적 수익률 카드로 돌아간다", on() == 0, on())
        tab(page, 2)
        page.reload(wait_until="networkidle")
        capture.settle(page)
        capture.turn(page, "자산")
        check("A2 다시 열면 누적 수익률 카드로 연다", on() == 0 and "card" not in page.evaluate("JSON.parse(localStorage.getItem('asset-view'))"), on())

        tab(page, 0)
        latest = read(page, 0)
        check("A3 최신 날짜는 마지막 점이 1분 값", latest["count"] == len(account["performance"]["sectors"]["nasdaq"]["returns"]["days"]) + 1, latest)
        if shots:
            page.locator(CARDS).screenshot(path=str(shots / "latest.png"))

        tap_at(page, 0, 0.3)
        past = read(page, 0)
        check("A3 그래프를 눌러도 선의 마지막 값은 그대로", past["last"] == latest["last"] and past["count"] == latest["count"], [past, latest])
        check("A3 누른 날짜로 '현재' 점만 옮긴다", past["mark"] is not None and latest["mark"] is not None and past["mark"][0] < latest["mark"][0], [past["mark"], latest["mark"]])
        check("A3 누른 날짜의 큰 값이 바뀐다", past["value"] != latest["value"], [past["value"], latest["value"]])
        tab(page, 1)
        other = read(page, 1)
        check("A3 초과 수익률 카드도 같은 날짜를 고른다", other["mark"] is not None and abs(other["mark"][0] - past["mark"][0]) < 0.01, [other["mark"], past["mark"]])
        if shots:
            page.locator(CARDS).screenshot(path=str(shots / "past.png"))
        tab(page, 0)
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        capture.settle(page, 800)
        kept = read(page, 0)
        check("A3 계좌 요약을 다시 그려도 고른 날짜를 유지한다", kept["value"] == past["value"] and kept["mark"] == past["mark"], [kept, past])
        tap_at(page, 0, 0.99)
        back = read(page, 0)
        check("A3 가장 늦은 점을 누르면 처음 상태로 돌아온다", back["value"] == latest["value"] and back["mark"] == latest["mark"], [back, latest])

        # 1분 값: 최신 점을 고른 상태로 읽는다.
        before = read(page, 0)
        clock = dt.datetime.fromisoformat(account["live"]["time"]).strftime("%H:%M")
        counts = page.evaluate("""(cards) => [...document.querySelectorAll(cards + ' .slide')[0].querySelectorAll('svg path')]
          .map((p) => [p.getAttribute('stroke'), p.getAttribute('d').split('L').length])""", CARDS)
        check("A4 판단 선도 최신 날짜 점까지 그린다", len({n for _, n in counts}) == 1 and len(counts) == 3, counts)
        stamp = page.evaluate("(cards) => document.querySelector(cards + ' .slide .top .kind')?.textContent", CARDS)
        check("A4 최신 날짜의 기준 시각은 체결가 시각", bool(stamp) and stamp.endswith(f"{clock} KST"), stamp)
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
