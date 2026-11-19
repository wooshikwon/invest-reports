// @ts-nocheck
import { gaugeCard, indexInk } from "../shared/card";
import { figure, signed, tone } from "../shared/format";
import { DIMS, shape } from "../shared/svg";
// 내 자산 페이지와 거래 내역 화면이 함께 쓰는 글씨. 달러는 `$`와 소수 둘째 자리까지, 원화는 원 단위 정수로 쓰고, `bare`면 원화 뒤 "원"을 뺀다.
export const assetSign = (v) => (v > 0 ? "+" : v < 0 ? "−" : "");
export const assetMoney = (v, currency, bare) => currency === "USD" ? `$${figure(Math.abs(v))}` : `${Math.round(Math.abs(v)).toLocaleString("ko-KR")}${bare ? "" : "원"}`;
export const assetText = (value) => Object.assign(document.createElement("span"), { textContent: value }).innerHTML;
export const assetShares = (v) => `${v.toLocaleString("en-US", { maximumFractionDigits: 6 })}주`;
export const assetRow = (name, sub, value, tail) => `<div class="asset-item"><div><strong>${name}</strong><small>${sub}</small></div>`
  + `<div><strong>${value}</strong>${tail ? `<small>${tail}</small>` : ""}</div></div>`;
export const assetDay = (date) => `${+date.slice(5, 7)}.${+date.slice(8, 10)}`;
// 집행 신호등 카드. 값(`signal`)은 거래 내역 값의 `signal`이고, 그 지수(`index`)의 값이 없으면 카드를 두지 않는다. 옵티마이저 게이트와
// 조건부 게이트 가운데 더 묶는 관문(빨강 > 주황 > 초록) 한 줄만 그 관문의 이름, 색, 배치가 쓴 이유로 쓰고, 두 관문의 색이 같으면 옵티마이저 게이트를 쓴다.
// 옵티마이저 게이트가 초록이면 카드를 단추(`go`)로 만들어, 누르면 그날 집행 요청을 맨 위에 두는 거래 내역 화면을 연다.
export const assetSignal = (signal, index) => {
  const sector = signal?.sectors?.[index];
  if (!sector) return "";
  const rank = ["green", "orange", "red"], { optimizer, conditional } = sector;
  const [name, value] = rank.indexOf(conditional.color) > rank.indexOf(optimizer.color) ? ["조건부 게이트", conditional] : ["옵티마이저 게이트", optimizer];
  const go = optimizer.color === "green" ? ' go" role="button" tabindex="0' : "";
  return `<div class="signal${go}"><div class="gate"><i class="lamp ${value.color}"></i><div><strong>${name}</strong><p>${assetText(value.reason)}</p></div></div></div>`;
};
// 내 자산 페이지의 그림 카드. 값(`perf`)은 계좌 요약의 `performance.sectors.{지수}`이고, 값이 없는 카드는 뺀다. 카드 이름과 상자 목록(`cards`)과 다시 그리는 함수(`show`)를 돌려준다.
// 배율 카드는 위 줄에 목표 배율을, 큰 값에 현재 배율을 현재 배율 선과 같은 주황 글씨로 쓴다. 그림에는 오늘 가격 경로들의 배율 분포(지수색 면)와 이슈가 없을 때의 분포(회색 면)를 배율 축에 그리고,
// 목표 배율에 지수색 실선, 현재 배율에 주황 점선을 긋는다. 누적 수익률 카드는 첫날 대비 고정 배율·판단·집행 누적 수익률을,
// 초과 수익률 카드는 판단과 집행의 누적 수익률에서 고정 배율 누적 수익률을 뺀 값을 거래일 축에 그린다. 큰 값은 집행 선의 마지막 값이다.
// `show(past)`는 `past`가 없으면 받은 값으로 그린다. 지난 날짜면 배율 카드는 그날 판단의 배율 분포(`past.chart`)에 그날 현재·목표 배율(`past.current`, `past.target`)을 긋고,
// 수익률 카드는 그날 기준 가격 날짜(`past.base_date`)까지의 값만 그린다. 그날 현재 배율을 모르면 현재 배율 선을 긋지 않고 큰 값에 "기록 없음"을 쓴다.
export function assetCards(perf) {
  const W = 320, H = 236, B = 212, L = 6, R = W - 6, T = 22, color = indexInk(W), NOW = "#FF9F1C", BASE = "#A7ABB0";
  const big = (text, unit) => [text, Object.assign(document.createElement("small"), { textContent: unit })];
  const cards = [], draws = [];
  const lev = perf?.leverage;
  if (lev?.today?.length > 1) {
    const c = gaugeCard("", W, H), s = c.svg;
    draws.push((past) => {
      const den = past ? { ...past.chart, anchor: lev.anchor, current: past.current, target: past.target ?? lev.anchor * (1 + past.chart.mean) } : lev, n = den.today.length;
      c.head("", den.current == null ? "기록 없음" : big(den.current.toFixed(3), "배"), `목표 ${den.target.toFixed(3)}배`);
      c.value.className = "";
      c.value.style.color = den.current == null ? DIMS : NOW;
      const xs = Array.from({ length: n }, (_, i) => den.anchor * (1 + den.low + (den.high - den.low) * i / (n - 1)));
      const X = (v) => Math.min(R, Math.max(L, L + (v - xs[0]) / (xs[n - 1] - xs[0]) * (R - L))), peak = Math.max(...den.today, ...den.quiet);
      const Y = (v) => B - v / peak * (B - T);
      const area = (values) => `M${X(xs[0])} ${B}L${values.map((v, i) => `${X(xs[i])} ${Y(v)}`).join("L")}L${X(xs[n - 1])} ${B}Z`;
      s.replaceChildren();
      s.append(shape("path", { d: area(den.quiet), fill: "rgba(167, 171, 176, .14)" }));
      s.append(shape("path", { d: area(den.today), fill: color, opacity: .2 }));
      if (den.current != null) s.append(shape("line", { x1: X(den.current), x2: X(den.current), y1: T, y2: B, stroke: NOW, "stroke-width": 1.6, "stroke-dasharray": "4 3" }));
      s.append(shape("line", { x1: X(den.target), x2: X(den.target), y1: T, y2: B, stroke: color, "stroke-width": 1.6 }));
      s.append(shape("line", { x1: L, x2: R, y1: B, y2: B, stroke: DIMS }));
      const gap = xs[n - 1] - xs[0] > 3 ? 1 : 0.5;
      for (let v = Math.ceil(xs[0] / gap) * gap; v <= xs[n - 1] + 1e-9; v += gap) {
        s.append(shape("line", { x1: X(v), x2: X(v), y1: B, y2: B + 4, stroke: DIMS }));
        s.append(shape("text", { x: X(v), y: B + 18, "font-size": 11, fill: den.current != null && Math.abs(v - den.current) < gap / 4 ? "#EAEAEA" : DIMS, "text-anchor": "middle" }, `${v.toFixed(1)}배`));
      }
    });
    cards.push(["배율", c.box]);
  }
  const ret = perf?.returns;
  // 선 그림은 값 범위를 1·2·5 단위 눈금 네댓 칸으로 나눠 오른쪽 끝에 눈금 값을 쓰고, 그림 아래에 첫날·가운데·마지막 거래일을 쓴다.
  // 고정 배율 선이 0인 초과 수익률 그림은 0 눈금을 회색 점선으로 긋는다.
  const lines = (c, series, unit, flat) => {
    const s = c.svg, n = series[0][0].length, all = [0, ...series.flatMap(([values]) => values)], P = R - 40;
    let lo = Math.min(...all), hi = Math.max(...all);
    if (hi - lo < 1e-4) { lo -= 0.005; hi += 0.005; }
    const raw = (hi - lo) / 4, power = 10 ** Math.floor(Math.log10(raw)), step = [1, 2, 5, 10].map((m) => m * power).find((m) => m >= raw);
    lo = Math.floor(lo / step + 1e-9) * step; hi = Math.ceil(hi / step - 1e-9) * step;
    const X = (i) => L + i / (n - 1) * (P - L), Y = (v) => B - (v - lo) / (hi - lo) * (B - T), digits = step >= 0.01 ? 0 : 1;
    s.replaceChildren();
    for (let k = 0; k <= Math.round((hi - lo) / step); k++) {
      const v = lo + k * step, zero = Math.abs(v) < step / 2;
      s.append(shape("line", { x1: L, x2: P, y1: Y(v), y2: Y(v), ...(zero && flat ? { stroke: BASE, "stroke-dasharray": "2 3" } : { stroke: zero ? "rgba(255, 255, 255, .22)" : "rgba(255, 255, 255, .07)" }) }));
      s.append(shape("text", { x: R, y: Y(v) + 4, "font-size": 11, fill: DIMS, "text-anchor": "end" }, `${zero ? "0" : signed(v * 100, digits)}${unit}`));
    }
    series.forEach(([values, stroke, dash]) => s.append(shape("path", { d: `M${values.map((v, i) => `${X(i)} ${Y(v)}`).join("L")}`, fill: "none", stroke,
      "stroke-width": dash ? 1.2 : 1.8, "stroke-linejoin": "round", ...(dash ? { "stroke-dasharray": "3 3" } : {}) })));
    [[0, "start"], [Math.floor((n - 1) / 2), "middle"], [n - 1, "end"]].forEach(([i, anchor]) =>
      s.append(shape("text", { x: X(i), y: B + 18, "font-size": 11, fill: DIMS, "text-anchor": anchor }, assetDay(ret.days[i]))));
  };
  // 그날까지의 값이 두 거래일보다 적으면 그림을 비우고 큰 값에 "기록 없음"을 쓴다.
  const figureOf = (c, v, unit) => {
    if (v == null) { c.head("", "기록 없음"); c.value.className = ""; c.svg.replaceChildren(); return false; }
    c.head("", big(signed(v * 100, 2), unit)); c.value.className = tone(v); return true;
  };
  if (ret?.days?.length > 1) {
    const cum = gaugeCard(`첫날 ${assetDay(ret.days[0])} 대비 집행 누적 수익률`, W, H), over = gaugeCard("고정 배율 대비 집행 초과 수익률", W, H);
    draws.push((past) => {
      const n = past ? ret.days.filter((day) => day <= past.base_date).length : ret.days.length, last = n - 1;
      const [anchor, target, realized] = [ret.anchor, ret.target, ret.realized].map((values) => values.slice(0, n));
      const gap = (values) => values.map((v, i) => v - anchor[i]);
      if (figureOf(cum, n > 1 ? realized[last] : null, "%")) lines(cum, [[anchor, BASE, true], [target, color], [realized, NOW]], "%");
      if (figureOf(over, n > 1 ? realized[last] - anchor[last] : null, "%p")) lines(over, [[gap(target), color], [gap(realized), NOW]], "%p", true);
    });
    cards.push(["누적 수익률", cum.box], ["초과 수익률", over.box]);
  }
  const show = (past) => draws.forEach((draw) => draw(past));
  show(null);
  return { cards, show };
}
