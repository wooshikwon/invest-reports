"""이슈 본문 소제목(`h5`)의 동작 시험. 소제목 두 개를 둔 이슈의 상세 화면, 이슈 목록 상자의 미리보기 글, 히스토리 상자에서 앞 날짜를 고른 화면을 연다.

    python3 tests/golden/subhead.py --data /tmp/sn-u3/sample --shots /tmp/sn-u3/shots

`--data`는 가장 늦은 리포트가 2026-11-19 나스닥인 리포트 자료이고, 그 리포트와 2026-11-18 나스닥 리포트의 `ISSUE`번 이슈는 본문에 소제목(`#####`)을 두 개씩 둔 SAMPLE이다.
두 이슈는 같은 사안이라 2026-11-19 이슈의 히스토리 상자에 2026-11-18 줄이 있다. 소제목 글은 `SUBHEADS`에 날짜마다 적는다. 화면 값은 모두 지어낸 값이다.
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import capture
import fixtures

KEY = "20261119-nasdaq"
ISSUE = 2
SUBHEADS = {"2026-11-19": ["매출과 이익 추정치", "지수와 AI 주식"], "2026-11-18": ["내년 수요 전망", "주가에 반영된 기대"]}
FAILS = []

# 보이는 이슈 문단의 자식 차례. 문단은 `p`, 소제목은 `h5:글`, 머리 줄은 `lead`, 그래프 카드는 `chart`, 그 밖의 요소는 빼고 적는다.
BLOCKS = """() => [...document.querySelector('.issue-page.on').children].map((node) =>
  node.matches('h4') && node.querySelector('mark')?.textContent.trim() === '이슈 해설' ? 'lead'
  : node.matches('h5') ? 'h5:' + node.textContent.trim() : node.matches('figure.issue-chart') ? 'chart' : node.matches('p:not(.written)') ? 'p' : null).filter(Boolean)"""


def check(name: str, ok: bool, detail=""):
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        FAILS.append(name)


def subheads(blocks: list[str]) -> list[str]:
    return [block[3:] for block in blocks if block.startswith("h5:")]


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

        page = run.open(f"?r={KEY}")
        previews = page.evaluate("() => [...document.querySelectorAll('.issue-list .pick')].map((pick) => pick.textContent)")
        found = [text for text in previews if any(head in text for heads in SUBHEADS.values() for head in heads)]
        check("목록 블록의 미리보기 글에 소제목이 없다", len(previews) > ISSUE and not found, f"상자 {len(previews)}개, 소제목이 든 상자 {len(found)}개")
        run.close()

        page = run.open(f"?r={KEY}&issue={ISSUE}")
        today = page.evaluate(BLOCKS)
        check("이슈 상세에 소제목 h5 두 개가 본문 순서대로 있다", subheads(today) == SUBHEADS["2026-11-19"]
              and today.index("lead") < today.index(f"h5:{SUBHEADS['2026-11-19'][0]}") < today.index(f"h5:{SUBHEADS['2026-11-19'][1]}")
              and today.count("p") >= 4 and today[-1] == "p", " ".join(today))
        check("그래프 카드는 소제목 바로 앞뒤에 없다", "chart" in today and all(not today[k + side].startswith("h5:") for k, block in enumerate(today)
                                                                       if block == "chart" for side in (-1, 1) if 0 <= k + side < len(today)))
        capture.top(page, page.locator(".issue-page.on > h5"), 140)
        page.screenshot(path=str(shots / "issue-subhead.png"))

        page.locator(".issue-page.on .history .entry", has_text="11/18").first.click()
        capture.settle(page, 600)
        past = page.evaluate(BLOCKS)
        check("히스토리에서 앞 날짜를 고르면 소제목도 그날의 것으로 바뀐다", subheads(past) == SUBHEADS["2026-11-18"], " ".join(past))
        page.locator(".issue-page.on .history .entry", has_text="11/19").first.click()
        capture.settle(page, 600)
        check("오늘 줄을 다시 고르면 오늘 소제목으로 돌아온다", subheads(page.evaluate(BLOCKS)) == SUBHEADS["2026-11-19"])
        run.close()
        browser.close()
    check("페이지 오류와 바깥 요청이 없다", not server.errors and not server.escaped, f"{server.errors[:3]} {server.escaped[:3]}")
    print(f"{len(FAILS)} FAIL" if FAILS else "ALL PASS", f"· 스크린숏 {shots / 'issue-subhead.png'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
