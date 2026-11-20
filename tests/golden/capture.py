"""미니 앱 화면 열한 개를 띄워 화면마다 `main`의 정규화한 HTML과 PNG를 저장한다.

    python3 tests/golden/capture.py --ref v0.8 --out ~/data/invest-reports/golden/v0.8
    python3 tests/golden/capture.py --ref /path/to/built --out /tmp/golden-new --only asset,trades
    python3 tests/golden/capture.py --ref /path/to/built --out /tmp/golden-split --split

`--ref`는 git 태그·커밋이거나 `app.html`(과 `assets/`, `maps/`)이 있는 폴더이고, 앱 코드만 거기서 읽는다. 리포트 자료 `r/`는 늘
`--data`(기본 `v0.8`)의 git 시점에서 읽는다. 두 쪽 모두 git 시점이면 `git archive`로 임시 폴더에 풀고 끝나면 지운다.
`--split`이면 리포트 자료를 `fixtures.split`으로 build.py가 지금 쓰는 모양으로 바꿔, 이슈 과거 맥락과 요약 카드 값을 `history.json`·`cards.json`에서 받는 길로 연다.

모든 요청은 가짜 주소 `https://app.local/`과 아래 네 곳만 답하고, 나머지 외부 요청은 abort한 뒤 실패로 끝낸다.
- `telegram.org`: 빈 스크립트. 텔레그램 WebApp은 init 스크립트가 흉내 낸다(사용자 ID는 1이나 2).
- `invest-account`: initData의 사용자가 1이면 `fixtures.account()`의 지어낸 계좌 요약과 `/decide` 결정, 아니면 403. 그래서 사용자 1이 본인이고 사용자 2는 남이다.
- `invest-live`: `GET /`은 세 값을 묶은 객체, `GET /{이름}`은 그 값 하나(`fixtures.live()`).
- `invest-news`: 공개 읽기 네 경로를 `fixtures.news_answer()`의 SAMPLE 기사로 답한다. `Server.news_down`이 참이면 답하지 않고 abort한다.
소유자 해시 상수 `ASSET_OWNER`를 가진 앱 코드(v0.8)는 서빙할 때 그 상수를 sha256("1")로 바꾼다.
시각은 `fixtures.NOW`로 고정하고(`clock.set_fixed_time`), 화면은 390×1000, 배율 1, `reduced_motion`으로 연다.
화면을 여는 절차는 화면 이름마다 함수 하나이고 `SCREENS`에 이름 순서대로 모인다. 차이를 받아들이는 선택자는 `compare.ALLOW`에 둔다.
"""
import argparse
import glob
import hashlib
import json
import mimetypes
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from playwright.sync_api import sync_playwright

import compare
import fixtures

REPO = Path(__file__).resolve().parents[2]
APP = "https://app.local/app.html"
LIVE_URL = "https://invest-live.wonwooshik.workers.dev"
ASSET_URL = "https://invest-account.wonwooshik.workers.dev"
NEWS_URL = fixtures.NEWS_URL
OWNER_PATTERN = re.compile(r'(ASSET_OWNER\s*=\s*")[0-9a-f]{64}(")')
OWNER_STAND_IN = hashlib.sha256(b"1").hexdigest()
JSON_HEAD = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"}
SETTLE = 1500


def launch(p):
    return p.chromium.launch(executable_path=sorted(glob.glob(str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux*/chrome")))[-1])


def mock(uid: int) -> str:
    """텔레그램 WebApp 흉내. initData의 서명은 가짜이고, 계좌 요청은 가로채므로 검증하지 않는다."""
    return """(() => { const now = Math.floor(Date.now() / 1000); const user = { id: %d, first_name: "t" };
      window.Telegram = { WebApp: { initData: `user=${encodeURIComponent(JSON.stringify(user))}&auth_date=${now}&hash=00`,
        initDataUnsafe: { user, auth_date: now }, ready() {}, expand() {}, onEvent() {}, isVersionAtLeast: () => false,
        HapticFeedback: { impactOccurred() {}, selectionChanged() {}, notificationOccurred() {} },
        safeAreaInset: {}, contentSafeAreaInset: {}, viewportStableHeight: innerHeight } }; })();""" % uid


def checkout(ref: str, keep: list) -> Path:
    """`ref`가 폴더면 그 폴더, 아니면 그 git 시점을 임시 폴더에 푼 경로. 임시 폴더는 `keep`에 더한다."""
    if Path(ref).expanduser().is_dir():
        return Path(ref).expanduser().resolve()
    subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], check=True, stdout=subprocess.DEVNULL)
    target = Path(tempfile.mkdtemp(prefix="ir-golden-"))
    keep.append(target)
    archive = subprocess.Popen(["git", "-C", str(REPO), "archive", ref], stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", str(target)], stdin=archive.stdout, check=True)
    if archive.wait():
        raise SystemExit(f"git archive 실패: {ref}")
    return target


class Server:
    """한 캡처 실행의 요청 응답. 앱 코드는 `code`, 리포트 자료는 `data`에서 읽고, `overlay`의 경로는 그 바이트로 답한다."""

    def __init__(self, code: Path, data: Path):
        self.code, self.data = code, data
        self.live = fixtures.live(data)
        self.escaped, self.errors, self.unpatched = [], [], 0
        self.news_down = False

    def file(self, path: str, overlay: dict) -> bytes | None:
        if path in overlay:
            return overlay[path]
        root = self.data if path.startswith("r/") else self.code
        found = root / path
        if not found.is_file():
            return None
        body = found.read_bytes()
        if found.suffix in (".html", ".js"):
            text, count = OWNER_PATTERN.subn(lambda m: m.group(1) + OWNER_STAND_IN + m.group(2), body.decode("utf-8"))
            self.unpatched += "ASSET_OWNER" in text and not count
            body = text.encode("utf-8")
        return body

    def handler(self, overlay: dict, account: dict):
        def serve(route):
            request = route.request
            url = request.url
            if url.startswith("https://app.local/"):
                path = unquote(urlparse(url).path).lstrip("/")
                body = self.file(path, overlay)
                if body is None:
                    return route.fulfill(status=404, body="")
                return route.fulfill(status=200, body=body, content_type=mimetypes.guess_type(path)[0] or "application/octet-stream")
            if url.startswith("https://telegram.org/"):
                return route.fulfill(status=200, body="", content_type="text/javascript")
            if url.startswith(LIVE_URL):
                if request.method == "OPTIONS":
                    return route.fulfill(status=204, headers=JSON_HEAD)
                name = urlparse(url).path.strip("/")
                value = self.live if not name else self.live.get(name, {})
                return route.fulfill(status=200, body=json.dumps(value), headers=JSON_HEAD)
            if url.startswith(ASSET_URL):
                if request.method == "OPTIONS":
                    return route.fulfill(status=204, headers=JSON_HEAD)
                decide = urlparse(url).path.rstrip("/").endswith("/decide")
                init = json.loads(request.post_data or "{}").get("initData", "") if decide else request.post_data or ""
                if json.loads(parse_qs(init).get("user", ["{}"])[0]).get("id") != 1:
                    return route.fulfill(status=403, body="", headers=JSON_HEAD)
                if decide:
                    return route.fulfill(status=200, body=json.dumps(fixtures.decide(account, request.post_data)), headers=JSON_HEAD)
                return route.fulfill(status=200, body=json.dumps(account), headers=JSON_HEAD)
            if url.startswith(NEWS_URL):
                if self.news_down:
                    return route.abort()
                parsed = urlparse(url)
                status, body, kind = fixtures.news_answer(self.data, unquote(parsed.path).strip("/"), parse_qs(parsed.query))
                return route.fulfill(status=status, body=body, headers={"Access-Control-Allow-Origin": "*", "Content-Type": kind})
            self.escaped.append(urlparse(url).netloc)
            return route.abort()
        return serve


class Run:
    """화면 하나를 여는 데 쓰는 브라우저 문맥을 만든다. 화면 함수는 `open`으로 페이지를 받는다."""

    def __init__(self, browser, server: Server, split: bool = False):
        self.browser, self.server, self.context = browser, server, None
        self.base = fixtures.split(server.data, {}) if split else {}

    def open(self, query: str = "", uid: int = 1, dataset: str = "base"):
        context = self.browser.new_context(viewport={"width": 390, "height": 1000}, device_scale_factor=1, reduced_motion="reduce",
                                           locale="ko-KR", timezone_id="Asia/Seoul")
        context.clock.set_fixed_time(fixtures.NOW)
        context.add_init_script(mock(uid))
        if uid == 1:
            context.add_init_script("try { localStorage.setItem('asset', '1'); } catch {}")
        context.route("**/*", self.server.handler(self.base, fixtures.account()))
        self.context = context
        page = context.new_page()
        page.on("pageerror", lambda error: self.server.errors.append(f"pageerror: {str(error)[:300]}"))
        page.on("console", lambda message: message.type == "error" and self.server.errors.append(f"console: {message.text[:300]}"))
        page.goto(APP + query, wait_until="networkidle")
        settle(page)
        return page

    def close(self):
        if self.context:
            self.context.close()
            self.context = None


def settle(page, wait: int = SETTLE):
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready.then(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))))")
    page.wait_for_timeout(wait)


def top(page, locator, below: int = 90):
    """`locator`의 보이는 첫 요소를 화면 위에서 `below`px 아래(머리 상자 아래)에 둔다."""
    locator.filter(visible=True).first.evaluate("(node, below) => scrollTo(0, node.getBoundingClientRect().top + scrollY - below)", below)
    settle(page, 600)


def turn(page, name: str):
    """아래 내비게이션의 `name` 페이지를 연다."""
    page.locator("nav.jump button", has_text=name).first.click()
    settle(page)
    page.evaluate("scrollTo(0, 0)")
    settle(page, 400)


def latest(run):
    return run.open()


def issue(run):
    return run.open(f"?r={fixtures.BASE_KEY}&issue=1")


def calendar(run):
    page = run.open()
    top(page, page.locator("main h2", has_text="이벤트 캘린더"))
    return page


def past(run):
    return run.open("?r=20261118-nasdaq")


def market(run):
    page = run.open()
    turn(page, "시장")
    top(page, page.locator("main h2", has_text="한 눈에 보기"))
    return page


def stock(run):
    return run.open(f"?r={fixtures.BASE_KEY}&stock=NVDA")


def asset(run):
    page = run.open()
    turn(page, "자산")
    return page


def trades(run):
    return run.open(f"?r={fixtures.BASE_KEY}&trades=nasdaq")


def glossary(run):
    page = run.open(f"?r={fixtures.BASE_KEY}&issue=1")
    term = page.locator("main button.term")
    top(page, term, 400)
    term.filter(visible=True).first.click()
    settle(page, 800)
    return page


def rewind(run):
    page = run.open()
    top(page, page.locator("main .rewind"), 500)
    box = page.locator("main .rewind").filter(visible=True).first
    box.locator(".open").click()
    settle(page, 400)
    box.locator("input[type=range]").evaluate("(range) => { range.value = 45; range.dispatchEvent(new Event('input')); }")
    settle(page, 800)
    return page


def nonowner(run):
    return run.open(uid=2)


SCREENS = {screen.__name__: screen for screen in
           (latest, issue, calendar, past, market, stock, asset, trades, glossary, rewind, nonowner)}


def dom(page) -> str:
    """`main`과, `main` 밖에 떠 있는 말풍선(`body > .bubble`)의 HTML."""
    return page.evaluate("[document.querySelector('main'), ...document.querySelectorAll('body > .bubble')]"
                         ".filter(Boolean).map((node) => node.outerHTML).join('\\n')")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", required=True, help="앱 코드의 git 시점이나 폴더")
    parser.add_argument("--data", default="v0.8", help="리포트 자료 r/의 git 시점이나 폴더")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only", default="", help="쉼표로 가른 화면 이름")
    parser.add_argument("--split", action="store_true", help="리포트 자료를 `fixtures.split`으로 바꿔 `history.json`·`cards.json`을 따로 받는 길로 연다")
    args = parser.parse_args()
    names = [name for name in args.only.split(",") if name] or list(SCREENS)
    unknown = [name for name in names if name not in SCREENS]
    if unknown:
        raise SystemExit(f"없는 화면: {', '.join(unknown)}")
    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    temps = []
    try:
        code = checkout(args.ref, temps)
        data = code if args.data == args.ref else checkout(args.data, temps)
        if not (code / "app.html").is_file() or not (data / "r" / "index.json").is_file():
            raise SystemExit("app.html이나 r/index.json이 없다")
        server = Server(code, data)
        failed = []
        with sync_playwright() as p:
            browser = launch(p)
            run = Run(browser, server, args.split)
            for name in names:
                try:
                    page = SCREENS[name](run)
                    (out / f"{name}.html").write_text(compare.normalize(dom(page)), encoding="utf-8")
                    page.screenshot(path=str(out / f"{name}.png"), animations="disabled", caret="hide")
                    print(f"{name}: 저장")
                except Exception as error:
                    failed.append(name)
                    print(f"{name}: 실패 {type(error).__name__}: {str(error).splitlines()[0][:200]}")
                finally:
                    run.close()
            browser.close()
    finally:
        for temp in temps:
            shutil.rmtree(temp, ignore_errors=True)
    if server.unpatched:
        print("ASSET_OWNER 상수를 바꾸지 못함")
        failed.append("owner")
    if server.escaped:
        print(f"막은 외부 요청: {', '.join(sorted(set(server.escaped)))}")
    if server.errors:
        print(f"화면 오류 {len(server.errors)}건")
        for error in dict.fromkeys(server.errors):
            print(f"  {error}")
    return 1 if failed or server.escaped else 0


if __name__ == "__main__":
    sys.exit(main())
