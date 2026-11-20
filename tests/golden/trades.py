"""거래 내역 화면(T1~T4)의 동작 시험. 출처 스티커, 목표 배율 갭, 출처 필터 드롭다운, 금액 단위 단추, 기간 투자액을 연다.

    python3 tests/golden/trades.py --data /tmp/dp-u4/out --shots /tmp/at-u2

`--data`는 리포트 자료 `r/`가 있는 폴더이고 앱 코드는 저장소 루트의 빌드(`app.html`)를 쓴다. 거래는 모두 지어낸 SAMPLE 값이다.
SAMPLE 거래 내역(나스닥, 목표 배율과 거래 직후 배율은 블록마다 적는다):
    11/18 LLM  QLD 매수 $700.00   목표 1.9, 직후 1.6  -> 갭 +0.300배
    11/18 일반 TQQQ 매수 $300.00  목표 1.9, 직후 1.75 -> 갭 +0.150배 (같은 날 두 출처라 카드가 둘)
    11/17 LLM  QQQ 매도 $400.00   목표 1.5, 직후 1.62 -> 갭 −0.120배
    11/14 일반 QLD 매도 $140.00   목표 1.55, 직후 1.5 -> 갭 +0.050배
기대 기간 투자액: 전체 $460.00(카드 4), LLM 매수 $300.00(카드 2), 일반 매수 $160.00(카드 2).
필터 시험은 기기에 달러 단위를 적어 두고 연다. 원 단위의 기대값은 SAMPLE 계좌 요약의 환율 1,330.5원으로 바꾼 값이다.
"""
import argparse
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

import capture
import fixtures

FAILS = []


def check(name: str, ok: bool, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILS.append(name)


def fill(symbol, side, quantity, price, day, time):
    return {"symbol": symbol, "side": side, "quantity": quantity, "price": price, "amount": round(quantity * price, 2), "at": f"{day}T{time}:30+09:00", "filled": True}


def block(day, source, target, after, executions, reason=None):
    return {"date": day, "sector": "nasdaq", "source": source, "state": "executed", "current": 1.5, "target": target, "anchor": 1.5,
            "reason": reason, "orders": [], "executions": executions, "after": after}


SAMPLE = [
    block("2026-11-18", "manual", 1.9, 1.75, [fill("TQQQ", "BUY", 5, 60.0, "2026-11-18", "23:40")]),
    block("2026-11-18", "llm", 1.9, 1.6, [fill("QLD", "BUY", 10, 70.0, "2026-11-18", "23:31")], "고용 지표가 약해 하락 쪽 경로가 줄었다."),
    block("2026-11-17", "llm", 1.5, 1.62, [fill("QQQ", "SELL", 1, 400.0, "2026-11-17", "23:31")]),
    block("2026-11-14", "manual", 1.55, 1.5, [fill("QLD", "SELL", 2, 70.0, "2026-11-14", "23:35")]),
]
# 11/19 집행 요청(아직 집행 전). 필터와 관계없이 집행 요청 절에 남는다.
OPEN = {"date": fixtures.TODAY, "sector": "nasdaq", "source": "llm", "state": "pending", "current": 1.61, "target": 1.82, "anchor": 1.5,
        "run_at": None, "reason": "금리 인하 기대가 커졌다.", "orders": [{"symbol": "QLD", "side": "BUY", "krw": 1.0e6, "usd": 750.0, "shares": 10.0}],
        "executions": [], "after": None}
EXPECT = {"all": (4, "$460.00"), "llm": (2, "$300.00"), "manual": (2, "$160.00")}
KRW = {"sum": "612,030원", "row": "931,350원", "order": ("1,000,000원", "약 $750.00")}
GAPS = [("2026-11-18", "일반 매수", "+0.150배"), ("2026-11-18", "LLM 매수", "+0.300배"), ("2026-11-17", "LLM 매수", "−0.120배"), ("2026-11-14", "일반 매수", "+0.050배")]


def account(blocks, with_open=True) -> dict:
    out = fixtures.account()
    run_at = out["trades"]["request"]["run_at"]
    out["trades"]["sectors"]["nasdaq"] = ([{**OPEN, "run_at": run_at}] if with_open else []) + blocks
    if not with_open:
        out["trades"]["request"]["sectors"]["nasdaq"]["order_count"] = 0
    return out


def open_page(p, data: Path, kept: dict, unit="USD"):
    server = capture.Server(capture.REPO, data)
    browser = capture.launch(p)
    context = browser.new_context(viewport={"width": 390, "height": 1000}, device_scale_factor=1, reduced_motion="reduce", locale="ko-KR", timezone_id="Asia/Seoul")
    context.clock.set_fixed_time(fixtures.NOW)
    context.add_init_script(capture.mock(1))
    context.add_init_script("try { localStorage.setItem('asset', '1'); } catch {}")
    if unit:
        context.add_init_script(f"try {{ localStorage.setItem('asset-view', JSON.stringify({{ unit: '{unit}', card: 2 }})); }} catch {{}}")
    context.route("**/*", server.handler({}, kept))
    page = context.new_page()
    page.on("pageerror", lambda e: server.errors.append(f"pageerror: {str(e)[:300]}"))
    page.on("console", lambda m: m.type == "error" and server.errors.append(f"console: {m.text[:300]}"))
    page.goto(f"{capture.APP}?r={fixtures.BASE_KEY}&trades=nasdaq", wait_until="networkidle")
    page.wait_for_selector(".trade-sum", timeout=15000)
    capture.settle(page)
    return server, browser, page


def cards(page):
    return page.evaluate("""() => [...document.querySelectorAll('.trade:not(:has(.act))')].map((c) => ({
      date: c.dataset.date, sticker: c.querySelector('.badge')?.textContent ?? null, lev: c.querySelector('.lev')?.textContent ?? null,
      rows: [...c.querySelectorAll('.asset-item')].map((r) => r.innerText.replace(/\\s+/g, ' '))}))""")


def pick(page, label):
    page.locator(".trade-head .pick > button").click()
    page.locator(".trade-head .menu button", has_text=label).click()
    capture.settle(page, 300)


def state(page):
    return {"cards": cards(page), "sum": page.locator(".trade-sum").inner_text().replace("\n", " "),
            "on": page.locator(".trade-head .pick > button").inner_text(), "open": page.locator(".trade .act").count(),
            "unit": page.locator(".trade-head [data-unit].on").inner_text(), "text": page.locator(".trades-page").inner_text()}


def gaps(page):
    """화면 그림에서 제목 줄의 단추 아래부터 "기간 투자액" 글씨 위까지, 큰 값 글씨 아래부터 첫 거래 카드 위까지 빈 줄 수(px)를 센다."""
    top, bottom, left, right = page.evaluate("""() => {
      const tools = document.querySelector('.trade-head .tools').getBoundingClientRect(), card = document.querySelector('.trade-sum ~ .trade').getBoundingClientRect();
      return [Math.round(tools.bottom), Math.round(card.top), Math.round(card.left), Math.round(card.right)];
    }""")
    shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    bg = shot.getpixel((2, top))
    inked = [y for y in range(top, bottom) if any(max(abs(a - b) for a, b in zip(shot.getpixel((x, y)), bg)) > 40 for x in range(left, right))]
    return inked[0] - top, bottom - inked[-1] - 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--shots", required=True)
    args = parser.parse_args()
    data, shots = Path(args.data), Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        server, browser, page = open_page(p, data, account(SAMPLE))
        s = state(page)
        menu = page.locator(".trade-head .menu")
        check("a 드롭다운은 전체를 쓰고 목록을 접어 둔다", s["on"] == "전체" and not menu.is_visible())
        page.locator(".trade-head .pick > button").click()
        check("a 드롭다운을 누르면 필터 세 개를 펼친다", menu.is_visible() and menu.locator("button").all_inner_texts() == ["전체", "LLM 매수", "일반 매수"]
              and page.locator(".trade-head .pick > button").get_attribute("aria-expanded") == "true")
        page.mouse.click(20, 900)
        check("a 목록 밖을 누르면 접는다", not menu.is_visible())
        check("a 기간 투자액 이름이 값 위에 있다", s["sum"].startswith("기간 투자액"), s["sum"])
        check("a 카드 스티커와 갭이 SAMPLE 기대값", [(c["date"], c["sticker"], c["lev"]) for c in s["cards"]] == [(d, k, f"목표 배율 갭 {g}") for d, k, g in GAPS],
              [(c["date"], c["sticker"], c["lev"]) for c in s["cards"]])
        check("a 체결·미체결 글씨가 없음", "체결" not in s["text"], s["text"][:120])
        check("a 행 오른쪽에 시각만", all(r.endswith(("23:31", "23:40", "23:35")) for c in s["cards"] for r in c["rows"]), [c["rows"] for c in s["cards"]])
        check("a 현재 → 목표 줄이 없음", "→" not in s["text"])
        check("a 집행 요청 카드(승인 단추)와 LLM 스티커", s["open"] == 1 and page.locator(".trade:has(.act) .badge").inner_text() == "LLM 매수")
        for name, label in (("all", "전체"), ("llm", "LLM 매수"), ("manual", "일반 매수"), ("all", "전체")):
            pick(page, label)
            s = state(page)
            count, total = EXPECT[name]
            check(f"b 필터 {label}: 카드 수와 기간 투자액", len(s["cards"]) == count and total in s["sum"] and s["on"] == label and s["open"] == 1, (len(s["cards"]), s["sum"]))
            if name == "llm":
                check("b 필터 LLM 매수: 스티커가 모두 LLM 매수", {c["sticker"] for c in s["cards"]} == {"LLM 매수"})
                page.locator(".trade-head").scroll_into_view_if_needed()
                capture.settle(page, 400)
                page.evaluate("scrollTo(0, document.querySelector('.trade-head').getBoundingClientRect().top + scrollY - 70)")
                capture.settle(page, 400)
                page.screenshot(path=str(shots / "trades-llm.png"))
                above, below = gaps(page)
                check("b 기간 투자액 묶음의 위아래 여백이 같다", abs(above - below) <= 1, (above, below))
        check("b 필터를 고르면 목록을 접는다", not menu.is_visible())
        page.locator(".trade-head [data-unit='KRW']").click()
        capture.settle(page, 300)
        s = state(page)
        check("e 원 단위: 기간 투자액과 체결 금액을 환율로 바꾼다", s["unit"] == "원" and KRW["sum"] in s["sum"] and KRW["row"] in s["cards"][1]["rows"][0], (s["sum"], s["cards"][1]["rows"]))
        order = page.locator(".trade:has(.act) .asset-item").inner_text()
        check("e 원 단위: 보낼 주문은 원화 금액 아래 달러 어림값", all(v in order for v in KRW["order"]) and order.index("원") < order.index("$"), order)
        kept = page.evaluate("JSON.parse(localStorage.getItem('asset-view'))")
        check("e 단위를 기기에 적고 그림 카드 번호는 지킨다", kept == {"unit": "KRW", "card": 2}, kept)
        page.screenshot(path=str(shots / "trades-krw.png"))
        page.locator(".trade-head [data-unit='USD']").click()
        capture.settle(page, 300)
        order = page.locator(".trade:has(.act) .asset-item").inner_text()
        check("e 달러 단위: 보낼 주문은 달러 어림값 아래 원화 금액", "$460.00" in state(page)["sum"] and order.index("$") < order.index("1,000,000원"), order)
        check("c 오류·외부 요청 0건", not server.errors and not server.escaped, (server.errors, server.escaped))
        browser.close()

        # 옛 모양 블록(출처와 `after` 없음)도 깨지지 않고 전체에서만 보인다.
        old = [{k: v for k, v in b.items() if k not in ("source", "after")} for b in SAMPLE]
        server, browser, page = open_page(p, data, account(old, with_open=False), unit=None)
        check("d 기기에 적은 단위가 없으면 원 단위로 연다", state(page)["unit"] == "원" and KRW["sum"] in state(page)["sum"], state(page)["sum"])
        s = state(page)
        check("d 옛 블록: 카드 4개, 스티커와 갭 줄 없음", len(s["cards"]) == 4 and all(c["sticker"] is None and c["lev"] is None for c in s["cards"]), s["cards"][:1])
        pick(page, "LLM 매수")
        check("d 옛 블록: LLM 매수 필터는 비어 있음", state(page)["cards"] == [] and "거래 내역이 없다" in state(page)["text"])
        check("d 오류 0건", not server.errors, server.errors)
        browser.close()
    print("FAILED" if FAILS else "ALL PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
