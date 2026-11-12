#!/usr/bin/env python3
"""card — `invest-reports` 미니 앱(`app.html`)이 그린 1년 주가와 예측 카드를 그림으로 찍는다. `run-with-notify.sh`가 이 그림을 공개 채널로 보낸다.

사용법: python3 card.py --key 20261112-nasdaq --out ~/obsidian-vault/routine/invest/.../assets/card-nasdaq.png

`build.py`가 `r/{key}/`에 공개본을 만든 뒤 실행한다. 이 저장소를 임시 포트의 로컬 서버로 열어 그 리포트를 휴대폰 폭(390px)으로 그리고,
첫 카드(`.gauge.summary`)를 카드 위 끝부터 기간 단추(`.zoom`) 위까지 잘라 3배 해상도로 저장한다. 처음 열린 기간이 1년이므로 그림은 1년 범위다.
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
            gauge = page.locator(".gauge.summary").first
            gauge.locator(".zoom").wait_for(timeout=20000)
            gauge.scroll_into_view_if_needed()
            # 카드의 선과 범위가 그려지는 움직임이 끝난 뒤 찍는다.
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
    parser = argparse.ArgumentParser(description="`invest-reports` 미니 앱의 1년 주가와 예측 카드를 그림으로 찍는다")
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
