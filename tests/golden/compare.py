"""두 골든 캡처 폴더를 화면마다 견줘 DOM 차이 줄 수와 픽셀 차이 비율을 낸다.

    python3 tests/golden/compare.py ~/data/invest-reports/golden/v0.8 ~/data/invest-reports/golden/new

DOM은 `normalize`로 정규화한 뒤 줄 단위로 견준다. 정규화 규칙은 이 파일에만 둔다. `capture.py`도 이 함수로 정규화한 HTML을 저장한다.
`ALLOW`는 화면마다 차이를 받아들이는 요소의 CSS 선택자이고, 두 쪽에서 그 요소를 지운 뒤 견준다.
출력에는 화면 이름과 차이 줄 수, 픽셀 비율만 쓴다. 차이 줄 자체는 `--show`로 화면을 지정할 때만 찍는다.
모든 화면이 `--max-dom`, `--max-pixel` 안이면 종료 코드 0, 아니면 1이다.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# 화면 이름 → 차이를 받아들이는 요소의 CSS 선택자 목록.
ALLOW: dict[str, list[str]] = {}

# 시각 문자열. ISO 시각을 먼저 바꾸고, 남은 "HH:MM"과 뒤따르는 시간대 이름을 바꾼다.
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?")
_CLOCK = re.compile(r"(?<![\d.])\d{1,2}:\d{2}(?::\d{2})?(?:\s?(?:KST|ET|EST|EDT))?(?![\d])")


def normalize(html: str) -> str:
    """태그마다 한 줄로 나누고 시각 문자열을 `<시각>`으로 바꾼다. 같은 입력을 두 번 넣어도 결과가 같다."""
    html = _ISO.sub("<시각>", html)
    html = _CLOCK.sub("<시각>", html)
    lines = re.sub(r"\s*(<(?!시각>)[^>]*>)\s*", r"\n\1\n", html).split("\n")
    return "\n".join(line.strip() for line in lines if line.strip()) + "\n"


def allowed(html: str, selectors: list[str]) -> str:
    """`selectors`에 맞는 요소를 지운 HTML."""
    if not selectors:
        return html
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for selector in selectors:
        for node in soup.select(selector):
            node.decompose()
    return str(soup)


def dom_diff(a: Path, b: Path, name: str) -> list[str]:
    left, right = (normalize(allowed(path.read_text(encoding="utf-8"), ALLOW.get(name, []))).splitlines() for path in (a, b))
    return [line for line in difflib.unified_diff(left, right, lineterm="", n=0)
            if line[:1] in "+-" and not line.startswith(("+++", "---"))]


def pixel_ratio(a: Path, b: Path) -> float:
    """두 PNG에서 값이 다른 픽셀의 비율(%). 크기가 다르면 100이다."""
    left, right = (np.asarray(Image.open(path).convert("RGBA")) for path in (a, b))
    if left.shape != right.shape:
        return 100.0
    return float((left != right).any(axis=2).mean() * 100)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("--max-dom", type=int, default=0, help="화면마다 허용하는 DOM 차이 줄 수")
    parser.add_argument("--max-pixel", type=float, default=0.1, help="화면마다 허용하는 픽셀 차이 비율(%%)")
    parser.add_argument("--show", action="append", default=[], help="차이 줄을 찍을 화면 이름")
    args = parser.parse_args()
    names = sorted({path.stem for path in args.a.glob("*.html")} | {path.stem for path in args.b.glob("*.html")})
    failed = False
    print(f"{'화면':<12} {'DOM 차이 줄':>10} {'픽셀 차이 %':>11}")
    for name in names:
        files = [args.a / f"{name}.html", args.b / f"{name}.html", args.a / f"{name}.png", args.b / f"{name}.png"]
        if not all(path.is_file() for path in files):
            print(f"{name:<12} {'파일 없음':>10}")
            failed = True
            continue
        lines = dom_diff(files[0], files[1], name)
        ratio = pixel_ratio(files[2], files[3])
        bad = len(lines) > args.max_dom or ratio > args.max_pixel
        failed |= bad
        print(f"{name:<12} {len(lines):>10} {ratio:>11.4f}{'  초과' if bad else ''}")
        if name in args.show:
            print("\n".join(lines))
    print("통과" if not failed else "실패")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
