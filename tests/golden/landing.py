"""자산 탭 U1(처음 여는 탭, 평가 금액, 머리 줄, 예측 단추 글자)의 동작 시험. 화면 값은 모두 지어낸 값이다.

    python3 tests/golden/landing.py --data /tmp/dp-u2/out --shots /tmp/at-u1/shots

`--data`는 가장 늦은 리포트가 날짜 지점 2026-11-19인 리포트 자료다. 주말 시나리오의 리포트 항목(금요일·토요일 리포트)은 이 시험이 지어 얹는다.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import capture
import date_point as dp
import fixtures

FAILS = dp.FAILS
check = dp.check
# 시나리오: (이름, 보는 리포트의 날짜 지점·날짜, 배치 진행 날짜, 앞선 날짜 지점, 도착하는 리포트의 날짜와 지점)
WEEKDAY = {"name": "평일", "report": ("2026-11-19", "2026-11-19"), "batch": "2026-11-20", "ahead": "2026-11-20", "arrive": ("2026-11-20", "2026-11-20")}
SATURDAY = {"name": "토요일 배치", "report": ("2026-11-20", "2026-11-20"), "batch": "2026-11-21", "ahead": "2026-11-23", "arrive": ("2026-11-21", "2026-11-23")}
MONDAY = {"name": "월요일 배치", "report": ("2026-11-21", "2026-11-23"), "batch": "2026-11-23", "ahead": None, "arrive": ("2026-11-23", "2026-11-23")}


def key_of(date: str, index: str = "nasdaq") -> str:
    return f"{date.replace('-', '')}-{index}"


def closes(date: str) -> list:
    """리포트 날짜 `date`의 서울 아침 기준으로 끝난 정규장 날짜(지난 정규장 거래일)들 중 시료 자료에 없는 것."""
    return {"2026-11-19": [], "2026-11-20": ["2026-11-19"], "2026-11-21": ["2026-11-19", "2026-11-20"], "2026-11-23": ["2026-11-19", "2026-11-20"]}[date]


def refit(raw: bytes, date: str, point: str) -> bytes:
    """19일 리포트의 그림 카드 값(`cards.json`)을 `date` 리포트의 값으로 바꾼다. 종가 날짜 열에 지난 정규장 날짜를 더하고 날짜와 기준 날짜를 맞춘다."""
    cards = json.loads(raw)
    for day in closes(date):
        cards["dates"].append(day)
        cards["history"].append(round(cards["history"][-1] * 1.001, 2))
    cards["day"], cards["point"] = date, point
    cards["base_date"] = cards["dates"][-1]
    return json.dumps(cards).encode()


def story(data: Path, case: dict) -> dict:
    """`case`의 보는 리포트가 가장 늦은 리포트가 되도록 목록에 항목을 얹고, 그 리포트의 바이트를 `{경로: 바이트}`로 돌려준다."""
    out, base = {}, data / "r"
    listing = json.loads((base / "index.json").read_text(encoding="utf-8"))
    date, point = case["report"]
    if date != "2026-11-19":
        names = [key_of(date, "nasdaq"), key_of(date, "biotech")]
        for name in names:
            seed = key_of("2026-11-19", name.split("-")[1])
            out.update({f"r/{name}/{p.name}": p.read_bytes() for p in (base / seed).iterdir() if p.is_file()})
            out[f"r/{name}/cards.json"] = refit(out[f"r/{name}/cards.json"], date, point)
            listing = {name: {**listing[seed], "date": date, "point": point, "day": f"{date} (보기)"}, **listing}
    out["r/index.json"] = json.dumps(listing, ensure_ascii=False).encode()
    return out


def arrival(data: Path, case: dict, current: dict) -> dict:
    """`case`의 새 리포트가 도착한 뒤의 파일(목록, 리포트 파일)."""
    out, base = dict(current), data / "r"
    listing = json.loads(current["r/index.json"])
    date, point = case["arrive"]
    for index in ("nasdaq", "biotech"):
        name, seed = key_of(date, index), key_of("2026-11-19", index)
        out.update({f"r/{name}/{p.name}": p.read_bytes() for p in (base / seed).iterdir() if p.is_file()})
        out[f"r/{name}/cards.json"] = refit(out[f"r/{name}/cards.json"], date, point)
        listing = {name: {**listing[seed], "date": date, "point": point, "day": f"{date} (새)"}, **listing}
    out["r/index.json"] = json.dumps(listing, ensure_ascii=False).encode()
    return out


def live_for(data: Path, case: dict, stage: str) -> dict:
    """`stage`가 `running`이면 배치가 도는 값, `pre`이면 판단 날짜 지점의 정규장 값과 다음 날짜 지점의 1분 값이 온 값, `done`이면 판단 날짜 지점의 프리장 값만 온 값이다.
    월요일 배치처럼 판단 날짜 지점이 새 판단과 같은 경우(`ahead`가 없음)는 배치가 그 지점의 정규장 전에 돌므로 프리장 값만 둔다."""
    live = fixtures.live(data, "pre" if stage == "done" or not case["ahead"] else "closed")
    date, point = case["report"]
    board = json.loads((data / "r" / "market.json").read_text(encoding="utf-8"))["map"]
    for index in board:
        live["premarket"].setdefault(index, {})
        if point != fixtures.POINT:
            live["premarket"][index][point] = {**live["premarket"][index][fixtures.POINT], "point": point}
        if stage in ("pre", "running") and case["ahead"]:
            live["afterhours"].setdefault(index, {})[case["ahead"]] = {"time": f"{case['ahead']}T16:50:00-05:00", "ratio": 1.002, "stocks": {}, "point": case["ahead"]}
    live["progress"] = {"date": case["batch"] if stage == "running" else date,
                        "indexes": {index: {"step": 1, "since": "2026-11-20T06:50:00+09:00"} for index in board}, "plan": [0, 20, 60, 120]}
    return live


class Scene(dp.World):
    def __init__(self, p, data, overlay, live, uid=1, flag=False, reloads=False):
        super().__init__(p, data, overlay, reloads)
        self.server.live = live
        if uid != 1:
            self.context.add_init_script(capture.mock(uid))
        if flag:
            self.context.add_init_script("try { localStorage.setItem('asset', '1'); } catch {}")


LABEL = "() => { const b = document.querySelector('button.aim'); return b && { text: b.textContent.trim(), pre: b.classList.contains('pre'), running: b.classList.contains('running'), on: b.classList.contains('on'), disabled: b.disabled }; }"


def label(page):
    return page.evaluate(LABEL)


def wait_label(page, want, tries=14):
    for _ in range(tries):
        got = label(page)
        if got and want(got):
            return got
        page.wait_for_timeout(500)
    return label(page)


def active_page(page):
    return page.evaluate("() => history.state?.page ?? null")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--shots", required=True)
    args = parser.parse_args()
    data, shots = Path(args.data), Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        # 처음 여는 탭 (A1)
        for name, uid, flag, want in (("표시가 있는 기기", 1, True, "자산"), ("표시가 없는 기기", 2, False, None)):
            w = Scene(p, data, {}, fixtures.live(data, "closed"), uid, flag)
            page = w.open()
            capture.settle(page, 600)
            first = page.evaluate("() => document.querySelector('.tabs, nav')?.textContent ?? ''")
            at = active_page(page)
            check(f"a1 열 탭 없음, {name}", (at == want) if want else (at not in ("자산",) and at is not None), at)
            if want:
                check("a1 표시가 있는 기기의 첫 화면에 평가 금액", page.locator(".asset-sum").count() == 1)
            w.close()
        # 평가 금액 (A5)
        w = Scene(p, data, {}, fixtures.live(data, "closed"), 1, True)
        page = w.open()
        capture.settle(page, 800)
        state = lambda: page.evaluate("() => { const s = document.querySelector('.asset-sum'); return s && { veil: s.classList.contains('veil') }; }")
        first = state()
        page.locator(".asset-sum").first.click()
        page.wait_for_timeout(300)
        second = state()
        page.locator(".asset-sum").first.click()
        page.wait_for_timeout(300)
        third = state()
        check("a5 처음에는 평가 금액이 보임", first == {"veil": False}, first)
        check("a5 한 번 누르면 가림", second == {"veil": True}, second)
        check("a5 두 번 누르면 다시 보임", third == {"veil": False}, third)
        page.screenshot(path=str(shots / "asset-tab-first.png"))
        w.close()
        # 머리 줄 (P1)
        w = Scene(p, data, {}, fixtures.live(data, "closed"), 2, False)
        page = w.open()
        check("p1 #day 요소가 없음", page.evaluate("() => document.getElementById('day') === null && !document.querySelector('.stage')"))
        w.close()
        # 예측 단추 (P2)
        for case in (WEEKDAY, SATURDAY, MONDAY):
            base = story(data, case)
            for stage, text in (("done", "예측"), ("pre", "예측 업데이트 전"), ("running", None)):
                if stage == "pre" and not case["ahead"]:
                    continue
                w = Scene(p, data, base, live_for(data, case, stage), 2, False)
                page = w.open()
                got = wait_label(page, lambda s: s["pre"] or s["running"] if stage != "done" else True)
                good = got and ((got["text"] == text and not got["pre"] and not got["running"]) if stage == "done"
                                else (got["text"] == text and got["pre"]) if stage == "pre"
                                else (got["text"].startswith("예측 중 ") and got["text"].endswith("%") and got["running"]))
                check(f"p2 {case['name']} {stage}: 단추 글자", bool(good), got)
                notes = page.evaluate("() => { const slides = [...document.querySelectorAll('.carousel.cards .track > .slide')], on = [...document.querySelectorAll('.carousel.cards .tabs button')].findIndex((b) => b.classList.contains('on')); return [...document.querySelectorAll('[data-point]')].map((n) => [n.dataset.point, slides.indexOf(n.closest('.slide')) !== on, n.dataset.note]); }")
                check(f"p2 {case['name']} {stage}: 예측을 켜기 전에도 주가와 예측 카드의 설명 절(현재 상태)이 보임", dp.shows({"notes": notes, "tab": 0}), notes)
                faded = page.evaluate("() => [...document.querySelectorAll('[data-note]')].map((n) => n.classList.contains('stale'))")
                # 판단 날짜 지점의 정규장이 시작한 뒤(`ahead`가 있는 경우의 pre·running)만 회색이다. 월요일 배치는 정규장 전에 돌므로 회색이 아니다.
                check(f"p2 {case['name']} {stage}: 설명 절은 정규장 시작 뒤 업데이트를 기다리는 동안만 회색", bool(faded) and all(f == (stage != "done" and bool(case["ahead"])) for f in faded), faded)
                # 세 상태 모두 눌러 가장 늦은 판단의 예측을 켠다
                page.locator("button.aim").first.click()
                capture.settle(page, 500)
                on = label(page)
                notes = page.evaluate("() => { const slides = [...document.querySelectorAll('.carousel.cards .track > .slide')], on = [...document.querySelectorAll('.carousel.cards .tabs button')].findIndex((b) => b.classList.contains('on')); return [...document.querySelectorAll('[data-point]')].map((n) => [n.dataset.point, slides.indexOf(n.closest('.slide')) !== on, n.dataset.note]); }")
                check(f"p2 {case['name']} {stage}: 눌러서 예측이 켜지고 현재 상태 절이 보임",
                      bool(on and on["on"] and not on["disabled"] and dp.shows({"notes": notes, "tab": 0}) and len({pt for pt, *_ in notes}) == 1), (on, notes))
                if case is WEEKDAY and stage == "running":
                    page.locator(".carousel.cards").first.scroll_into_view_if_needed()
                    capture.settle(page, 400)
                    page.screenshot(path=str(shots / "predict-running.png"))
                w.close()
            # 도착: 새 리포트가 목록에 생기면 새로 고침 없이 다시 그린다
            for stage in ("running",) + (("pre",) if case["ahead"] else ()):
                w = Scene(p, data, base, live_for(data, case, stage), 2, False, reloads=True)
                page = w.open()
                wait_label(page, lambda s: s["pre"] or s["running"])
                w.overlay.update(arrival(data, case, base))
                for _ in range(16):
                    page.wait_for_timeout(700)
                    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
                    if key_of(case["arrive"][0]) in page.url:
                        break
                capture.settle(page, 800)
                check(f"p2 {case['name']} {stage}: 새 리포트로 그 자리에서 다시 그림", key_of(case["arrive"][0]) in page.url, page.url)
                check(f"p2 {case['name']} {stage}: 새 화면의 예측 단추가 그려짐", (label(page) or {}).get("text") == "예측", label(page))
                check(f"p2 {case['name']} {stage}: location.reload 0번", page.evaluate("window.__reloads") == 0, page.evaluate("window.__reloads"))
                w.close()
        print("서버 오류", w.server.errors, "외부 요청", w.server.escaped)
    print("FAILS", FAILS)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
