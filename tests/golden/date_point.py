"""리포트 화면 그림 카드의 동작 시험. 판단 전과 후, 실시간 값의 사슬, 그림 누르기, 카드 넘기기, 판단 도착, 카드별 설명 절, 기기에 남기는 예측·지수 단추 상태, 처음 항목으로 돌아가는 나란한 항목 묶음을 연다.

    python3 tests/golden/date_point.py --data /tmp/dp-u4/out --after /tmp/dp-u4/out-after --shots /tmp/dp-u4/shots

`--data`는 판단 전(가장 늦은 리포트가 날짜 지점 2026-11-19)의 리포트 자료이고, `--after`는 거기에 2026-11-20 판단을 더한 자료다.
실시간 값은 `fixtures.live(..., "closed")`(날짜 지점 2026-11-19의 정규장 마감 값)에 그 뒤 애프터장 값(날짜 지점 2026-11-20)을 더한 값이다. 화면 값은 모두 지어낸 값이다.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import capture
import fixtures

PENDING = "2026-11-20"
AFTER = 1.002
FAILS = []


def check(name: str, ok: bool, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILS.append(name)


def pending_live(data: Path) -> dict:
    live = fixtures.live(data, "closed")
    for index, found in json.loads((data / "r" / "market.json").read_text(encoding="utf-8"))["map"].items():
        live["afterhours"].setdefault(index, {})[fixtures.POINT] = {
            "time": "2026-11-19T16:50:00-05:00", "ratio": AFTER, "stocks": {}, "point": PENDING}
    live["progress"] = {"date": PENDING, "indexes": {index: {"step": 1, "since": "2026-11-20T06:50:00+09:00"} for index in live["premarket"]}, "plan": [0, 20, 60, 120]}
    return live


def overlay_after(after: Path) -> dict:
    """`after` 자료에서 판단이 도착하며 바뀌는 파일을 바이트로 읽는다."""
    paths = ["r/index.json"] + [f"r/20261120-nasdaq/{p.name}" for p in (after / "r" / "20261120-nasdaq").iterdir()]
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


# 카드 묶음에서 고른 카드(`tab`)마다 그 아래에 보이는 설명 절 이름.
NOTE_OF = ["현재 상태", "주요 분기와 예측", "종합 시나리오"]


def shows(s) -> bool:
    """고른 카드의 장에 그 카드에 맞는 설명 절만 있는지. 다른 절은 다른 장에 있어 화면 밖이다."""
    return bool(s["notes"]) and {note for _, hidden, note in s["notes"] if not hidden} == {NOTE_OF[s["tab"]]}


def state(page):
    return page.evaluate("""() => ({
      notes: (() => { const slides = [...document.querySelectorAll('.carousel.cards .track > .slide')], on = [...document.querySelectorAll('.carousel.cards .tabs button')].findIndex((b) => b.classList.contains('on'));
        return [...document.querySelectorAll('[data-point]')].map((n) => [n.dataset.point, slides.indexOf(n.closest('.slide')) !== on, n.dataset.note]); })(),
      aim: (() => { const b = document.querySelector('.carousel.cards button.aim'); return b && { disabled: b.disabled, on: b.classList.contains('on'), text: b.textContent.trim() }; })(),
      tab: [...document.querySelectorAll('.carousel.cards .tabs button')].findIndex((b) => b.classList.contains('on')),
      toast: document.querySelector('.toast')?.textContent ?? null,
    })""")


def to_cards(page):
    page.locator(".carousel.cards").first.scroll_into_view_if_needed()
    capture.settle(page, 300)


def price(page):
    """주가 카드의 머리 글씨, 점선 수, '현재' 표시[세션, 가로 자리]."""
    return page.evaluate("""() => { const g = document.querySelector('.carousel.cards .slide .gauge');
      return { top: g.querySelector('.top .ctx')?.textContent, val: g.querySelector('.val b')?.textContent, state: g.querySelector('.val .state')?.textContent,
        dashed: g.querySelectorAll('.fig svg path[stroke-dasharray="2 2"]').length,
        mark: [...g.querySelectorAll('.fig svg circle[data-kind]')].map((c) => [c.dataset.kind, Math.round(+c.getAttribute('cx'))]),
        ticker: document.getElementById('ticker').textContent }; }""")


def tap(page, fraction):
    """주가 카드 그림의 가로 `fraction` 자리를 누른다."""
    svg = page.locator(".carousel.cards .slide .gauge .fig svg").first
    box = svg.bounding_box()
    svg.click(position={"x": box["width"] * fraction, "y": box["height"] * 0.5})
    capture.settle(page, 600)


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
        check("a1 판단 전 최신: 머리 줄(#day)이 없음", page.evaluate("document.getElementById('day') === null"))
        check("a1 판단 전 최신: 예측 단추가 꺼져 있고 단계 글자를 보임", s["aim"] == {"disabled": False, "on": False, "text": "예측 중 25%"}, s["aim"])
        check("a1 판단 전 최신: 예측 단추가 꺼져도 고른 카드의 설명 절이 보이고 가장 늦은 판단의 날짜", shows(s) and {pt for pt, *_ in s["notes"]} == {"2026-11-19"}, s["notes"])
        page.screenshot(path=str(shots / "a1-before-latest-top.png"))
        to_cards(page)
        page.screenshot(path=str(shots / "a1-before-latest-cards.png"))
        # (b) 정규장이 끝난 뒤의 애프터장 값이 사슬로 이어진다
        page.locator(".zoom button[aria-label='선 그래프로 보기']").first.click()
        capture.settle(page, 600)
        live = price(page)
        check("b 머리 글씨가 다음 지점의 애프터장 값", live["top"].startswith("미국 11/19 애프터마켓") and live["state"] == "+0.20%", live)
        check("b 정규장 마감 값은 실선, 애프터장 값만 점선으로 잇고 '현재' 표시가 애프터장 색", live["dashed"] == 1 and [k for k, _ in live["mark"]] == ["after"], live)
        check("b 머리 상자 아래 줄이 애프터마켓", "애프터마켓" in live["ticker"], live["ticker"])
        page.screenshot(path=str(shots / "b-chain.png"))
        # (a) 그림 누르기
        tap(page, 0.4)
        picked = price(page)
        check("a2 그림을 누르면 그날 정규장 종가로 머리 글씨와 '현재' 표시가 옮겨 간다",
              picked["top"].startswith("미국") and "정규장" in picked["top"] and picked["val"] != live["val"] and picked["mark"][0][0] == "regular" and picked["mark"][0][1] < live["mark"][0][1], picked)
        tap(page, 0.995)
        check("a2 오른쪽 끝을 누르면 처음 상태로 돌아온다", price(page) == live, price(page))
        # (c) 판단 전에도 카드를 넘긴다
        w.close()
        w = World(p, data, {})
        page = w.open()
        to_cards(page)
        swipe(page, -240)
        s = state(page)
        check("c 판단 전 최신: 밀면 예측과 일정 카드로 넘어가고 알림이 없다", s["tab"] == 1 and s["toast"] is None, s)
        page.locator(".carousel.cards .tabs button").nth(2).click()
        page.wait_for_timeout(900)
        s = state(page)
        check("c 판단 전 최신: 권장 배율 탭을 누르면 넘어가고 알림이 없다", s["tab"] == 2 and s["toast"] is None and shows(s), s)
        page.screenshot(path=str(shots / "c-swipe.png"))
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
        check("d 새 판단의 예측과 일정 카드가 같은 화면에 그려짐", s["tab"] == 1 and s["toast"] is None, s)
        page.screenshot(path=str(shots / "d-arrival-schedule.png"))
        w.close()

        # (a) 판단 후 최신 날짜와 지난 날짜
        w = World(p, after, {})
        page = w.open()
        to_cards(page)
        page.locator(".carousel.cards button.aim").first.click()
        capture.settle(page, 600)
        s = state(page)
        check("a3 판단 후 최신: 설명 절이 최신 판단이고 고른 카드의 절만 보인다", {pt for pt, *_ in s["notes"]} == {PENDING} and shows(s), s["notes"])
        for i in (1, 2, 0):
            page.locator(".carousel.cards .tabs button").nth(i).click()
            capture.settle(page, 600)
            s = state(page)
            check(f"a3 {NOTE_OF[i]} 카드로 넘기면 그 절만 보인다", s["tab"] == i and shows(s), [s["tab"], s["notes"]])
        page.screenshot(path=str(shots / "a3-after-latest-cards.png"))
        page.evaluate("document.querySelector('[data-point]').scrollIntoView({block:'start'})")
        capture.settle(page, 400)
        page.screenshot(path=str(shots / "a3-after-latest-notes.png"))
        # (e) 예측 단추와 지수 단추의 상태는 기기에 남아 다음에 열 때도 쓴다.
        check("e 예측 단추를 켠 상태를 기기에 남긴다", page.evaluate("localStorage.getItem('aim')") == "true")
        page = w.open()
        check("e 다시 열면 예측 단추를 켠 채로 연다", state(page)["aim"]["on"], state(page)["aim"])
        page.locator(".index-pick").click()
        capture.settle(page, 800)
        check("e 지수 단추로 고른 지수를 기기에 남긴다", page.evaluate("localStorage.getItem('index')") == '"biotech"')
        page = w.open()
        tint = page.evaluate("document.documentElement.style.getPropertyValue('--index')")
        check("e 리포트 키 없이 다시 열면 마지막에 고른 지수의 리포트를 연다", tint == "#AE9CE6" and state(page)["aim"]["on"], (tint, state(page)["aim"]))
        w.close()

        # (f) 나란한 항목 묶음(그림 카드, 캘린더 날짜, 이슈 탭, 거시 지표)은 바로가기 탭을 옮기거나 화면이 가려지면 처음 항목으로 돌아간다.
        w = World(p, after, {})
        page = w.open()
        chosen = lambda: page.evaluate("""() => {
          const on = (q) => [...document.querySelectorAll(q)].findIndex((b) => b.classList.contains('on'));
          return { cards: on('.carousel.cards .tabs button'), day: on('.days .strip button'),
                   today: [...document.querySelectorAll('.days .strip button')].findIndex((b) => b.classList.contains('today')),
                   news: on('h2.tabbed .tabline button'), macro: on('.carousel.indicators .tabs .strip button') }; }""")
        first = chosen()
        check("f 처음 항목: 주가 카드, 리포트 날짜, 첫 거시 지표", first["cards"] == 0 and first["day"] == first["today"] >= 0 and first["macro"] in (-1, 0), first)

        def move_all():
            # 다른 바로가기 페이지의 단추는 화면에 보이지 않으므로 문서에서 바로 누른다.
            press = lambda q, n: page.evaluate("([q, n]) => document.querySelectorAll(q)[n]?.click()", [q, n])
            press(".carousel.cards .tabs button", 2)
            press(".days .strip button", 0 if first["today"] else 1)
            press("h2.tabbed .tabline button", 1 - first["news"])
            press(".carousel.indicators .tabs .strip button", 1)
            capture.settle(page, 900)
            moved = chosen()
            return moved["cards"] == 2 and moved["day"] != first["day"] and moved["news"] != first["news"] and (first["macro"] < 0 or moved["macro"] == 1), moved

        moved = move_all()
        check("f 묶음마다 다른 항목을 고른다", *moved)
        capture.turn(page, "이슈")
        capture.turn(page, "예측")
        check("f 바로가기 탭을 옮기고 돌아오면 처음 항목으로 돌아간다", chosen() == first, chosen())
        moved = move_all()
        page.evaluate("Object.defineProperty(document, 'hidden', { value: true, configurable: true }); document.dispatchEvent(new Event('visibilitychange'));"
                      "Object.defineProperty(document, 'hidden', { value: false, configurable: true }); document.dispatchEvent(new Event('visibilitychange'));")
        capture.settle(page, 400)
        check("f 화면이 가려졌다 돌아오면(상세 화면, 앱 밖) 처음 항목으로 돌아간다", moved[0] and chosen() == first, (moved, chosen()))
        moved = move_all()
        page.reload(wait_until="networkidle")
        capture.settle(page)
        check("f 다시 열면 처음 항목으로 연다", moved[0] and chosen() == first, (moved, chosen()))
        check("f 오류 0건", not w.server.errors, w.server.errors)
        w.close()
        print("서버 오류", w.server.errors, "외부 요청", w.server.escaped)
    print("FAILS", FAILS)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
