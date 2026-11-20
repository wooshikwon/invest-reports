"""큰 글씨 숫자 굴림의 동작 시험. 받은 값으로 다시 그릴 때만 바뀐 숫자 자리를 굴리고, 사용자가 고른 변경과 굴림을 줄인 기기는 바로 바꾸는지 연다.

    python3 tests/golden/roll.py

화면 값은 모두 지어낸 값이다. 계좌 요약은 `asset_tab.sample()`, 실시간 값은 `fixtures.live`의 값이다.
"""
import json
import sys

from playwright.sync_api import sync_playwright

import asset_tab
import capture
import fixtures

FAILS = []
CARDS = asset_tab.CARDS
# 문서에 들어온 굴림 자리(`.roll`)를 센다. 굴림이 끝나면 자리를 글씨로 되돌리므로 남은 자리 수와 따로 센다.
COUNT = """window.__rolls = []; new MutationObserver((records) => records.forEach((r) => r.addedNodes.forEach((node) => {
  if (node.nodeType === 1) [node, ...node.querySelectorAll('.roll')].filter((n) => n.matches('.roll'))
    .forEach((n) => window.__rolls.push({ to: n.querySelector('.d').textContent, strip: [...n.querySelectorAll('.strip span')].map((s) => s.textContent),
      at: n.closest('.gauge, .asset-sum')?.className ?? '' }));
}))).observe(document, { childList: true, subtree: true });"""


def check(name: str, ok: bool, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILS.append(name)


def rolls(page) -> list:
    return page.evaluate("window.__rolls.splice(0)")


def text(page, selector: str) -> str:
    return page.locator(selector).first.text_content()


def refresh(page, wait: int = 120):
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_timeout(wait)


def open_page(browser, server, account, motion: str):
    context = browser.new_context(viewport={"width": 390, "height": 1000}, device_scale_factor=1, reduced_motion=motion,
                                  locale="ko-KR", timezone_id="Asia/Seoul")
    context.clock.set_fixed_time(fixtures.NOW)
    context.add_init_script(capture.mock(1))
    context.add_init_script("try { localStorage.setItem('asset', '1'); } catch {}")
    context.add_init_script(COUNT)
    context.route("**/*", server.handler({}, account))
    page = context.new_page()
    page.on("pageerror", lambda e: server.errors.append(f"pageerror: {str(e)[:300]}"))
    page.on("console", lambda m: m.type == "error" and server.errors.append(f"console: {m.text[:300]}"))
    page.goto(capture.APP, wait_until="networkidle")
    capture.settle(page)
    return context, page


def asset(browser, server):
    account = asset_tab.sample()
    ret = account["performance"]["sectors"]["nasdaq"]["returns"]
    context, page = open_page(browser, server, account, "no-preference")
    capture.turn(page, "자산")
    asset_tab.tab(page, 0)
    rolls(page)
    cum = f"{CARDS} .slide:nth-child(1) .val b"
    before = text(page, cum)
    ret["now"]["realized"] += 0.0123
    refresh(page)
    moving = page.locator(f"{cum} .roll").count()
    got = rolls(page)
    check("R1 새 계좌 요약은 누적 수익률 숫자를 굴린다", moving > 0 and any("gauge" in r["at"] for r in got), [before, moving, len(got)])
    up = [r for r in got if "gauge" in r["at"]]
    check("R1 값이 커지면 이전 숫자부터 위로 굴린다", all(r["strip"][-1] == r["to"] for r in up), up[:2])
    page.wait_for_timeout(900)
    after = text(page, cum)
    check("R1 굴림이 끝나면 글씨만 남는다", page.locator(".roll").count() == 0 and after != before, [before, after])

    ret["now"]["realized"] -= 0.0246
    refresh(page)
    down = [r for r in rolls(page) if "gauge" in r["at"]]
    check("R2 값이 작아지면 아래로 굴린다", down and all(r["strip"][0] == r["to"] for r in down), down[:2])
    page.wait_for_timeout(900)

    item = next(it for it in account["items"] if it["sector"] == "nasdaq")
    item["value"] += 1234
    refresh(page)
    got = rolls(page)
    check("R3 평가 금액 숫자를 굴린다", any("asset-sum" in r["at"] for r in got), got[:2])
    page.wait_for_timeout(900)

    page.locator(".asset-head [data-unit]:not(.on)").first.click()
    page.wait_for_timeout(120)
    check("R4 금액 단위를 바꾸면 굴리지 않는다", not rolls(page))
    page.locator(".asset-head [data-unit]:not(.on)").first.click()
    page.wait_for_timeout(120)
    rolls(page)
    asset_tab.drag_back(page, 40)
    check("R4 기준 날짜를 옮기면 굴리지 않는다", not rolls(page))
    context.close()


def trades(browser, server):
    account = asset_tab.sample()
    block = account["trades"]["sectors"]["nasdaq"][-1]
    execution = {"symbol": "QQQ", "side": "BUY", "quantity": 1, "amount": 500.0, "at": f"{block['date']}T23:31:00", "filled": True}
    block["executions"] = [execution]
    context, page = open_page(browser, server, account, "no-preference")
    page.goto(capture.APP + "?trades=nasdaq", wait_until="networkidle")
    capture.settle(page)
    rolls(page)
    before = text(page, ".trade-sum b")
    execution["amount"] += 37
    refresh(page)
    got = rolls(page)
    check("R5 기간 투자액 숫자를 굴린다", any("trade-sum" in r["at"] for r in got), [before, got[:2]])
    page.wait_for_timeout(900)
    check("R5 굴림이 끝나면 새 기간 투자액이다", text(page, ".trade-sum b") != before, [before, text(page, ".trade-sum b")])
    page.locator(".trade-head [data-filter]:not(.on)").first.click()
    page.wait_for_timeout(120)
    check("R5 필터를 바꾸면 굴리지 않는다", not rolls(page))
    context.close()


def outlook(browser, server):
    """실시간 값을 가장 늦은 리포트의 날짜 지점에 옮겨 연 뒤, 정규장 체결가를 올려 받게 한다."""
    reports = json.loads((capture.REPO / "r" / "index.json").read_text(encoding="utf-8"))
    for index, found in server.live["premarket"].items():
        point = next(entry["point"] for entry in reports.values() if entry["index"] == index)
        found.update({point: {**value, "point": point} for value in found.values()})
    context, page = open_page(browser, server, asset_tab.sample(), "no-preference")
    capture.turn(page, "예측")
    rolls(page)
    price = ".carousel.cards .gauge.summary .val b"
    before = text(page, price)
    for found in server.live["premarket"].values():
        for point in found.values():
            point["ratio"] = round(point["ratio"] * 1.013, 6)
            point["stocks"] = {symbol: round(value * 1.013, 4) for symbol, value in point["stocks"].items()}
    refresh(page)
    got = rolls(page)
    page.wait_for_timeout(900)
    after = text(page, price)
    check("R6 1분 값은 예측 탭 큰 값 숫자를 굴린다", after != before and bool(got), [before, after, len(got)])
    page.locator("button.aim").first.click()
    page.wait_for_timeout(120)
    shown = text(page, price)
    check("R6 예측 단추를 누르면 굴리지 않는다", not rolls(page) and shown != after, [after, shown])
    context.close()


def reduced(browser, server):
    account = asset_tab.sample()
    context, page = open_page(browser, server, account, "reduce")
    capture.turn(page, "자산")
    asset_tab.tab(page, 0)
    rolls(page)
    cum = f"{CARDS} .slide:nth-child(1) .val b"
    before = text(page, cum)
    account["performance"]["sectors"]["nasdaq"]["returns"]["now"]["realized"] += 0.0123
    refresh(page, 400)
    check("R7 굴림을 줄인 기기는 바로 바꾼다", not rolls(page) and text(page, cum) != before, [before, text(page, cum)])
    context.close()


def main():
    server = capture.Server(capture.REPO, capture.REPO)
    with sync_playwright() as p:
        browser = capture.launch(p)
        for run in (asset, trades, outlook, reduced):
            run(browser, server)
        browser.close()
    check("화면 오류 없음", not server.errors, server.errors[:3])
    print("FAILED" if FAILS else "OK", FAILS)
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
