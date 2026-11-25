"""거래 내역 화면(T1~T4)의 동작 시험. 출처 스티커, 출처 필터 드롭다운, 금액 단위 단추, 기간 투자액, 조회 기간 달력을 연다.

    python3 tests/golden/trades.py --data /tmp/dp-u4/out --shots /tmp/at-u2

`--data`는 리포트 자료 `r/`가 있는 폴더이고 앱 코드는 저장소 루트의 빌드(`app.html`)를 쓴다. 거래는 모두 지어낸 SAMPLE 값이다.
SAMPLE 거래 내역(나스닥):
    11/18 LLM  QLD 매수 $700.00
    11/18 일반 TQQQ 매수 $300.00 (같은 날 두 출처라 카드가 둘)
    11/17 LLM  QQQ 매도 $400.00
    11/14 일반 QLD 매도 $140.00
기대 기간 투자액: 전체 $460.00(카드 4), LLM 매수 $300.00(카드 2), 일반 매수 $160.00(카드 2).
필터 시험은 기기에 달러 단위를 적어 두고 연다. 원 단위의 기대값은 SAMPLE 계좌 요약의 환율 1,330.5원으로 바꾼 값이다.
조회 기간은 처음에 8/19~11/19(최근 3개월)이다. 달력에서 11/16~11/18을 고르고 확인을 누르면 카드 3개, 기간 투자액 $600.00이다.
그 기간에 LLM 매수 필터를 고른 뒤 다시 열면 기기에 적은 필터와 조회 기간으로 연다.
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
STICKERS = [("2026-11-18", "일반 매수"), ("2026-11-18", "LLM 매수"), ("2026-11-17", "LLM 매수"), ("2026-11-14", "일반 매수")]


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
        context.add_init_script(f"try {{ localStorage.getItem('asset-view') || localStorage.setItem('asset-view', JSON.stringify({{ unit: '{unit}' }})); }} catch {{}}")
    context.route("**/*", server.handler({}, kept))
    page = context.new_page()
    page.on("pageerror", lambda e: server.errors.append(f"pageerror: {str(e)[:300]}"))
    page.on("console", lambda m: m.type == "error" and server.errors.append(f"console: {m.text[:300]}"))
    page.goto(f"{capture.APP}?r={fixtures.BASE_KEY}&trades=nasdaq", wait_until="networkidle")
    page.wait_for_selector(".trade-sum", timeout=15000)
    capture.settle(page)
    return server, browser, page


def cards(page):
    return page.evaluate("""() => [...document.querySelectorAll('.trade:not(:has(.act)):not(.gate)')].map((c) => ({
      date: c.dataset.date, sticker: c.querySelector('.badge')?.textContent ?? null,
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
    """화면 그림에서 제목 줄의 단추 아래부터 기간 투자액 글씨 위까지, 기간 투자액 글씨 아래부터 기간 단추 위까지 빈 줄 수(px)를 세고,
    기간 단추 아래부터 첫 거래 카드 위까지와 첫 두 카드 사이의 거리(px)를 잰다."""
    top, bottom, left, right, after, between = page.evaluate("""() => {
      const r = (q) => document.querySelector(q).getBoundingClientRect(), [one, two] = [...document.querySelectorAll('.trade-sum ~ .trade')].map((c) => c.getBoundingClientRect());
      const value = r('.trade-sum b'), period = r('.trade-sum .period');
      return [Math.round(r('.trade-head .tools').bottom), Math.round(period.top), Math.round(value.left), Math.round(value.right), Math.round(one.top - period.bottom), Math.round(two.top - one.bottom)];
    }""")
    shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    bg = shot.getpixel((2, top))
    inked = [y for y in range(top, bottom) if any(max(abs(a - b) for a, b in zip(shot.getpixel((x, y)), bg)) > 40 for x in range(left, right))]
    return inked[0] - top, bottom - inked[-1] - 1, after, between


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
        check("a 기간 투자액 이름 없이 기간 단추에 최근 3개월을 쓴다", s["sum"].endswith("8.19 ~ 11.19") and "기간 투자액" not in s["sum"], s["sum"])
        box = page.evaluate("""() => { const [row, value, period] = ['.trade-sum', '.trade-sum b', '.trade-sum .period'].map((q) => document.querySelector(q).getBoundingClientRect());
          return { below: period.top - value.bottom, right: Math.round(row.right - period.right), left: Math.round(value.left - row.left) }; }""")
        check("a 기간 단추는 기간 투자액 아래 줄 오른쪽 끝에 있다", box["below"] >= 0 and box["right"] == 0 and box["left"] == 0, box)
        check("a 카드 스티커가 SAMPLE 기대값", [(c["date"], c["sticker"]) for c in s["cards"]] == STICKERS, [(c["date"], c["sticker"]) for c in s["cards"]])
        check("a 목표 배율 갭 줄이 없음", "배율 갭" not in s["text"], s["text"][:120])
        check("a 체결·미체결 글씨가 없음", "체결" not in s["text"], s["text"][:120])
        check("a 행 오른쪽에 시각만", all(r.endswith(("23:31", "23:40", "23:35")) for c in s["cards"] for r in c["rows"]), [c["rows"] for c in s["cards"]])
        check("a 현재 → 목표 줄이 없음", "→" not in s["text"])
        check("a 집행 요청 카드(승인 단추)는 신호등 머리에 리밸런싱 주문 요청을 쓴다", s["open"] == 1 and page.locator(".trade:has(.act) .top.ask b").inner_text().endswith(" 리밸런싱 주문 요청"),
              page.locator(".trade:has(.act) .top").inner_text())
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
                above, below, after, between = gaps(page)
                check("b 기간 투자액 글씨는 제목 줄과 기간 단추 사이의 가운데에 있다", abs(above - below) <= 1, (above, below))
                check("b 기간 단추와 첫 카드 사이는 카드 사이와 같다", after == between, (after, between))
        check("b 필터를 고르면 목록을 접는다", not menu.is_visible())
        page.locator(".trade-head [data-unit='KRW']").click()
        capture.settle(page, 300)
        s = state(page)
        check("e 원 단위: 기간 투자액과 체결 금액을 환율로 바꾼다", s["unit"] == "원" and KRW["sum"] in s["sum"] and KRW["row"] in s["cards"][1]["rows"][0], (s["sum"], s["cards"][1]["rows"]))
        order = page.locator(".trade:has(.act) .asset-item").inner_text()
        check("e 원 단위: 보낼 주문은 원화 금액 아래 달러 어림값", all(v in order for v in KRW["order"]) and order.index("원") < order.index("$"), order)
        kept = page.evaluate("JSON.parse(localStorage.getItem('asset-view'))")
        check("e 단위를 기기에 적고 총 자산·판단 보기·금액가중 단추, 수익률 기준일, 필터와 조회 기간은 지킨다",
              kept == {"unit": "KRW", "whole": False, "judge": True, "money": False, "since": None, "filter": "all", "period": None}, kept)
        page.screenshot(path=str(shots / "trades-krw.png"))
        page.locator(".trade-head [data-unit='USD']").click()
        capture.settle(page, 300)
        order = page.locator(".trade:has(.act) .asset-item").inner_text()
        check("e 달러 단위: 보낼 주문은 달러 어림값 아래 원화 금액", "$460.00" in state(page)["sum"] and order.index("$") < order.index("1,000,000원"), order)
        sheet, day = page.locator(".period-card"), lambda d: page.locator(f'.period-card [data-day="{d}"]')
        marked = lambda: (page.locator(".period-card .start").get_attribute("data-day"), [e.get_attribute("data-day") for e in page.locator(".period-card .end").all()])
        month = lambda: page.locator(".period-card .month h4").inner_text()
        seen = lambda d: page.evaluate("(d) => { const c = document.querySelector(`.period-card [data-day='${d}']`).getBoundingClientRect(), t = document.querySelector('.period-card .months').getBoundingClientRect();"
                                       " return c.left >= t.left - 1 && c.right <= t.right + 1; }", d)
        ok = page.locator(".period-card .ok")
        page.locator(".trade-sum .period").click()
        capture.settle(page, 300)
        check("f 달력은 이번 달 한 달을 보이고 최근 3개월을 칠하고 오늘 뒤 날짜를 끈다", sheet.is_visible() and month() == "2026년 11월" and seen(fixtures.TODAY) and not seen("2026-10-31")
              and marked() == ("2026-08-19", [fixtures.TODAY]) and day("2026-11-20").is_disabled() and not day(fixtures.TODAY).is_disabled()
              and page.locator(".period-card .next").is_disabled() and ok.is_enabled(), (month(), marked()))
        page.screenshot(path=str(shots / "trades-calendar.png"))
        page.locator(".period-card .prev").click()
        capture.settle(page, 600)
        check("f 앞 달 꺽쇠는 한 달을 넘긴다", month() == "2026년 10월" and seen("2026-10-31") and not seen(fixtures.TODAY), month())
        track = page.locator(".period-card .months").bounding_box()
        page.mouse.move(track["x"] + track["width"] - 20, track["y"] + 60)
        page.evaluate("document.querySelector('.period-card .months').scrollBy({ left: document.querySelector('.period-card .months').clientWidth })")
        capture.settle(page, 600)
        check("f 옆으로 밀면 한 달씩 넘긴다", month() == "2026년 11월" and seen(fixtures.TODAY), month())
        day("2026-11-17").click()
        check("f 시작 날짜만 고르면 확인 단추가 꺼진다", marked() == ("2026-11-17", []) and ok.is_disabled(), marked())
        day("2026-11-16").click()
        check("f 시작 날짜보다 앞을 누르면 시작 날짜를 다시 고른다", sheet.is_visible() and marked() == ("2026-11-16", []), marked())
        day("2026-11-18").click()
        capture.settle(page, 400)
        check("f 끝 날짜를 눌러도 확인 전에는 기간을 바꾸지 않는다", sheet.is_visible() and marked() == ("2026-11-16", ["2026-11-18"]) and ok.is_enabled()
              and state(page)["sum"].endswith("8.19 ~ 11.19"), state(page)["sum"])
        page.screenshot(path=str(shots / "trades-calendar-pick.png"))
        ok.click()
        capture.settle(page, 500)
        s = state(page)
        check("f 확인을 누르면 기간을 바꾸고 달력을 닫는다", sheet.count() == 0 and len(s["cards"]) == 3 and "$600.00" in s["sum"] and s["sum"].endswith("11.16 ~ 11.18")
              and s["open"] == 1, (len(s["cards"]), s["sum"]))
        page.screenshot(path=str(shots / "trades-period.png"))
        pick(page, "LLM 매수")
        kept = page.evaluate("JSON.parse(localStorage.getItem('asset-view'))")
        check("g 고른 필터와 조회 기간을 기기에 적는다", kept["filter"] == "llm" and kept["period"] == {"start": "2026-11-16", "end": "2026-11-18"}, kept)
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".trade-sum", timeout=15000)
        capture.settle(page)
        s = state(page)
        check("g 다시 열면 적어 둔 필터와 조회 기간으로 연다", s["on"] == "LLM 매수" and s["sum"].endswith("11.16 ~ 11.18"), (s["on"], s["sum"]))
        pick(page, "전체")
        page.locator(".trade-sum .period").click()
        day("2026-11-10").click()
        day("2026-11-12").click()
        page.mouse.click(5, 5)
        check("f 고른 기간은 달력 밖을 누르면 버리고 닫는다", sheet.count() == 0 and state(page)["sum"].endswith("11.16 ~ 11.18"))
        page.locator(".trade-sum .period").click()
        page.locator(".period-card .reset").click()
        capture.settle(page, 300)
        check("f 최근 3개월 단추는 고른 기간만 처음 기간으로 돌린다", sheet.is_visible() and marked() == ("2026-08-19", [fixtures.TODAY]) and state(page)["sum"].endswith("11.16 ~ 11.18"), marked())
        ok.click()
        capture.settle(page, 300)
        s = state(page)
        check("f 확인을 누르면 처음 기간으로 돌아간다", sheet.count() == 0 and len(s["cards"]) == 4 and "$460.00" in s["sum"] and s["sum"].endswith("8.19 ~ 11.19"), s["sum"])
        check("g 최근 3개월로 돌린 기간은 빈 값으로 적는다", page.evaluate("JSON.parse(localStorage.getItem('asset-view')).period") is None)
        check("c 오류·외부 요청 0건", not server.errors and not server.escaped, (server.errors, server.escaped))
        browser.close()

        # 옛 모양 블록(출처와 `after` 없음)도 깨지지 않고 전체에서만 보인다.
        old = [{k: v for k, v in b.items() if k not in ("source", "after")} for b in SAMPLE]
        server, browser, page = open_page(p, data, account(old, with_open=False), unit=None)
        check("d 기기에 적은 단위가 없으면 원 단위로 연다", state(page)["unit"] == "원" and KRW["sum"] in state(page)["sum"], state(page)["sum"])
        s = state(page)
        check("d 옛 블록: 카드 4개, 스티커 없음", len(s["cards"]) == 4 and all(c["sticker"] is None for c in s["cards"]), s["cards"][:1])
        pick(page, "LLM 매수")
        check("d 옛 블록: LLM 매수 필터는 비어 있음", state(page)["cards"] == [] and "거래 내역이 없다" in state(page)["text"])
        check("d 오류 0건", not server.errors, server.errors)
        browser.close()
    print("FAILED" if FAILS else "ALL PASS", FAILS)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
