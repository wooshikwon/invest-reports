#!/usr/bin/env python3
"""make — 이슈 그래프의 지도 카드가 쓰는 경계 파일 `maps/{view}.json`을 만든다.

    python3 maps/make.py {원본 폴더}

원본 폴더에는 jsDelivr에서 받은 TopoJSON 두 개를 둔다.

- `states-albers-10m.json` (`us-atlas@3`): 미국 주 경계. 알래스카와 하와이를 왼쪽 아래에 옮겨 그린 Albers 투영 좌표(975×610)다.
- `countries-50m.json` (`world-atlas@2`): 나라 경계(경도·위도). `BOUNDS` 안으로 잘라 정거원통 투영 좌표로 바꾼다.

경계 파일은 `width`·`height`(투영 좌표의 크기)와 `shapes`(코드마다 한국어 이름 `name`, SVG 경로 `d`, 가장 큰 조각의 상자 `box`와
무게중심 `center`)를 담는다. 미국 주의 코드는 우편 약어(`TX`), 나라의 코드는 ISO 3166-1 alpha-3(`IRN`)이다. 나라 지도는 투영 식
(`projection`), 투영할 수 있는 경도·위도 범위(`bounds`), 바다 이름의 자리(`seas`)도 담는다. 미니 앱은 투영 좌표를 그대로 그리고,
지점은 경도·위도를 `projection`으로 바꿔 찍는다.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

STATES = {
    "01": ("AL", "앨라배마"), "02": ("AK", "알래스카"), "04": ("AZ", "애리조나"), "05": ("AR", "아칸소"), "06": ("CA", "캘리포니아"),
    "08": ("CO", "콜로라도"), "09": ("CT", "코네티컷"), "10": ("DE", "델라웨어"), "11": ("DC", "워싱턴DC"), "12": ("FL", "플로리다"),
    "13": ("GA", "조지아"), "15": ("HI", "하와이"), "16": ("ID", "아이다호"), "17": ("IL", "일리노이"), "18": ("IN", "인디애나"),
    "19": ("IA", "아이오와"), "20": ("KS", "캔자스"), "21": ("KY", "켄터키"), "22": ("LA", "루이지애나"), "23": ("ME", "메인"),
    "24": ("MD", "메릴랜드"), "25": ("MA", "매사추세츠"), "26": ("MI", "미시간"), "27": ("MN", "미네소타"), "28": ("MS", "미시시피"),
    "29": ("MO", "미주리"), "30": ("MT", "몬태나"), "31": ("NE", "네브래스카"), "32": ("NV", "네바다"), "33": ("NH", "뉴햄프셔"),
    "34": ("NJ", "뉴저지"), "35": ("NM", "뉴멕시코"), "36": ("NY", "뉴욕"), "37": ("NC", "노스캐롤라이나"), "38": ("ND", "노스다코타"),
    "39": ("OH", "오하이오"), "40": ("OK", "오클라호마"), "41": ("OR", "오리건"), "42": ("PA", "펜실베이니아"), "44": ("RI", "로드아일랜드"),
    "45": ("SC", "사우스캐롤라이나"), "46": ("SD", "사우스다코타"), "47": ("TN", "테네시"), "48": ("TX", "텍사스"), "49": ("UT", "유타"),
    "50": ("VT", "버몬트"), "51": ("VA", "버지니아"), "53": ("WA", "워싱턴"), "54": ("WV", "웨스트버지니아"), "55": ("WI", "위스콘신"),
    "56": ("WY", "와이오밍"),
}
COUNTRIES = {
    "792": ("TUR", "튀르키예"), "760": ("SYR", "시리아"), "422": ("LBN", "레바논"), "376": ("ISR", "이스라엘"), "275": ("PSE", "팔레스타인"),
    "400": ("JOR", "요르단"), "368": ("IRQ", "이라크"), "364": ("IRN", "이란"), "682": ("SAU", "사우디"), "414": ("KWT", "쿠웨이트"),
    "048": ("BHR", "바레인"), "634": ("QAT", "카타르"), "784": ("ARE", "UAE"), "512": ("OMN", "오만"), "887": ("YEM", "예멘"),
    "818": ("EGY", "이집트"), "729": ("SDN", "수단"), "232": ("ERI", "에리트레아"), "231": ("ETH", "에티오피아"), "262": ("DJI", "지부티"),
    "706": ("SOM", "소말리아"), "004": ("AFG", "아프가니스탄"), "586": ("PAK", "파키스탄"), "795": ("TKM", "투르크메니스탄"),
    "031": ("AZE", "아제르바이잔"), "051": ("ARM", "아르메니아"), "268": ("GEO", "조지아"), "196": ("CYP", "키프로스"), "434": ("LBY", "리비아"),
    "860": ("UZB", "우즈베키스탄"), "398": ("KAZ", "카자흐스탄"), "643": ("RUS", "러시아"), "300": ("GRC", "그리스"), "100": ("BGR", "불가리아"),
    "728": ("SSD", "남수단"), "148": ("TCD", "차드"), "N. Cyprus": ("CYN", "북키프로스"), "Somaliland": ("SOL", "소말릴란드"),
}
BOUNDS = (25.0, 8.0, 66.0, 43.0)  # 서·남·동·북 끝 경도·위도
PARALLEL = 27.0  # 정거원통 투영에서 경도 1도의 폭을 위도 1도의 cos(27°)배로 줄인다
SCALE = 8.0  # 위도 1도의 투영 좌표 길이
SEAS = [("지중해", 29.5, 33.4), ("홍해", 38.6, 20.6), ("페르시아만", 51.0, 27.6), ("아라비아해", 62.0, 17.0), ("오만만", 59.2, 24.4),
        ("아덴만", 48.0, 12.4), ("카스피해", 50.8, 41.2)]


def decode(topology: dict) -> list[list[list[float]]]:
    """TopoJSON의 양자화한 호를 변환 식으로 풀어 호마다 [[x, y], ...]로 낸다."""
    (sx, sy), (tx, ty) = topology["transform"]["scale"], topology["transform"]["translate"]
    arcs = []
    for arc in topology["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            points.append([x * sx + tx, y * sy + ty])
        arcs.append(points)
    return arcs


def rings(geometry: dict, arcs: list) -> list[list[list[list[float]]]]:
    """도형의 다각형마다 고리 목록. 음수 호 번호 `~i`는 i번 호를 거꾸로 잇는다."""
    def ring(indexes):
        points = []
        for i in indexes:
            arc = arcs[i] if i >= 0 else arcs[~i][::-1]
            points += arc[1:] if points else arc
        return points
    polygons = geometry["arcs"] if geometry["type"] == "MultiPolygon" else [geometry["arcs"]] if geometry["type"] == "Polygon" else []
    return [[ring(r) for r in polygon] for polygon in polygons]


def clip(points: list, west: float, south: float, east: float, north: float) -> list:
    """고리를 경도·위도 상자 안으로 자른다(Sutherland–Hodgman)."""
    edges = [(lambda p: p[0] >= west, lambda a, b: (west - a[0]) / (b[0] - a[0]), 0),
             (lambda p: p[0] <= east, lambda a, b: (east - a[0]) / (b[0] - a[0]), 0),
             (lambda p: p[1] >= south, lambda a, b: (south - a[1]) / (b[1] - a[1]), 1),
             (lambda p: p[1] <= north, lambda a, b: (north - a[1]) / (b[1] - a[1]), 1)]
    for inside, cut, _ in edges:
        if not points:
            break
        result = []
        for k, current in enumerate(points):
            previous = points[k - 1]
            if inside(current):
                if not inside(previous):
                    t = cut(previous, current)
                    result.append([previous[0] + t * (current[0] - previous[0]), previous[1] + t * (current[1] - previous[1])])
                result.append(current)
            elif inside(previous):
                t = cut(previous, current)
                result.append([previous[0] + t * (current[0] - previous[0]), previous[1] + t * (current[1] - previous[1])])
        points = result
    return points


def project(lon: float, lat: float) -> list[float]:
    west, _, _, north = BOUNDS
    return [(lon - west) * math.cos(math.radians(PARALLEL)) * SCALE, (north - lat) * SCALE]


def shape(polygons: list, name: str, near: float) -> dict:
    """투영한 다각형 목록의 SVG 경로와 가장 큰 조각의 상자·무게중심. `near`보다 가까운 이웃 점은 지운다."""
    path, largest = [], (0.0, None)
    for polygon in polygons:
        for k, points in enumerate(polygon):
            kept: list[list[float]] = []
            for x, y in points:
                if not kept or math.hypot(x - kept[-1][0], y - kept[-1][1]) >= near:
                    kept.append([round(x, 1), round(y, 1)])
            if len(kept) < 3:
                continue
            path.append("M" + "L".join(f"{x:g} {y:g}" for x, y in kept) + "Z")
            if k == 0:
                area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(kept, kept[1:] + kept[:1])) / 2
                if abs(area) > largest[0]:
                    cx = sum((a[0] + b[0]) * (a[0] * b[1] - b[0] * a[1]) for a, b in zip(kept, kept[1:] + kept[:1])) / (6 * area)
                    cy = sum((a[1] + b[1]) * (a[0] * b[1] - b[0] * a[1]) for a, b in zip(kept, kept[1:] + kept[:1])) / (6 * area)
                    xs, ys = [x for x, _ in kept], [y for _, y in kept]
                    largest = (abs(area), {"box": [min(xs), min(ys), max(xs), max(ys)], "center": [round(cx, 1), round(cy, 1)]})
    return {"name": name, "d": "".join(path), **(largest[1] or {"box": [0, 0, 0, 0], "center": [0, 0]})}


def main() -> int:
    source, out = Path(sys.argv[1]), Path(__file__).resolve().parent
    us = json.loads((source / "states-albers-10m.json").read_text())
    arcs = decode(us)
    shapes = {}
    for geometry in us["objects"]["states"]["geometries"]:
        code, name = STATES[geometry["id"]]
        shapes[code] = shape(rings(geometry, arcs), name, 1.0)
    (out / "us-states.json").write_text(json.dumps({"width": 975, "height": 610, "shapes": shapes}, ensure_ascii=False, separators=(",", ":")))

    world = json.loads((source / "countries-50m.json").read_text())
    arcs = decode(world)
    shapes = {}
    for geometry in world["objects"]["countries"]["geometries"]:
        polygons = [[clip(r, *BOUNDS) for r in polygon] for polygon in rings(geometry, arcs)]
        polygons = [[[project(lon, lat) for lon, lat in r] for r in polygon if len(r) >= 3] for polygon in polygons]
        polygons = [polygon for polygon in polygons if polygon]
        if not polygons:
            continue
        code, name = COUNTRIES.get(geometry.get("id") or geometry["properties"]["name"], (geometry.get("id"), geometry["properties"]["name"]))
        shapes[code] = shape(polygons, name, 0.15)
    width, height = project(BOUNDS[2], BOUNDS[1])
    (out / "middle-east.json").write_text(json.dumps({
        "width": round(width, 1), "height": round(height, 1), "bounds": list(BOUNDS),
        "projection": {"west": BOUNDS[0], "north": BOUNDS[3], "kx": round(math.cos(math.radians(PARALLEL)) * SCALE, 6), "ky": SCALE},
        "shapes": shapes, "seas": [[name, *project(lon, lat)] for name, lon, lat in SEAS]}, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
