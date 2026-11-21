// @ts-nocheck
import { DIM, DIMS, FIGURE, KNOB, PRICE, candleGroups, candleLate, canvas, nextClip, dailyBounds, drawCandles, drawMap, frame, legend, mapOf, nowMark, shape, textWidth, zoneOf } from "./svg";
// 시간 축 그림을 누를 수 있는 자리. 점이나 막대마다 그림 좌표의 가로 자리와, 그 자리가 가리키는 점 번호를 돌려준다.
// 가로 자리는 `columns`와 `daily`가 점을 그리는 식과 같다.
export const columnTaps = ({ bars }) => {
  const w = (256 - 2 * (bars.length - 1)) / bars.length;
  return [bars.map((_, i) => 6 + i * (w + 2) + w / 2), bars.map((_, i) => i)];
};
// 일별 선은 그림 왼쪽 끝(`start`) 뒤의 점만 담고, 다음 세션 값 자리(`reach`)는 마지막 점 번호를 가리킨다.
export const dailyTaps = ({ points, start = 0, reach = 0 }) => {
  const last = points.length - 1, span = Math.max(1, last + reach - start), X = (i) => 4 + 308 * (i - start) / span;
  const idx = [];
  for (let i = Math.max(0, Math.ceil(start)); i <= last; i++) idx.push(i);
  return [[...idx.map(X), ...(reach ? [X(last + reach)] : [])], [...idx, ...(reach ? [last] : [])]];
};
export const GAUGES = {
  // 반원 속도계: 구간 경계값을 바깥에 적는다.
  semi({ min, max, zones, value, ends }) {
    const cx = 160, cy = 150, r = 118, sw = 18, s = canvas(178), now = zoneOf(zones, value);
    // `min`에서 `max` 사이 값이 축 왼쪽 끝에서 얼마나 떨어졌는지를 0에서 1로 돌려준다.
    const P = (v) => (Math.min(max, Math.max(min, v)) - min) / (max - min);
    const angle = (v) => Math.PI * (1 - P(v));
    const at = (a, rr) => [cx + rr * Math.cos(a), cy - rr * Math.sin(a)];
    let from = min;
    zones.forEach((zone) => {
      const [left, right] = [P(from), P(zone[0])].sort((a, b) => a - b);
      const a0 = Math.PI * (1 - left) - (left > 0 ? 0.012 : 0), a1 = Math.PI * (1 - right) + (right < 1 ? 0.012 : 0);
      const [x0, y0] = at(a0, r), [x1, y1] = at(a1, r);
      s.append(shape("path", { d: `M${x0} ${y0} A${r} ${r} 0 0 1 ${x1} ${y1}`, fill: "none", stroke: zone[1], "stroke-width": sw,
                               opacity: zone === now ? 1 : DIM }));
      from = zone[0];
    });
    zones.slice(0, -1).forEach(([to]) => {
      const [x, y] = at(angle(to), r + sw / 2 + 11);
      s.append(shape("text", { x, y: y + 4, "text-anchor": "middle", "font-size": 11, fill: "#7A828C" }, String(to)));
    });
    const [nx, ny] = at(angle(value), r - sw / 2 - 6);
    s.append(shape("line", { x1: cx, y1: cy, x2: nx, y2: ny, stroke: "#EAEAEA", "stroke-width": 3.5, "stroke-linecap": "round" }));
    s.append(shape("circle", { cx, cy, r: 7, ...KNOB }));
    ends.forEach((end, i) => s.append(shape("text", { x: cx + (i ? r : -r), y: cy + 24, "text-anchor": "middle", "font-size": 12,
                                                       "font-weight": 600, fill: "#A7ABB0" }, end)));
    return s;
  },
  // 주별 세로 막대: 막대마다 [날짜, 값, 글자]이고 0에서 시작한다. 고른 막대(`stop`, 처음에는 마지막 막대)는 흰색, 나머지는 회색이며 고른 막대 위에만 값을 적는다.
  // `lines`는 [값, 이름]이고 점선을 긋고 오른쪽 여백에 이름을 적는다. 고른 값 글자와 높이가 겹치는 선은 긋지 않는다. 날짜는 처음과 마지막 막대 아래에만 적는다.
  columns({ bars, max, lines = [], stop = bars.length - 1 }) {
    const x0 = 6, x1 = 262, top = 26, base = 146, gap = 2, s = canvas(FIGURE);
    const w = (x1 - x0 - gap * (bars.length - 1)) / bars.length, Y = (v) => base - (base - top) * Math.min(1, Math.max(0, v / max));
    const mark = Y(bars[stop][1]) - 12;
    lines.filter(([v]) => Math.abs(Y(v) - mark) > 12).forEach(([v, name]) => {
      s.append(shape("line", { x1: x0, y1: Y(v), x2: x1, y2: Y(v), stroke: "#7A828C", "stroke-width": 1, "stroke-dasharray": "3 3", opacity: 0.7 }));
      s.append(shape("text", { x: x1 + 10, y: Y(v) + 4, "font-size": 11, fill: "#7A828C" }, name));
    });
    bars.forEach(([day, v, text], i) => {
      const x = x0 + i * (w + gap), y = Y(v), r = Math.min(4, (base - y) / 2, w / 2), last = i === stop;
      const bar = shape("path", { d: `M${x} ${base}V${y + r}Q${x} ${y} ${x + r} ${y}H${x + w - r}Q${x + w} ${y} ${x + w} ${y + r}V${base}Z`,
                                  fill: last ? "#EAEAEA" : "#7A828C", opacity: last ? 1 : 0.55 });
      bar.append(shape("title", {}, `${day} ${text}`));
      s.append(bar);
      if (last) s.append(shape("text", { x: x + w / 2, y: y - 8, "text-anchor": "middle", "font-size": 12.5, "font-weight": 700, fill: "#EAEAEA" }, text));
    });
    s.append(shape("line", { x1: x0, y1: base, x2: x1, y2: base, stroke: "#7A828C", "stroke-width": 1.2 }));
    [[x0, "start", bars[0][0]], [x1, "end", bars[bars.length - 1][0]]].forEach(([x, anchor, text]) => s.append(shape("text", {
      x, y: base + 20, "font-size": 12, fill: "#7A828C", "text-anchor": anchor }, text)));
    return s;
  },
  // 주별 선: 점마다 [날짜, 값, 글자]이고 세로축은 `min`에서 `max`까지다. 선은 회색이고 오늘 점만 흰 점으로 찍어 그 위에 값을 적는다.
  // `lines`는 [값, 이름]이고 세로 막대처럼 점선을 긋고 오른쪽 여백에 이름을 적는다. 오늘 값 글자와 높이가 겹치는 선은 긋지 않는다.
  // 날짜는 처음과 마지막 점 아래에만 적고, 점마다 선보다 넓은 투명 원을 두어 누르거나 올리면 그 주의 날짜와 값을 보여 준다.
  line({ points, min, max, lines = [] }) {
    const x0 = 10, x1 = 254, top = 30, base = 146, s = canvas(FIGURE);
    const X = (i) => x0 + (x1 - x0) * i / Math.max(1, points.length - 1);
    const Y = (v) => base - (base - top) * Math.min(1, Math.max(0, (v - min) / (max - min)));
    // 선이 위에서 내려와 마지막 점에 닿으면 값 글자를 점 아래에, 그 밖에는 점 위에 적는다.
    const [lx, ly] = [X(points.length - 1), Y(points[points.length - 1][1])];
    const below = points.length > 1 && Y(points[points.length - 2][1]) < ly && ly + 22 <= base + 4, mark = below ? ly + 22 : ly - 14;
    lines.filter(([v]) => Math.abs(Y(v) - mark) > 12).forEach(([v, name]) => {
      s.append(shape("line", { x1: 6, y1: Y(v), x2: 262, y2: Y(v), stroke: "#7A828C", "stroke-width": 1, "stroke-dasharray": "3 3", opacity: 0.7 }));
      s.append(shape("text", { x: 272, y: Y(v) + 4, "font-size": 11, fill: "#7A828C" }, name));
    });
    s.append(shape("polyline", { points: points.map(([, v], i) => `${X(i)},${Y(v)}`).join(" "), fill: "none", stroke: "#A7ABB0",
                                 "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    s.append(shape("circle", { cx: lx, cy: ly, r: 5, fill: "#EAEAEA", stroke: "#1d1e21", "stroke-width": 2 }));
    s.append(shape("text", { x: lx, y: mark, "text-anchor": "end", "font-size": 12.5, "font-weight": 700, fill: "#EAEAEA" }, points[points.length - 1][2]));
    points.forEach(([day, v, text], i) => {
      const hit = shape("circle", { cx: X(i), cy: Y(v), r: 11, fill: "transparent" });
      hit.append(shape("title", {}, `${day} ${text}`));
      s.append(hit);
    });
    [[x0, "start", points[0][0]], [x1, "end", points[points.length - 1][0]]].forEach(([x, anchor, text]) => s.append(shape("text", {
      x, y: base + 20, "font-size": 12, fill: "#7A828C", "text-anchor": anchor }, text)));
    return s;
  },
  // 일별 선: 점마다 [날짜, 값, 글자]이고, 주가와 예측 카드의 종가 선과 같은 모양으로 그린다. 가는 회색 선으로 점을 잇고, 가로축 아래에
  // 달이 바뀌는 점마다 달 이름을 적는다. 달 이름과 선 굵기는 주가와 예측 카드가 같은 기간을 그릴 때와 같게 정한다.
  // 기간 안 최고·최저 점에 점을 찍어 글자를 적고, 오늘 점에는 '현재' 표시(`nowMark`)를 찍는다. 세로축은 값의 최저에서 최고까지이고,
  // 최저 글자가 들어가게 최저 점 아래에 20px을 비운다. 그림 높이(`height`)를 받으면 가로축을 그 높이의 24px 위에 긋는다.
  // 가로축은 마지막 점 오른쪽 `reach` 거래일까지 담는다. 정규장 다음 세션의 값(`extra`)과 그 값의 날짜 지점(`point`)을 받으면 다음 거래일 자리에 값을 '현재' 표시로 찍고
  // 마지막 점에서 점선으로 잇는다. 세로축은 그 값까지 담는다. '현재' 표시의 색은 `extra`의 세션(`kind`)으로 고른다.
  // 봉 비율과 봉 하나가 묶는 기간과 값 글자(`candle`, `{ ratios, unit, label }`)를 받으면 선 대신 봉을 그리고, 세로축을 봉의 고가와 저가까지 담는다.
  // 최고·최저 글자는 가장 높은 고가와 가장 낮은 저가를 봉 위아래에 적고, 정규장 다음 세션 값은 다음 거래일이 든 기간의 흐린 잠정 봉(`candleLate`)으로 그린다.
  // 정규장 다음 세션 값이 최저보다 낮거나 최고보다 높으면 최저 글자는 그 값 아래에, 최고 글자는 그 값 위에 두어 점선과 '현재' 표시에 겹치지 않게 한다.
  // 봉 그림의 '현재' 표시는 마지막 봉의 고가 위에 찍는다.
  // `stop`을 받으면 점은 끝까지 그리고 '현재' 표시만 `stop`번 점에 찍는다. 봉 그림이면 그 점이 든 봉의 고가 위에 찍는다. `extra`는 `stop`이 마지막 점일 때만 준다.
  // `stop`번 점이 그림 왼쪽 끝 앞이면 '현재' 표시를 찍지 않는다.
  // 그림 왼쪽 끝은 `start`번 점(소수 값이면 두 점 사이)이고, 그 앞 점은 그리지 않는다. 세로 범위(`bounds`, [아래, 위])를 받으면 그 범위로 그리고,
  // 받지 않으면 `dailyBounds`로 정한다. `marks`가 거짓이면 최고·최저 글자를 적지 않는다. 기간을 옮기는 동안 그 사이 그림을 이 세 값으로 그린다.
  daily({ points, extra = null, point = null, kind = "regular", reach = 0, candle = null, height = FIGURE, stop = points.length - 1, start = 0, bounds = null, marks = true }) {
    const L = 4, R = 312, T = 22, B = height - 24, s = frame(height), values = points.map(([, v]) => v), days = points.map(([day]) => day), last = points.length - 1;
    const i0 = Math.max(0, Math.floor(start)), seen = values.slice(i0);
    const groups = candle && candleGroups(days, values, candle.ratios, candle.unit, last).filter((group) => group[1] >= i0);
    const span = Math.max(1, last + reach - start), hi = Math.max(...seen), low = Math.min(...seen);
    const [lo, top] = bounds ?? dailyBounds({ points, extra, candle, height, start });
    const X = (i) => L + (R - L) * (i - start) / span, Y = (v) => B - (v - lo) / (top - lo || 1) * (B - T);
    const room = (v, dy) => (extra == null ? Y(v) : dy > 0 ? Math.max(Y(v), Y(extra)) : Math.min(Y(v), Y(extra))) + dy;
    // 왼쪽 끝에 걸친 선과 봉은 그림 왼쪽 끝에서 자르고, 덧붙인 잠정 봉이 오른쪽 끝에서 3px까지 나가므로 그 3px도 그린다.
    const clipId = `daily-clip-${nextClip()}`, clip = shape("clipPath", { id: clipId });
    clip.append(shape("rect", { x: L, y: 0, width: R - L + 3, height: B }));
    s.append(clip);
    const g = s.appendChild(shape("g", { "clip-path": `url(#${clipId})` }));
    const perMonth = 21 * (R - L) / span, fade = (months) => Math.max(0, Math.min(1, (months * perMonth - 30) / 12));
    points.forEach(([day], i) => {
      if (i && day.slice(0, 7) === points[i - 1][0].slice(0, 7)) return;
      const m = +day.slice(5, 7), opacity = fade(m % 6 === 0 ? 6 : m % 3 === 0 ? 3 : 1);
      if (X(i) >= L + 12 && opacity > 0) s.append(shape("text", { x: X(i), y: B + 17, "font-size": 11, fill: DIMS, "text-anchor": "middle", opacity }, `${m}월`));
    });
    s.append(shape("line", { x1: L, x2: R, y1: B, y2: B, stroke: DIMS, "stroke-width": 1 }));
    if (groups) {
      const late = extra != null && point != null, bars = late ? candleLate(groups, days, candle.unit, extra, point) : groups, centers = drawCandles(g, bars, X, Y, (R - L) / span, R + 3);
      const high = groups.reduce((a, b) => (b[3] > a[3] ? b : a)), lowest = groups.reduce((a, b) => (b[4] < a[4] ? b : a));
      if (marks) [[high, high[3], -5, "최고"], [lowest, lowest[4], 13, "최저"]].forEach(([[a, b], v, dy, text]) => {
        s.append(shape("text", { x: Math.min(Math.max(X((a + b) / 2), L + 36), R - 36), y: room(v, dy), "font-size": 11, fill: DIMS, "text-anchor": "middle" }, `${text} ${candle.label(v)}`));
      });
      const at = late ? bars.length - 1 : bars.findLastIndex(([a]) => a <= stop);
      if (late || stop >= i0) nowMark(s, centers[at], Y(bars[at][3]) - 5, late ? kind : "regular");
      return s;
    } else {
      g.append(shape("path", { d: `M${seen.map((v, k) => `${X(i0 + k)} ${Y(v)}`).join("L")}`, fill: "none", stroke: PRICE,
                               "stroke-width": 1.4 - .4 * Math.max(0, Math.min(1, (last - start - 63) / 693)), "stroke-linejoin": "round" }));
      if (marks) [[i0 + seen.indexOf(hi), -7, "최고"], [i0 + seen.indexOf(low), 15, "최저"]].forEach(([i, dy, text]) => {
        s.append(shape("circle", { cx: X(i), cy: Y(values[i]), r: 2.5, fill: PRICE }));
        s.append(shape("text", { x: Math.min(Math.max(X(i), L + 36), R - 36), y: room(values[i], dy), "font-size": 11, fill: DIMS, "text-anchor": "middle" }, `${text} ${points[i][2]}`));
      });
    }
    const [end, ahead] = extra != null ? [extra, 1] : [values[stop], 0];
    if (extra != null) {
      s.append(shape("path", { d: `M${X(last)} ${Y(values[last])}L${X(last + ahead)} ${Y(end)}`, fill: "none", stroke: PRICE, "stroke-width": 1.4, "stroke-dasharray": "2 2" }));
      s.append(shape("circle", { cx: X(last), cy: Y(values[last]), r: 2, fill: PRICE }));
    }
    if (extra != null || stop >= i0) nowMark(s, X((extra != null ? last : stop) + ahead), Y(end), extra != null ? kind : "regular");
    return s;
  },
  // 묶음 막대: 묶음마다 [이름, [[값, 글자], ...]]이고 막대는 0 가로선에서 위나 아래로 그린다. 세로축은 `min`에서 `max`까지다.
  // 묶음 안 막대가 여럿이면 묶음마다 마지막 막대를 흰색, 나머지를 회색으로 칠하고 `items`의 막대 이름을 그림 위에 범례로 적는다.
  // 묶음마다 막대가 하나면 마지막 묶음의 막대만 흰색이다. 값 글자는 막대 끝 바깥에 적는다.
  // 값 글자가 들어갈 폭(묶음 안 막대가 여럿이면 막대 하나의 폭과 간격, 하나면 묶음 하나의 폭)보다 길면 값 뒤 단위를 떼고 숫자만 적는다.
  // 단위는 카드 머리의 값 뒤에 있다. 막대가 하나인 묶음에서 숫자만 적어도 폭을 넘으면 흰 막대에만 값을 적는다.
  // 묶음 안 막대가 여럿이면 흰 막대, 회색 막대 순서로, 같은 색 안에서는 마지막 묶음부터 값을 적되 이미 적은 값 글자와 겹치는 값은 적지 않는다.
  // 묶음 이름은 그림 아래에 적고, 묶음 하나의 폭보다 길면 마지막 띄어쓰기에서 두 줄로 나눈다.
  bars({ items = [], groups, min, max }) {
    const x0 = 6, x1 = 314, top = items.length > 1 ? 44 : 30, s = canvas(FIGURE), n = groups[0][1].length;
    const slot = (x1 - x0) / groups.length, gap = 4, w = Math.min(40, (slot * 0.62 - gap * (n - 1)) / n);
    const wrap = groups.some(([name]) => name.includes(" ") && textWidth(name, 12) > slot - 6), bottom = wrap ? 134 : 146;
    const Y = (v) => top + (bottom - top) * (max - Math.min(max, Math.max(min, v))) / (max - min), zero = Y(0);
    const room = n > 1 ? w + gap : slot - 4, texts = groups.flatMap(([, bars]) => bars.map(([, text]) => text));
    const short = texts.some((text) => textWidth(text, 12.5) > room), bare = (text) => (short ? text.replace(/[^\d.%]+$/, "") : text);
    const lit = (g, k) => (n > 1 ? k === n - 1 : g === groups.length - 1), left = (g) => x0 + slot * g + (slot - (w * n + gap * (n - 1))) / 2;
    const end = (v) => (Math.abs(Y(v) - zero) < 2 ? zero + (v >= 0 ? -2 : 2) : Y(v));
    const every = texts.every((text) => textWidth(bare(text), 12.5) <= room), placed = [], shown = new Set();
    if (n > 1) {
      const order = groups.flatMap(([, bars], g) => bars.map(([v, text], k) => ({ g, k, v, text })))
        .sort((a, b) => lit(b.g, b.k) - lit(a.g, a.k) || b.g - a.g);
      order.forEach(({ g, k, v, text }) => {
        const x = left(g) + k * (w + gap) + w / 2, half = textWidth(bare(text), 12.5) / 2, y = v >= 0 ? end(v) - 8 : end(v) + 17;
        const box = [x - half - 2, x + half + 2, y - 13, y + 3];
        if (placed.some((b) => !(box[1] <= b[0] || b[1] <= box[0] || box[3] <= b[2] || b[3] <= box[2]))) return;
        placed.push(box);
        shown.add(`${g}-${k}`);
      });
    }
    const labeled = (g, k) => (n > 1 ? shown.has(`${g}-${k}`) : every || lit(g, k));
    groups.forEach(([name, bars], g) => {
      bars.forEach(([v, text], k) => {
        const x = left(g) + k * (w + gap), up = v >= 0, on = lit(g, k), edge = end(v);
        const r = Math.min(4, Math.abs(edge - zero) / 2, w / 2), tip = up ? r : -r;
        const bar = shape("path", { d: `M${x} ${zero}V${edge + tip}Q${x} ${edge} ${x + r} ${edge}H${x + w - r}Q${x + w} ${edge} ${x + w} ${edge + tip}V${zero}Z`,
                                    fill: on ? "#EAEAEA" : "#7A828C", opacity: on ? 1 : 0.55 });
        bar.append(shape("title", {}, `${name} ${items[k] ?? ""} ${text}`.replace(/\s+/g, " ")));
        s.append(bar);
        if (labeled(g, k)) s.append(shape("text", { x: x + w / 2, y: up ? edge - 8 : edge + 17, "text-anchor": "middle", "font-size": 12.5,
                                                  "font-weight": 700, fill: on ? "#EAEAEA" : "#7A828C" }, bare(text)));
      });
      const cut = wrap ? name.lastIndexOf(" ") : -1, lines = cut > 0 ? [name.slice(0, cut), name.slice(cut + 1)] : [name];
      lines.forEach((line, j) => s.append(shape("text", { x: x0 + slot * (g + 0.5), y: bottom + 18 + 15 * j + (lines.length < 2 && wrap ? 7 : 0),
                                                         "text-anchor": "middle", "font-size": 12, fill: "#A7ABB0" }, line)));
    });
    s.append(shape("line", { x1: x0, y1: zero, x2: x1, y2: zero, stroke: "#7A828C", "stroke-width": 1.2 }));
    if (items.length > 1) legend(s, items.map((item, k) => (k === n - 1 ? [item, "#EAEAEA", "box"] : [item, "#7A828C", "box", 0.55])), x1);
    return s;
  },
  // 표: `columns`는 열 이름, `rows`는 줄마다 칸 글자다. `focus` 열은 흰 글씨로 쓴다.
  table({ columns, rows, focus }) {
    const table = document.createElement("table"), cell = (tag, text, j) => Object.assign(document.createElement(tag), {
      textContent: text, className: j === focus ? "focus" : "" });
    table.createTHead().insertRow().append(...columns.map((text, j) => cell("th", text, j)));
    const body = table.createTBody();
    rows.forEach((row) => body.insertRow().append(...row.map((text, j) => cell("td", text, j))));
    return table;
  },
  // 0 기준 위아래 막대: 열마다 [이름, 값, 글자]이고, 가운데 0 가로선에서 양수는 위로, 음수는 아래로 그린다. 첫 열 막대와 글자는 흰색,
  // 나머지 열은 회색이다. 값 글자는 막대 끝 바깥에, 열 이름은 그림 아래에 적는다. 세로축은 위아래로 `max`까지이고, 그 끝에서 그림 끝까지는
  // 값 글자 한 줄을 적을 여백으로 남기고, `max`를 넘는 막대는 축 끝에서 자른다. `max`는 날마다 같아서 `step` 높이와 `-step` 높이의
  // 점선 가로선은 날짜를 바꿔도 같은 높이에 있다. 세로축 오른쪽 여백에는 `step` 높이에 인상을, `-step` 높이에 인하를 적는다.
  diverge({ rows, max, step }) {
    const x0 = 6, x1 = 262, top = 8, base = 148, mid = (top + base) / 2, reach = (base - top) / 2 - 18, s = canvas(FIGURE);
    const slot = (x1 - x0) / rows.length, w = Math.min(40, slot * 0.5), Y = (v) => mid - reach * Math.min(1, Math.max(-1, v / max));
    [step, -step].forEach((v) => s.append(shape("line", { x1: x0, y1: Y(v), x2: x1, y2: Y(v), stroke: "#7A828C", "stroke-width": 1, "stroke-dasharray": "3 3", opacity: 0.7 })));
    rows.forEach(([name, v, text], i) => {
      const x = x0 + slot * i + (slot - w) / 2, up = v >= 0, end = Math.abs(Y(v) - mid) < 2 ? mid + (up ? -2 : 2) : Y(v), first = i === 0;
      const r = Math.min(4, Math.abs(end - mid) / 2), tip = up ? r : -r;
      const bar = shape("path", { d: `M${x} ${mid}V${end + tip}Q${x} ${end} ${x + r} ${end}H${x + w - r}Q${x + w} ${end} ${x + w} ${end + tip}V${mid}Z`,
                                  fill: first ? "#EAEAEA" : "#7A828C", opacity: first ? 1 : 0.55 });
      bar.append(shape("title", {}, `${name} ${text}`));
      s.append(bar);
      s.append(shape("text", { x: x + w / 2, y: up ? end - 8 : end + 17, "text-anchor": "middle", "font-size": 12.5, "font-weight": 700,
                               fill: first ? "#EAEAEA" : "#7A828C" }, text));
      s.append(shape("text", { x: x + w / 2, y: base + 20, "text-anchor": "middle", "font-size": 12, fill: first ? "#EAEAEA" : "#A7ABB0" }, name));
    });
    s.append(shape("line", { x1: x0, y1: mid, x2: x1, y2: mid, stroke: "#7A828C", "stroke-width": 1.2 }));
    [[Y(step), "인상"], [Y(-step), "인하"]].forEach(([y, name]) =>
      s.append(shape("text", { x: x1 + 10, y: y + 4, "font-size": 11, fill: "#7A828C" }, name)));
    return s;
  },
  // 사건 연표: 사건마다 [날짜, 이름]이고 위에서 아래로 앞선 사건부터 적는다. 세로선 위에 사건마다 점을 찍고, 마지막 사건은 흰 점과 흰 글씨로,
  // 앞선 사건은 회색으로 적는다. 날짜는 세로선 왼쪽에 끝을 맞춰 적고, 사건 사이 간격은 사건이 많을수록 좁힌다.
  timeline({ events }) {
    const n = events.length, gap = Math.min(34, 150 / Math.max(1, n - 1)), top = 12, s = frame(top * 2 + gap * (n - 1));
    const x = 6 + Math.max(...events.map(([day]) => textWidth(day, 12))) + 14, Y = (i) => top + gap * i;
    s.append(shape("line", { x1: x, x2: x, y1: Y(0), y2: Y(n - 1), stroke: DIMS, "stroke-width": 1.5, opacity: 0.55 }));
    events.forEach(([day, name], i) => {
      const last = i === n - 1;
      s.append(shape("text", { x: x - 14, y: Y(i) + 4, "text-anchor": "end", "font-size": 12, fill: last ? "#EAEAEA" : DIMS }, day));
      s.append(shape("circle", last ? { cx: x, cy: Y(i), r: 5.5, fill: "#EAEAEA", stroke: "#1d1e21", "stroke-width": 2 }
        : { cx: x, cy: Y(i), r: 4, fill: DIMS, stroke: "#1d1e21", "stroke-width": 2 }));
      s.append(shape("text", { x: x + 14, y: Y(i) + 4.5, "font-size": 13, "font-weight": last ? 700 : 400, fill: last ? "#EAEAEA" : "#A7ABB0" }, name));
    });
    return s;
  },
  // 지도: `view`의 경계 파일을 받아 그림 위 범례 아래에 그린다. `categories`는 [이름, 색], `regions`는 [지역 코드, 분류 번호],
  // `points`는 [이름, 경도, 위도, 분류 번호]다. 경계 파일을 받는 동안 그림에 `data-pending`을 단다.
  map(figure) {
    const top = 28, tall = figure.view === "us-states" ? 200 : 220, s = shape("svg", { viewBox: `0 0 320 ${top + tall}`, "data-pending": "" });
    const used = new Set(figure.regions.map(([, k]) => k));
    legend(s, figure.categories.map(([name, color], k) => [name, color, used.has(k) ? "box" : "dot"]));
    mapOf(figure.view).then((data) => drawMap(s, figure, data, top, tall)).finally(() => s.removeAttribute("data-pending"));
    return s;
  },
};

// 카드 값 하나로 지표 카드를 만든다. 위 줄에 이름과 기준일, 가운데 줄에 값·상태·보조 값, 아래에 그림이나 표를 둔다.
// 값이 없는 카드는 가운데 줄을 두지 않고, 상태가 없는 카드는 상태를 적지 않는다.
export function gauge(c) {
  const box = Object.assign(document.createElement("div"), { className: "gauge" });
  const top = box.appendChild(Object.assign(document.createElement("div"), { className: "top" }));
  const name = top.appendChild(Object.assign(document.createElement("span"), { className: "name", textContent: c.name }));
  top.append(Object.assign(document.createElement("span"), { className: "asof", textContent: c.asof }));
  if (c.value != null) {
    const val = box.appendChild(Object.assign(document.createElement("div"), { className: "val" }));
    const number = val.appendChild(Object.assign(document.createElement("b"), { textContent: c.value }));
    if (c.unit) number.append(Object.assign(document.createElement("small"), { textContent: c.unit }));
    if (c.state) {
      const state = val.appendChild(Object.assign(document.createElement("span"), { className: "state", style: `color:${c.state[1]}` }));
      state.append(document.createElement("i"), c.state[0]);
    }
    if (c.note) val.append(Object.assign(document.createElement("span"), { className: "note", textContent: c.note }));
  }
  if (c.figure) box.appendChild(GAUGES[c.figure.type](c.figure)).classList.add("figure");
  return [box, name];
}

// 이슈 그래프 자리에 카드를 그리고, 카드 값에 그래프 설명(`caption`)이 있으면 카드 아래에 사진 설명과 같은 글씨로 단다.
// 카드 값은 `build.py`가 그림에 단 `data-card`다.
export function issueChart(figure) {
  const c = JSON.parse(figure.dataset.card);
  figure.append(gauge(c)[0]);
  if (c.caption) figure.append(Object.assign(document.createElement("figcaption"), { textContent: c.caption }));
}
