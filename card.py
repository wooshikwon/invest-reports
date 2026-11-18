#!/usr/bin/env python3
"""card — `invest-reports` 미니 앱(`app.html`)이 그린 1년 예측 카드를 그림으로 찍는다. `run-with-notify.sh`가 이 그림을 공개 채널로 보낸다.

사용법: python3 card.py --key 20261112-nasdaq --out ~/obsidian-vault/routine/invest/.../assets/card-nasdaq.png

`build.py`가 `r/{key}/`에 공개본을 만든 뒤 실행한다. 이 저장소를 임시 포트의 로컬 서버로 열어 그 리포트를 휴대폰 폭(390px)으로 그리고,
요약 절 카드 묶음의 "예측" 탭을 눌러 예측 카드로 넘기고, 처음 열린 3개월 기간에서 − 단추를 두 번 눌러 1년 범위로 늘린 뒤,
그 카드(`.gauge.summary`)를 카드 위 끝부터 기간 단추(`.zoom`) 위까지 잘라 3배 해상도로 저장한다. 새 브라우저로 열므로 그림 종류는 처음 값인 선 그림이다.
GitHub Pages 배포를 기다리지 않으므로 게시가 늦거나 실패한 날에도 그림을 만든다. 페이지 오류가 나거나 카드가 그려지지 않으면 0이 아닌 값으로 끝난다.
"""

import argparse
import functools
import glob
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
CHROME = "/home/ubuntu/.cache/ms-playwright/chromium-*/chrome-linux*/chrome"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def shoot(key: str, out: Path) -> list[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=sorted(glob.glob(CHROME))[-1])
            page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3)
            page.on("pageerror", lambda e: errors.append(str(e)))

            def failed(response):
                if response.status >= 400:
                    errors.append(f"{response.status} {response.url}")

            page.on("response", failed)
            page.goto(f"http://127.0.0.1:{server.server_port}/app.html?r={key}")
            cards = page.locator(".carousel.cards")
            cards.locator(".gauge.summary .zoom").first.wait_for(timeout=20000)
            names = cards.locator(".tabs button").all_text_contents()
            assert "예측" in names, f"예측 탭이 없다: {names}"
            cards.scroll_into_view_if_needed()
            cards.locator(".tabs button").nth(names.index("예측")).click()
            gauge = cards.locator(".slide").nth(names.index("예측")).locator(".gauge.summary")
            # 기간은 3년, 2년, 1년, 6개월, 3개월 다섯 단계다. 화면을 옮기지 않도록 누르는 이벤트만 보낸다.
            for _ in range(2):
                gauge.locator('.zoom button[aria-label="기간 늘리기"]').dispatch_event("click")
            # 예측 카드로 넘어가는 움직임과 카드의 선과 범위가 그려지는 움직임이 끝난 뒤 찍는다.
            page.wait_for_timeout(2000)
            card = gauge.bounding_box()
            zoom = gauge.locator(".zoom").bounding_box()
            assert card and zoom
            out.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out), clip={"x": card["x"], "y": card["y"],
                                                 "width": card["width"], "height": zoom["y"] - card["y"]})
            browser.close()
    finally:
        server.shutdown()
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="`invest-reports` 미니 앱의 1년 예측 카드를 그림으로 찍는다")
    parser.add_argument("--key", required=True, help="리포트 키 YYYYMMDD-지수")
    parser.add_argument("--out", required=True, help="저장할 PNG 경로")
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    errors = shoot(args.key, out)
    if errors:
        out.unlink(missing_ok=True)
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
