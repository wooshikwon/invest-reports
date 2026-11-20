"""날짜 지점 U4(리포트 화면)의 동작 시험. 판단 전과 후, 최신 날짜와 지난 날짜, 레버, 튕김 잠금, 판단 도착을 연다.

    python3 tests/golden/date_point.py --data /tmp/dp-u4/out --after /tmp/dp-u4/out-after --shots /tmp/dp-u4/shots

`--data`는 판단 전(가장 늦은 리포트가 날짜 지점 2026-11-19)의 리포트 자료이고, `--after`는 거기에 2026-11-20 판단을 더한 자료다.
실시간 값은 `fixtures.live(..., "closed")`에 날짜 지점 2026-11-20의 값을 더한 값이다. 화면 값은 모두 지어낸 값이다.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import capture
import fixtures

PENDING = "2026-11-20"
WHY = "아직 이전 정규장 분석이 완료되지 않았어요"
FAILS = []


def check(name: str, ok: bool, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILS.append(name)


def pending_live(data: Path) -> dict:
    live = fixtures.live(data, "closed")
    for index, found in json.loads((data / "r" / "market.json").read_text(encoding="utf-8"))["map"].items():
        live["afterhours"].setdefault(index, {})[fixtures.POINT] = {
            "time": "2026-11-19T16:50:00-05:00", "ratio": 1.002, "stocks": {}, "point": PENDING}
    live["progress"] = {"date": PENDING, "indexes": {index: {"step": 1, "since": "2026-11-20T06:50:00+09:00"} for index in live["premarket"]}, "plan": [0, 20, 60, 120]}
    return live


def overlay_after(after: Path) -> dict:
    """`after` 자료에서 판단이 도착하며 바뀌는 파일을 바이트로 읽는다."""
    paths = ["r/index.json", "r/rewind-nasdaq/cards.json"] + [f"r/20261120-nasdaq/{p.name}" for p in (after / "r" / "20261120-nasdaq").iterdir()]
    return {path: (after / path).read_bytes() for path in paths}


class World:
    def __init__(self, p, data: Path, overlay: dict, reloads: bool = False):
        self.server = capture.Server(capture.REPO, data)
        self.server.live = pending_live(data)
        self.overlay = dict(overlay)
        self.browser = capture.launch(p)
        self.context = self.browser.new_context(viewport={"width": 390, "height": 1000}, device_scale_factor=1, reduced_motion="reduce",
                                                locale="ko-KR", timezone_id="Asia/Seoul", has_touch=True)
        self.context.clock.set_fixed_time(fixtures.MOMENTS["closed"])
        self.context.add_init_script(capture.mock(1))
        self.context.route("**/*", self.server.handler(self.overlay, fixtures.account()))
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda e: self.server.errors.append(f"pageerror: {str(e)[:300]}"))
        self.page.on("console", lambda m: m.type == "error" and self.server.errors.append(f"console: {m.text[:300]}"))
        if reloads:
            self.page.add_init_script("window.__reloads = 0; try { Object.defineProperty(Location.prototype, 'reload', { value() { window.__reloads++; }, configurable: true }); } catch (e) {}")

    def open(self, query=""):
        self.page.goto(capture.APP + query, wait_until="networkidle")
        capture.settle(self.page)
        return self.page

    def close(self):
        self.context.close()
        self.browser.close()


def state(page):
    return page.evaluate("""() => ({
      date: document.querySelector('.carousel.cards .rewind span')?.textContent ?? null,
      notes: [...document.querySelectorAll('[data-point]')].map((n) => [n.dataset.point, n.hidden]),
      aim: (() => { const b = document.querySelector('button.aim'); return b && { disabled: b.disabled, on: b.classList.contains('on') }; })(),
      tab: [...document.querySelectorAll('.carousel.cards .tabs button')].findIndex((b) => b.classList.contains('on')),
      toast: document.querySelector('.toast')?.textContent ?? null,
      pill: document.querySelector('main')?.innerText.replace(/\\s+/g, ' ').slice(0, 160) ?? null,
    })""")


def to_cards(page):
    page.locator(".carousel.cards").first.scroll_into_view_if_needed()
    capture.settle(page, 300)


def open_lever(page):
    page.locator(".carousel.cards .rewind .open").first.click()
    capture.settle(page, 300)


def grip(page):
    box = page.locator(".carousel.cards .rewind .grip").first.bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def drag_to(page, label, hold=False, away=False):
    """레버를 잡고 날짜 이름표가 `label`이 될 때까지 왼쪽으로 옮긴다. `hold`이면 손을 떼지 않는다."""
    x, y = grip(page)
    page.mouse.move(x, y)
    page.mouse.down()
    seen = []
    for step in range(1, 160):
        page.mouse.move(x - step * 2, y)
        page.wait_for_timeout(30)
        now = page.locator(".carousel.cards .rewind > span").first.text_content()
        if not seen or seen[-1] != now:
            seen.append(now)
        if now == label:
            break
    if not hold:
        page.mouse.up()
        capture.settle(page, 500)
    return seen


def swipe(page, dx):
    """묶음 위를 손가락으로 가로로 민다(CDP 터치 이벤트). `dx`가 음수이면 왼쪽으로 밀어 다음 카드로 넘긴다."""
    box = page.locator(".carousel.cards .track").first.bounding_box()
    x0, y = box["x"] + box["width"] / 2 - dx / 2, box["y"] + 40
    cdp = page.context.new_cdp_session(page)
    point = lambda x: [{"x": x, "y": y, "id": 1}]
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": point(x0)})
    for i in range(1, 21):
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": point(x0 + dx * i / 20)})
        page.wait_for_timeout(20)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    page.wait_for_timeout(1200)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--shots", required=True)
    args = parser.parse_args()
    data, after, shots = Path(args.data), Path(args.after), Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    arrival = overlay_after(after)
    with sync_playwright() as p:
        # (a) 판단 전 최신 날짜
        w = World(p, data, {})
        page = w.open()
        s = state(page)
        check("a1 판단 전 최신: 날짜 줄이 날짜 지점", "11월 20일" in (s["pill"] or ""), s["pill"])
        check("a1 판단 전 최신: 예측 단추가 꺼지고 막힘", s["aim"] == {"disabled": True, "on": False}, s["aim"])
        check("a1 판단 전 최신: 설명 절이 숨음", all(h for _, h in s["notes"]), s["notes"])
        page.screenshot(path=str(shots / "a1-before-latest-top.png"))
        to_cards(page)
        page.screenshot(path=str(shots / "a1-before-latest-cards.png"))
        # (a) 판단 전 지난 날짜
        open_lever(page)
        seen = drag_to(page, "11/18")
        page.wait_for_timeout(600)
        page.locator("button.aim").first.click()
        capture.settle(page, 600)
        s = state(page)
        check("a2 판단 전 지난 날짜: 예측 단추를 누를 수 있음", s["aim"] == {"disabled": False, "on": True}, s["aim"])
        check("a2 판단 전 지난 날짜: 설명 절이 보임", s["notes"] and all(not h for _, h in s["notes"]) and {pt for pt, _ in s["notes"]} == {"2026-11-18"}, s["notes"])
        page.screenshot(path=str(shots / "a2-before-past-cards.png"))
        page.locator(".fold, h2").first.scroll_into_view_if_needed()
        page.evaluate("document.querySelector('[data-point]').scrollIntoView({block:'start'})")
        capture.settle(page, 400)
        page.screenshot(path=str(shots / "a2-before-past-notes.png"))
        # (b) 레버를 잡고 세 날짜를 지남
        page.evaluate("scrollTo(0, 0)")
        to_cards(page)
        marks = []
        x, y = grip(page)
        page.mouse.move(x, y)
        page.mouse.down()
        path = [page.locator(".carousel.cards .rewind > span").first.text_content()]
        graph = [page.evaluate("document.querySelector('.carousel.cards .slide').innerHTML.length")]
        held = []
        for step in range(1, 120):
            page.mouse.move(x - step * 2, y)
            page.wait_for_timeout(40)
            label = page.locator(".carousel.cards .rewind > span").first.text_content()
            if label != path[-1]:
                path.append(label)
                page.wait_for_timeout(120)
                graph.append(page.evaluate("document.querySelector('.carousel.cards .slide').innerHTML.length"))
                held.append({pt for pt, _ in state(page)["notes"]})
            if len(path) >= 4:
                break
        at_release = path[-1]
        page.mouse.up()
        capture.settle(page, 700)
        s = state(page)
        check("b 잡고 있는 동안 날짜 세 번 바뀜", len(path) >= 4, path)
        check("b 그래프 점이 세 번 움직임", len({g for g in graph}) >= 3, graph)
        check("b 잡고 있는 동안 설명 날짜가 처음 날짜", all(h == {"2026-11-18"} for h in held), held)
        check("b 손을 뗀 뒤 설명 날짜가 뗀 날짜", {pt for pt, _ in s["notes"]} == {f"2026-{at_release.replace('/', '-')}"}, [at_release, s["notes"]])
        w.close()

        # (c) 튕김 잠금
        w = World(p, data, {})
        page = w.open()
        to_cards(page)
        results = []
        for kind in ("swipe", "swipe", "tap", "tap"):
            if kind == "swipe":
                swipe(page, -240)
            else:
                page.locator(".carousel.cards .tabs button").nth(1).click()
                page.wait_for_timeout(900)
            s = state(page)
            results.append((kind, s["tab"], s["toast"]))
            if len(results) == 4:
                page.screenshot(path=str(shots / "c-bounce.png"))
            page.wait_for_timeout(2600)
        check("c 판단 전 최신: 밀기 2번과 누르기 2번이 막히고 알림", all(t == 0 and why == WHY for _, t, why in results[:1]) and all(t == 0 for _, t, _ in results), results)
        check("c 알림 문구", all(why == WHY for *_, why in results), results)
        open_lever(page)
        drag_to(page, "11/18")
        page.wait_for_timeout(600)
        passed = []
        for _ in range(2):
            swipe(page, -240)
            passed.append(state(page)["tab"])
            page.locator(".carousel.cards .tabs button").nth(0).click()
            page.wait_for_timeout(900)
        check("c 지난 날짜에서 밀기 2번이 통과", passed == [1, 1], passed)
        w.close()

        # (d) 판단 도착
        w = World(p, data, {}, reloads=True)
        page = w.open()
        before = state(page)
        w.overlay.update(arrival)
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        for _ in range(12):
            page.wait_for_timeout(700)
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            if "r=20261120-nasdaq" in page.url:
                break
        capture.settle(page, 800)
        s = state(page)
        reloads = page.evaluate("window.__reloads")
        check("d location.reload 0번", reloads == 0, reloads)
        check("d 새 판단 화면: 예측 단추가 열림", s["aim"] and not s["aim"]["disabled"], (s["aim"], page.url))
        to_cards(page)
        page.locator(".carousel.cards .tabs button").nth(1).click()
        page.wait_for_timeout(900)
        s = state(page)
        check("d 새 판단의 일정 카드가 같은 화면에 그려짐", s["tab"] == 1 and s["toast"] is None, s)
        page.screenshot(path=str(shots / "d-arrival-schedule.png"))
        w.close()

        # (a) 판단 후 최신 날짜와 지난 날짜
        w = World(p, after, {})
        page = w.open()
        to_cards(page)
        page.locator("button.aim").first.click()
        capture.settle(page, 600)
        s = state(page)
        check("a3 판단 후 최신: 설명 절이 최신 판단", {pt for pt, _ in s["notes"]} == {PENDING} and all(not h for _, h in s["notes"]), s["notes"])
        page.screenshot(path=str(shots / "a3-after-latest-cards.png"))
        page.evaluate("document.querySelector('[data-point]').scrollIntoView({block:'start'})")
        capture.settle(page, 400)
        page.screenshot(path=str(shots / "a3-after-latest-notes.png"))
        page.evaluate("scrollTo(0, 0)")
        to_cards(page)
        open_lever(page)
        drag_to(page, "11/18")
        page.wait_for_timeout(600)
        s = state(page)
        check("a4 판단 후 지난 날짜: 설명 절이 지난 판단", {pt for pt, _ in s["notes"]} == {"2026-11-18"}, s["notes"])
        page.screenshot(path=str(shots / "a4-after-past-cards.png"))
        page.evaluate("document.querySelector('[data-point]').scrollIntoView({block:'start'})")
        capture.settle(page, 400)
        page.screenshot(path=str(shots / "a4-after-past-notes.png"))
        w.close()
        print("서버 오류", w.server.errors, "외부 요청", w.server.escaped)
    print("FAILS", FAILS)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
