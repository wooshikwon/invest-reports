// @ts-nocheck
import { feelPress, feelSlide } from "./telegram";
// 미국 거시 지표 카드의 그림. `build.py`가 소제목에 단 `data-card`의 `figure`를 받아 폭 320, 높이 `FIGURE` 단위의 SVG를 그린다.
// 그림마다 필요한 높이로 그리고, 보이는 칸은 높이 `FIGURE`로 같게 잡아 그림을 가운데에 둔다.
// 반원 속도계의 흰 바늘은 오늘 값이다. `zones`는 [끝값, 색, 이름]이고, 오늘 값이 든 구간만 진하게 칠하고 나머지 구간은 `DIM` 불투명도로 흐리게 칠한다.
// 반원 속도계는 작은 값을 왼쪽에, 큰 값을 오른쪽에 그린다.
// 세로 막대는 가로축이 시간이므로 앞선 값을 왼쪽에 그린다. 주별 세로 막대, 주별 선, 일별 선은 앞 날짜를 왼쪽에, 오늘을 오른쪽에 그리고, 0 기준 위아래 막대는 가까운 회의를 왼쪽에 그린다.
export const SVG = "http://www.w3.org/2000/svg", FIGURE = 178;
export const shape = (tag, attrs = {}, text) => {
  const node = document.createElementNS(SVG, tag);
  Object.entries(attrs).forEach(([name, value]) => node.setAttribute(name, value));
  if (text != null) node.textContent = text;
  return node;
};
export const canvas = (height) => shape("svg", { viewBox: `0 ${(height - FIGURE) / 2} 320 ${FIGURE}` });
export const zoneOf = (zones, value) => zones.find(([to]) => value <= to) || zones[zones.length - 1];
export const KNOB = { fill: "#EAEAEA", stroke: "#1d1e21", "stroke-width": 3 }, DIM = 0.35;
// 글씨·축 색과 종가 선 색. 주가와 예측 카드와 일별 선 그림이 같이 쓴다.
export const DIMS = "#7A828C", PRICE = "#C9CDD3";
// 글자 폭의 어림값. 그림을 화면에 붙이기 전에 그리므로 글자를 재지 않고, 영숫자는 글자 크기의 0.6배, 한글은 1배로 센다.
export const textWidth = (text, size) => [...text].reduce((sum, c) => sum + (/[\x00-\x7f]/.test(c) ? 0.6 : 1) * size, 0);
// 주가와 예측 카드, 종목 주가 카드와 유가 카드의 그림 종류. 봉 그림이면 참이고, 처음에는 봉 그림이다. 고른 종류는 기기에 남겨 다른 리포트와 종목에도 쓴다.
export const CANDLE_KEY = "chart-kind", kindCards = new Set();
export let candleOn = (() => { try { return localStorage.getItem(CANDLE_KEY) !== "line"; } catch { return true; } })();
export const CANDLE_ICON = '<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true"><path d="M6.5 2.5V17" stroke="#ff5c5c" stroke-width="1.4"/><rect x="4" y="5.5" width="5" height="8.5" rx=".8" fill="#ff5c5c"/>'
  + '<path d="M13.5 4.5V16" stroke="#5b9bff" stroke-width="1.4"/><rect x="11" y="7.5" width="5" height="5.5" rx=".8" fill="#5b9bff"/></svg>';
export const LINE_ICON = '<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true"><path d="M2.5 14.5L7 8.5l3.8 3.8L17.5 5" fill="none" stroke="#ff5c5c" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
// 그림 아래 단추 줄 오른쪽 끝의 선·봉 단추. 선 그림이면 봉 아이콘을, 봉 그림이면 선 아이콘을 그리고, 누르면 그림 종류를 바꿔 단추를 단 카드마다 `redraw`를 부른다.
export const kindButton = (redraw) => {
  const button = Object.assign(document.createElement("button"), { type: "button", className: "chart-kind" });
  const paint = () => {
    button.innerHTML = candleOn ? LINE_ICON : CANDLE_ICON;
    button.setAttribute("aria-label", candleOn ? "선 그래프로 보기" : "봉 그래프로 보기");
  };
  paint();
  kindCards.add({ button, paint, redraw });
  button.addEventListener("click", () => {
    feelPress();
    candleOn = !candleOn;
    try { localStorage.setItem(CANDLE_KEY, candleOn ? "candle" : "line"); } catch {}
    kindCards.forEach((card) => {
      if (!card.button.isConnected) return kindCards.delete(card);
      card.paint();
      card.redraw();
    });
  });
  return button;
};
// 기간을 옮기는 그림이 처음과 끝에서 천천히 움직이게 하는 곡선. `t`(0~1)를 받아 0~1을 돌려준다.
export const ease = (t) => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
// 일별 선(`GAUGES.daily`)의 세로 범위 [아래, 위]. `start`번 점부터 보이는 값(봉 그림이면 보이는 봉의 고가와 저가)과 정규장 다음 세션 값(`extra`)을 담고,
// 최저 글자가 들어가게 최저 값 아래에 20px을 비운다.
export const dailyBounds = ({ points, extra = null, candle = null, height = FIGURE, start = 0 }) => {
  const T = 22, B = height - 24, i0 = Math.max(0, Math.floor(start)), values = points.map(([, v]) => v);
  const shown = candle ? candleGroups(points.map(([day]) => day), values, candle.ratios, candle.unit, values.length - 1)
    .filter((group) => group[1] >= i0).flatMap((group) => [group[3], group[4]]) : values.slice(i0);
  const ends = extra == null ? shown : [...shown, extra], top = Math.max(...ends), bottom = Math.min(...ends);
  return [bottom - (top - bottom) * 20 / (B - T - 20), top];
};
export let clips = 0;
export const nextClip = () => ++clips;
// 봉 하나가 묶는 기간. 그림에 담는 거래일이 1년보다 길면 월봉, 6개월보다 길면 주봉, 그 밖에는 일봉이다.
export const candleUnit = (days) => (days > 252 ? "month" : days > 126 ? "week" : "day");
// 날짜(`YYYY-MM-DD`)가 든 봉 기간의 이름. 월봉은 달, 주봉은 월요일에 시작하는 주, 일봉은 날짜다.
export const candleKey = (unit) => (unit === "month" ? (day) => day.slice(0, 7) : unit === "week" ? (day) => Math.floor((Date.parse(day) / 864e5 + 3) / 7) : (day) => day);
// 거래일 번호 0부터 `to`까지를 `unit`마다 묶은 봉 [첫 번호, 끝 번호, 시가, 고가, 저가, 종가] 목록. 묶음은 맨 앞 거래일부터 나누므로 그림 왼쪽 끝이 옮겨 가도 봉이 바뀌지 않는다.
// 시가·고가·저가는 그날 종가(`closes`)에 봉 비율(`ratios`, [시가, 고가, 저가] ÷ 종가)을 곱한 값이고, 비율이 없는 날은 종가로 둔다.
export const candleGroups = (days, closes, ratios, unit, to) => {
  const key = candleKey(unit);
  const groups = [];
  for (let i = 0; i <= to; i++) {
    const [o, h, l] = ratios[i] || [1, 1, 1], c = closes[i], group = groups[groups.length - 1];
    if (group && key(days[group[0]]) === key(days[i])) {
      group[1] = i;
      group[3] = Math.max(group[3], c * h);
      group[4] = Math.min(group[4], c * l);
      group[5] = c;
    } else groups.push([i, i, c * o, c * h, c * l, c]);
  }
  return groups;
};
// −·+ 줄의 점 묶음(`steps`)을 누르면 누른 자리의 점으로 기간을 옮기고, 누른 채 끌면 손가락 아래 점으로 이어서 옮긴다. 점 묶음 폭을 점 수로 나눈 칸으로 자리를 찾아,
// 돋보기 크기가 바뀌어도 칸이 움직이지 않는다. 누를 때 글자 선택과 끌어 옮기기를 막는다. `now()`는 고른 점 번호이고, 점이 바뀔 때마다 진동을 내고 `pick(i)`를 부른다.
export const zoomDrag = (steps, now, pick) => {
  const go = (event) => {
    const box = steps.getBoundingClientRect(), n = steps.children.length;
    const i = Math.max(0, Math.min(n - 1, Math.floor((event.clientX - box.left) / box.width * n)));
    if (i === now()) return;
    feelSlide();
    pick(i);
  };
  steps.addEventListener("pointerdown", (event) => { event.preventDefault(); steps.setPointerCapture(event.pointerId); steps.classList.add("held"); go(event); });
  steps.addEventListener("pointermove", (event) => { if (steps.hasPointerCapture(event.pointerId)) go(event); });
  ["pointerup", "pointercancel"].forEach((type) => steps.addEventListener(type, () => steps.classList.remove("held")));
};
// 봉 하나(`[a, b]`는 첫·마지막 거래일 번호)의 몸통 폭이다.
export const candleWidth = ([a, b], step) => Math.max(1, step * (b - a + 1) * .62);
// 봉 목록 끝에 날짜 지점 `point`(`YYYY-MM-DD`)의 잠정 봉을 더한 봉 목록. `live`는 `{ close, open?, high?, low?, gray }`이고, `close`가 그 지점의 마지막 체결가다.
// 애프터장(선물 포함)·프리장 값은 시가·고가·저가가 없어 마지막 종가를 시가로 삼고 `gray`를 참으로 두어 회색 봉으로 그리며, 정규장 값은 시가·고가·저가를 받아 등락 색으로 그린다.
// 잠정 봉의 자리는 날짜 지점 순서가 정한다. 날짜 지점은 마지막 거래일(`b`) 바로 다음 번호(`b + 1`)이고 날짜를 세지 않는다. `point`가 마지막 봉의 기간 안이면
// 마지막 봉이 그 지점까지 늘어나고, 기간 밖이면 새 봉을 기간 하나의 폭으로 덧붙인다. `point`는 호출하는 카드가 실시간 값의 날짜 지점으로 넘긴다.
// 바꾸거나 덧붙인 봉은 아직 정해지지 않은 잠정 봉이어서 일곱째 값을 참으로 두고, 여덟째 값이 회색 여부다.
export const candleLate = (groups, days, unit, live, point) => {
  const { close: v, gray = true } = typeof live === "number" ? { close: live } : live;
  const [a, b, o, h, l, c] = groups[groups.length - 1], key = candleKey(unit), day = point;
  const open = live.open ?? null, high = Math.max(live.high ?? v, v), low = Math.min(live.low ?? v, v);
  if (key(day) === key(days[b])) return [...groups.slice(0, -1), [a, b + 1, o, Math.max(h, high), Math.min(l, low), v, true, gray]];
  return [...groups, [b + 1, b + { day: 1, week: 5, month: 21 }[unit], open ?? c, Math.max(c, high), Math.min(c, low), v, true, gray]];
};
// 봉을 `parent`에 그린다. `X`는 거래일 번호의 가로 자리, `Y`는 값의 세로 자리, `step`은 거래일 하나의 폭이다. 종가가 시가 이상인 봉은 오름 색, 아래인 봉은 내림 색이다.
// 회색 봉(여덟째 값이 참)은 등락 색에 회색(#A7ABB0)을 9할 섞은 흐린 색으로 그린다. 잠정 봉(일곱째 값이 참)은 앞 봉 뒤에 덧붙이면 앞 봉과 1px 띄우고, 오른쪽 끝(`right`)을 넘지 않게 자리를 당기고 폭을 줄인다.
export const drawCandles = (parent, groups, X, Y, step, right = Infinity) => groups.map(([a, b, o, h, l, c, late, gray], i) => {
  let x = X((a + b) / 2), w = candleWidth([a, b], step);
  if (late && i && a > groups[i - 1][1]) {
    const [pa, pb] = groups[i - 1], edge = X((pa + pb) / 2) + candleWidth([pa, pb], step) / 2 + 1;
    w = Math.max(1, Math.min(w, right - edge));
    x = Math.max(edge + w / 2, Math.min(x, right - w / 2));
  }
  const color = c >= o ? (gray ? "#B0A3A8" : "#ff5c5c") : (gray ? "#9FA9B8" : "#5b9bff"), top = Y(Math.max(o, c)), bottom = Y(Math.min(o, c));
  parent.append(shape("path", { d: `M${x} ${Y(h)}V${Y(l)}`, stroke: color, "stroke-width": Math.min(1, w) }));
  const body = shape("rect", { x: x - w / 2, y: top, width: w, height: Math.max(.8, bottom - top), fill: color });
  if (late) body.dataset.live = gray ? "gray" : "color";
  parent.append(body);
  return x;
});
// 시간 축 그림을 누르면 누른 자리의 가로 좌표를 그림 좌표(`viewBox`)로 바꿔 `handle(x)`를 부른다. 그림을 다시 그려도 손길이 쌓이지 않게 `onclick` 하나만 둔다.
// 카드를 밀어 넘긴 손길에는 click이 오지 않으므로, 넘기기와 누르기가 섞이지 않는다.
export const onTap = (svg, handle) => {
  svg.style.cursor = "pointer";
  svg.onclick = (event) => {
    const box = svg.getBoundingClientRect(), view = svg.viewBox.baseVal;
    if (box.width) handle(view.x + (event.clientX - box.left) / box.width * view.width);
  };
};
// 가로 자리 목록 `xs`에서 `x`에 가장 가까운 번호다.
export const nearest = (xs, x) => xs.reduce((best, v, i) => (Math.abs(v - x) < Math.abs(xs[best] - x) ? i : best), 0);
// '현재' 표시. 값의 세션(`kind`: `regular`, `after`, `pre`) 색 점이고, 색은 위 줄 기준 시각 글씨와 같은 세션 색(`--kind`)이다.
export const nowMark = (parent, x, y, kind) => {
  parent.append(shape("circle", { cx: x, cy: y, r: 2.5, "data-kind": kind, style: "fill: var(--kind)", stroke: "#171719", "stroke-width": 1 }));
};
// 지도 카드의 경계 파일(`maps/{view}.json`)은 지도 카드가 처음 그려질 때 한 번 받는다.
export const MAPS = {};
export const mapOf = (view) => (MAPS[view] ||= fetch(`maps/${view}.json`).then((r) => r.json()));
// 그림 높이가 `FIGURE`보다 낮으면 같은 높이의 칸 가운데에 그리고, 높으면 그림 높이대로 칸을 늘린다.
export const frame = (height) => (height <= FIGURE ? canvas(height) : shape("svg", { viewBox: `0 0 320 ${height}` }));
// 범례: [이름, 색, 모양, 불투명도]를 그림 위 `right`에서 왼쪽으로 적는다. 모양은 네모(`box`)와 점(`dot`)이다.
export const legend = (s, items, right = 320) => {
  let x = right;
  [...items].reverse().forEach(([name, color, mark, opacity = 1]) => {
    s.append(shape("text", { x, y: 14, "text-anchor": "end", "font-size": 11.5, fill: "#A7ABB0" }, name));
    x -= textWidth(name, 11.5);
    s.append(mark === "dot" ? shape("circle", { cx: x - 9, cy: 10, r: 4.5, fill: color, opacity })
      : shape("rect", { x: x - 14, y: 5, width: 9, height: 9, rx: 2, fill: color, opacity }));
    x -= 26;
  });
};
// 지도 카드의 본문. 미국 주 지도는 미국 전체를, 중동 지도는 지점과 칠한 지역을 모두 담는 가장 좁은 범위를 폭 320, 높이 `tall`에 그린다.
// 칠한 지역은 분류 색으로 칠하고 이름이 지역 안에 들어가면 이름을 적는다. 지점은 분류 색 점을 찍고, 오른쪽·왼쪽·위·아래 가운데
// 다른 글자와 점에 겹치지 않는 첫 자리에 이름을 적는다. 중동 지도는 칠하지 않은 나라와 바다의 이름을 들어가고 겹치지 않을 때만 흐리게 적는다.
export const drawMap = (s, { view, categories, regions, points = [] }, data, top, tall) => {
  const P = data.projection, at = (lon, lat) => [(lon - P.west) * P.kx, (P.north - lat) * P.ky], fill = Object.fromEntries(regions);
  let box = [0, 0, data.width, data.height];
  if (P) {
    const xs = [], ys = [];
    points.forEach(([, lon, lat]) => { const [x, y] = at(lon, lat); xs.push(x); ys.push(y); });
    regions.forEach(([code]) => { const b = data.shapes[code].box; xs.push(b[0], b[2]); ys.push(b[1], b[3]); });
    const pad = 25, left = Math.min(...xs), right = Math.max(...xs), up = Math.min(...ys), down = Math.max(...ys);
    const w = Math.min(data.width, data.height * 320 / tall, Math.max(100, right - left + pad * 2, (down - up + pad * 2) * 320 / tall)), h = w * tall / 320;
    box = [Math.min(data.width - w, Math.max(0, (left + right - w) / 2)), Math.min(data.height - h, Math.max(0, (up + down - h) / 2)), w, h];
  }
  const k = Math.min(320 / box[2], tall / box[3]), ox = (320 - box[2] * k) / 2, oy = top + (tall - box[3] * k) / 2;
  const X = (x) => ox + (x - box[0]) * k, Y = (y) => oy + (y - box[1]) * k;
  const inner = s.appendChild(shape("svg", { x: 0, y: top, width: 320, height: tall, viewBox: `${box[0] - ox / k} ${box[1] - (oy - top) / k} ${320 / k} ${tall / k}` }));
  const codes = Object.keys(data.shapes).sort((a, b) => (a in fill) - (b in fill));
  codes.forEach((code) => {
    const on = code in fill, path = shape("path", { d: data.shapes[code].d, fill: on ? categories[fill[code]][1] : "#2a2c30", "fill-opacity": on ? 0.78 : 1,
      stroke: P && !on ? "#45484e" : "#171719", "stroke-width": 0.8, "vector-effect": "non-scaling-stroke" });
    path.append(shape("title", {}, on ? `${data.shapes[code].name} · ${categories[fill[code]][0]}` : data.shapes[code].name));
    inner.append(path);
  });
  // 글자와 점이 차지한 상자 [왼쪽, 위, 오른쪽, 아래]. 새 글자는 이 상자들과 지도 밖에 겹치지 않을 때만 적는다.
  const taken = [], free = (b) => b[0] >= 2 && b[2] <= 318 && b[1] >= top && b[3] <= top + tall
    && !taken.some((o) => b[0] < o[2] && o[0] < b[2] && b[1] < o[3] && o[1] < b[3]);
  const label = (x, y, anchor, size, text) => {
    const w = textWidth(text, size), x0 = anchor === "start" ? x : anchor === "end" ? x - w : x - w / 2;
    return [x0 - 1, y - size * 0.82, x0 + w + 1, y + size * 0.22];
  };
  const spots = points.map(([name, lon, lat, c]) => {
    const [x, y] = at(lon, lat), cx = X(x), cy = Y(y);
    taken.push([cx - 6, cy - 6, cx + 6, cy + 6]);
    return [name, cx, cy, c];
  });
  spots.forEach(([name, cx, cy]) => {
    const tries = [[cx + 9, cy + 4, "start"], [cx - 9, cy + 4, "end"], [cx, cy - 10, "middle"], [cx, cy + 19, "middle"]];
    const [x, y, anchor] = tries.find(([x, y, anchor]) => free(label(x, y, anchor, 12, name))) || tries[0];
    taken.push(label(x, y, anchor, 12, name));
    s.append(shape("text", { x, y, "text-anchor": anchor, "font-size": 12, "font-weight": 700, fill: "#EAEAEA",
                             stroke: "#171719", "stroke-width": 3, "stroke-linejoin": "round", "paint-order": "stroke" }, name));
  });
  spots.forEach(([name, cx, cy, c]) => {
    const dot = shape("circle", { cx, cy, r: 4.5, fill: categories[c][1], stroke: "#171719", "stroke-width": 2 });
    dot.append(shape("title", {}, `${name} · ${categories[c][0]}`));
    s.append(dot);
  });
  const names = [...codes.filter((code) => code in fill).map((code) => [code, 11, "#171719", 700]),
                 ...(P ? codes.filter((code) => !(code in fill)).map((code) => [code, 10.5, DIMS, 400]) : [])];
  names.forEach(([code, size, ink, weight]) => {
    const { name, box: b, center } = data.shapes[code], cx = X(center[0]), cy = Y(center[1]) + size * 0.35, w = textWidth(name, size);
    const area = label(cx, cy, "middle", size, name);
    if ((b[2] - b[0]) * k < w * 1.25 + 4 || (b[3] - b[1]) * k < size + 3 || !free(area)) return;
    taken.push(area);
    s.append(shape("text", { x: cx, y: cy, "text-anchor": "middle", "font-size": size, "font-weight": weight, fill: ink }, name));
  });
  (data.seas || []).forEach(([name, x, y]) => {
    const cx = X(x), cy = Y(y) + 4, area = label(cx, cy, "middle", 10.5, name);
    if (!free(area)) return;
    taken.push(area);
    s.append(shape("text", { x: cx, y: cy, "text-anchor": "middle", "font-size": 10.5, fill: "#56657a" }, name));
  });
};
