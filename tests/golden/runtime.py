"""미니 앱의 화면 수명과 정시 갱신을 시험한다. 화면 응답은 `capture.py`의 가짜 서버를 그대로 쓴다.

    python3 tests/golden/runtime.py leak --ref /path/to/built
    python3 tests/golden/runtime.py beat --ref /path/to/built --every 1 --minutes 3

`leak`은 화면마다 처음 연 뒤의 `setInterval` 수와 `document`·`window` 손길 수, 관찰자 수를 세고, 그 자리에서 다시 그리기(`popstate`)로
다른 화면과 오가기를 20번 한 뒤 같은 화면에서 다시 센다. 두 값이 화면마다 같으면 통과다.
손길은 대상·종류·함수·capture가 같으면 하나로 세고, `removeEventListener`와 `signal`이 끊긴 손길은 뺀다.

`beat`는 가짜 시계(`clock.install`)를 `fixtures.NOW` 30초 뒤에 두고 가장 늦은 리포트를 연 뒤, `--minutes`분 동안 `invest-live GET /` 요청 시각을 적는다.
이어서 화면을 숨긴 채 같은 시간을 보내 요청이 없는지 보고, 다시 보이게 해 바로 한 번 받는지 본다. 앱의 `LIVE_EVERY`가 `--every`와 같아야 한다.
같은 방법으로 내 자산 페이지의 `invest-account` 요청 시각과, 분석 중인 리포트의 단계 표시가 회차마다 진척률을 다시 쓰는지 본다.
"""
import argparse
import datetime as dt
import json
import shutil
import sys

from playwright.sync_api import sync_playwright

import capture
import fixtures

COUNT = """(() => {
  const active = new Map(), intervals = new Set(), observers = new Set();
  const named = (target) => (target === document ? "document" : target === window ? "window" : null);
  const add = EventTarget.prototype.addEventListener, remove = EventTarget.prototype.removeEventListener;
  const id = (target, type, listener, options) => `${named(target)} ${type} ${typeof options === "boolean" ? options : !!options?.capture}`;
  EventTarget.prototype.addEventListener = function (type, listener, options) {
    const where = named(this);
    if (where && listener && !options?.signal?.aborted) {
      const key = id(this, type, listener, options);
      if (!active.has(key)) active.set(key, new Set());
      active.get(key).add(listener);
      options?.signal?.addEventListener("abort", () => active.get(key)?.delete(listener), { once: true });
    }
    return add.call(this, type, listener, options);
  };
  EventTarget.prototype.removeEventListener = function (type, listener, options) {
    if (named(this)) active.get(id(this, type, listener, options))?.delete(listener);
    return remove.call(this, type, listener, options);
  };
  const every = window.setInterval, unevery = window.clearInterval;
  window.setInterval = function (...args) { const n = every.apply(this, args); intervals.add(n); return n; };
  window.clearInterval = function (n) { intervals.delete(n); return unevery.call(this, n); };
  for (const name of ["MutationObserver", "ResizeObserver", "IntersectionObserver"]) {
    const Base = window[name];
    if (!Base) continue;
    window[name] = class extends Base {
      observe(...args) { observers.add(this); return super.observe(...args); }
      disconnect() { observers.delete(this); return super.disconnect(); }
    };
  }
  window.__counts = () => {
    const sum = (where) => [...active].filter(([key]) => key.startsWith(where + " ")).reduce((n, [, set]) => n + set.size, 0);
    return { intervals: intervals.size, document: sum("document"), window: sum("window"), observers: observers.size };
  };
})();"""

VISIBLE = """(() => {
  window.__hidden = false;
  Object.defineProperty(Document.prototype, "visibilityState", { get: () => (window.__hidden ? "hidden" : "visible"), configurable: true });
  Object.defineProperty(Document.prototype, "hidden", { get: () => window.__hidden, configurable: true });
  const calls = (window.__calls = []), base = window.fetch;
  window.fetch = function (input, init) {
    const url = typeof input === "string" ? input : input.url, method = (init?.method || "GET").toUpperCase();
    calls.push({ url, method, at: Date.now() });
    return base.call(this, input, init);
  };
})();"""

BIOTECH = "20261119-biotech"
OTHER = f"?r={BIOTECH}"
# 화면 이름 → (처음 여는 주소, 그 화면으로 돌아오는 주소, 오갈 다른 화면 주소, 연 뒤 넘길 페이지, 사용자, 자료)
SCREENS = {
    "latest": ("", f"?r={fixtures.BASE_KEY}", OTHER, None, 1, "base"),
    "issue": (f"?r={fixtures.BASE_KEY}&issue=1", f"?r={fixtures.BASE_KEY}&issue=1", f"?r={fixtures.BASE_KEY}&issue=2", None, 1, "base"),
    "past": ("?r=20261118-nasdaq", "?r=20261118-nasdaq", OTHER, None, 1, "base"),
    "market": ("", f"?r={fixtures.BASE_KEY}", OTHER, "시장", 1, "base"),
    "asset": ("", f"?r={fixtures.BASE_KEY}", OTHER, "자산", 1, "base"),
    "stock": (f"?r={fixtures.BASE_KEY}&stock=NVDA", f"?r={fixtures.BASE_KEY}&stock=NVDA", f"?r={fixtures.BASE_KEY}&stock=NVDA", None, 1, "base"),
    "trades": (f"?r={fixtures.BASE_KEY}&trades=nasdaq", f"?r={fixtures.BASE_KEY}&trades=nasdaq", f"?r={fixtures.BASE_KEY}&trades=nasdaq", None, 1, "base"),
    "nonowner": ("", f"?r={fixtures.BASE_KEY}", OTHER, None, 2, "base"),
}
SWAP = """(url) => new Promise((done) => {
  history.pushState({ ...history.state }, "", url);
  dispatchEvent(new PopStateEvent("popstate", { state: history.state }));
  setTimeout(done, 350);
})"""


def context(browser, server, uid, dataset, clock=None, overlay=None):
    page_context = browser.new_context(viewport={"width": 390, "height": 1000}, device_scale_factor=1, reduced_motion="reduce",
                                       locale="ko-KR", timezone_id="Asia/Seoul")
    if clock is None:
        page_context.clock.set_fixed_time(fixtures.NOW)
    else:
        page_context.clock.install(time=clock)
    page_context.add_init_script(capture.mock(uid))
    if uid == 1:
        page_context.add_init_script("try { localStorage.setItem('asset', '1'); } catch {}")
    files = {}
    files.update(overlay or {})
    page_context.route("**/*", server.handler(files, fixtures.account()))
    return page_context


def leak(browser, server) -> bool:
    ok = True
    for name, (first, back, other, turn_to, uid, dataset) in SCREENS.items():
        page_context = context(browser, server, uid, dataset)
        page_context.add_init_script(COUNT)
        page = page_context.new_page()
        page.on("pageerror", lambda error: server.errors.append(f"pageerror: {str(error)[:300]}"))
        page.goto(capture.APP + first, wait_until="networkidle")
        capture.settle(page)
        if turn_to:
            capture.turn(page, turn_to)
        start = page.evaluate("__counts()")
        for _ in range(20):
            page.evaluate(SWAP, other)
            page.evaluate(SWAP, back)
        capture.settle(page)
        end = page.evaluate("__counts()")
        same = start == end
        ok &= same
        print(f"{name:9} 처음 {json.dumps(start)}  20번 뒤 {json.dumps(end)}  {'같음' if same else '다름'}")
        page_context.close()
    return ok


def advance(page, seconds: int):
    for _ in range(seconds):
        page.clock.run_for(1000)
        page.wait_for_timeout(15)


def calls(page, prefix: str, method: str, since: int = 0) -> list:
    return [call["at"] for call in page.evaluate("__calls") if call["url"].startswith(prefix) and call["method"] == method][since:]


def stamp(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%H:%M:%S.%f")[:-3]


def on_beat(times: list, every: int) -> bool:
    return all(ms % (every * 60_000) in range(3000, 3200) for ms in times)


def hide(page, hidden: bool):
    page.evaluate("(hidden) => { window.__hidden = hidden; document.dispatchEvent(new Event('visibilitychange')); }", hidden)


def beat(browser, server, every: int, minutes: int) -> bool:
    ok = True
    start = fixtures.NOW + dt.timedelta(seconds=30)
    span = minutes * 60
    page_context = context(browser, server, 1, "base", clock=start)
    page_context.add_init_script(VISIBLE)
    page = page_context.new_page()
    page.on("pageerror", lambda error: server.errors.append(f"pageerror: {str(error)[:300]}"))
    page.goto(capture.APP, wait_until="networkidle")
    page.wait_for_timeout(300)
    opened = calls(page, capture.LIVE_URL, "GET")
    advance(page, span)
    shown = calls(page, capture.LIVE_URL, "GET", len(opened))
    good = len(opened) == 1 and minutes // every <= len(shown) <= minutes // every + 1 and on_beat(shown, every)
    ok &= good
    print(f"invest-live 보이는 {minutes}분: 연 때 {len(opened)}번, 회차 {len(shown)}번 {[stamp(t) for t in shown]} {'통과' if good else '실패'}")
    seen = len(calls(page, capture.LIVE_URL, "GET"))
    hide(page, True)
    advance(page, span)
    hidden = calls(page, capture.LIVE_URL, "GET", seen)
    ok &= not hidden
    print(f"invest-live 숨긴 {minutes}분: {len(hidden)}번 {'통과' if not hidden else '실패'}")
    seen = len(calls(page, capture.LIVE_URL, "GET"))
    hide(page, False)
    page.wait_for_timeout(300)
    back = calls(page, capture.LIVE_URL, "GET", seen)
    advance(page, every * 60 + 5)
    after = calls(page, capture.LIVE_URL, "GET", seen + len(back))
    good = len(back) == 1 and len(after) >= 1 and on_beat(after, every)
    ok &= good
    print(f"invest-live 다시 보임: 바로 {len(back)}번, 그 뒤 {[stamp(t) for t in after]} {'통과' if good else '실패'}")
    page_context.close()

    # 내 자산 페이지는 보이는 동안 1분마다 정시 3초 뒤에 받고, 다른 페이지로 넘기면 받지 않는다.
    page_context = context(browser, server, 1, "base", clock=start)
    page_context.add_init_script(VISIBLE)
    page = page_context.new_page()
    page.goto(capture.APP, wait_until="networkidle")
    page.wait_for_timeout(300)
    page.locator("nav.jump button", has_text="자산").first.click()
    page.wait_for_timeout(300)
    seen = len(calls(page, capture.ASSET_URL, "POST"))
    advance(page, 180)
    polled = calls(page, capture.ASSET_URL, "POST", seen)
    good = 3 <= len(polled) <= 4 and on_beat(polled, 1)
    ok &= good
    print(f"invest-account 자산 3분: {len(polled)}번 {[stamp(t) for t in polled]} {'통과' if good else '실패'}")
    page.locator("nav.jump button", has_text="예측").first.click()
    page.wait_for_timeout(300)
    seen = len(calls(page, capture.ASSET_URL, "POST"))
    advance(page, 180)
    away = calls(page, capture.ASSET_URL, "POST", seen)
    ok &= not away
    print(f"invest-account 예측 페이지 3분: {len(away)}번 {'통과' if not away else '실패'}")
    page_context.close()

    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("test", choices=["leak", "beat"])
    parser.add_argument("--ref", required=True, help="앱 코드의 git 시점이나 폴더")
    parser.add_argument("--data", default="v0.8", help="리포트 자료 r/의 git 시점이나 폴더")
    parser.add_argument("--every", type=int, default=1, help="앱의 LIVE_EVERY(분)")
    parser.add_argument("--minutes", type=int, default=3, help="보이는 동안과 숨긴 동안 각각 보낼 분")
    args = parser.parse_args()
    temps = []
    try:
        code = capture.checkout(args.ref, temps)
        data = code if args.data == args.ref else capture.checkout(args.data, temps)
        server = capture.Server(code, data)
        with sync_playwright() as p:
            browser = capture.launch(p)
            ok = leak(browser, server) if args.test == "leak" else beat(browser, server, args.every, args.minutes)
            browser.close()
    finally:
        for temp in temps:
            shutil.rmtree(temp, ignore_errors=True)
    if server.escaped:
        print(f"막은 외부 요청: {', '.join(sorted(set(server.escaped)))}")
        ok = False
    for error in dict.fromkeys(server.errors):
        print(f"  {error}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
