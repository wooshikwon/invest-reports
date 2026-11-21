// @ts-nocheck
import "./asset-view.css";
import { ASSET_URL } from "../shared/account";
import { gaugeCard, indexInk } from "../shared/card";
import { INDEX_NAME, INDEX_TITLE } from "../shared/chrome";
import { figure, signed, tone } from "../shared/format";
import { slider } from "../shared/motion";
import { roll } from "../shared/roll";
import { closeAt, sessionAt, sessionTag } from "../shared/session";
import { key, visit } from "../shared/route";
import { DIMS, PRICE, nearest, nowMark, onTap, shape } from "../shared/svg";
import { feelPress, feelSlide, tg } from "../shared/telegram";
// 내 자산 조각. 내 자산 페이지와 거래 내역 화면의 글씨와 그림은 모두 이 파일에 있고, 공개 화면(`asset.ts`, `trades.ts`)은 Worker가 계좌 요약을 건넨 뒤에만
// 이 파일을 `import()`로 불러온다. 빌드는 이 파일과 `asset-view.css`를 `assets/asset-view-*.js`·`assets/asset-view-*.css`로 따로 낸다.
// 내 자산 페이지와 거래 내역 화면이 함께 쓰는 글씨. 달러는 `$`와 소수 둘째 자리까지, 원화는 원 단위 정수로 쓰고, `bare`면 원화 뒤 "원"을 뺀다.
export const assetSign = (v) => (v > 0 ? "+" : v < 0 ? "−" : "");
export const assetMoney = (v, currency, bare) => currency === "USD" ? `$${figure(Math.abs(v))}` : `${Math.round(Math.abs(v)).toLocaleString("ko-KR")}${bare ? "" : "원"}`;
export const assetText = (value) => Object.assign(document.createElement("span"), { textContent: value }).innerHTML;
export const assetShares = (v) => `${v.toLocaleString("en-US", { maximumFractionDigits: 6 })}주`;
export const assetRow = (name, sub, value, tail) => `<div class="asset-item"><div><strong>${name}</strong><small>${sub}</small></div>`
  + `<div><strong>${value}</strong>${tail ? `<small>${tail}</small>` : ""}</div></div>`;
export const assetDay = (date) => `${+date.slice(5, 7)}.${+date.slice(8, 10)}`;
// 금액 단위와 내 자산 페이지에서 보던 그림 카드는 기기에 적어 두고 다음에 열 때도 그대로 쓴다. 내 자산 페이지와 거래 내역 화면은 같은 금액 단위를 쓴다.
// 내 자산 화면의 고른 상태. 금액 단위(`unit`), 그림 카드(`card`), 총 자산 단추를 켰는지(`whole`), 판단 선을 보이는지(`judge`)를 기기에 남긴다.
export const assetView = () => {
  const view = { unit: "KRW", card: 0, whole: false, judge: true };
  try {
    const kept = JSON.parse(localStorage.getItem("asset-view"));
    view.unit = kept.unit === "USD" ? "USD" : "KRW"; view.card = kept.card | 0; view.whole = kept.whole === true; view.judge = kept.judge !== false;
  } catch {}
  return view;
};
export const assetRemember = (view) => { try { localStorage.setItem("asset-view", JSON.stringify(view)); } catch {} };
// 금액 단위 단추. 칸마다 `data-unit`에 통화를 적고, 고른 칸을 밝게 칠한다.
export const assetUnits = (unit) => '<div class="seg">' + [["USD", "$"], ["KRW", "원"]].map(([currency, label]) =>
  `<button type="button" data-unit="${currency}"${currency === unit ? ' class="on"' : ""}>${label}</button>`).join("") + "</div>";
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
// 시각 `time`의 기준 시각 글씨. 요약 절의 그림 카드처럼 "미국 11/20 정규장, 23:43 KST"로 쓰고, 뉴욕 시각으로 세션을 정해 그 세션의 색으로 칠한다.
// 04:00~09:30 ET는 프리마켓, 09:30~16:00 ET는 정규장, 16:00~20:00 ET는 애프터마켓이고, 그 밖은 주간거래다. 20:00 ET 뒤의 주간거래는 다음 날 세션의 날짜를 쓴다.
const NY_CLOCK = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const stamp = (time) => {
  const at = Date.parse(time), part = Object.fromEntries(NY_CLOCK.formatToParts(at).map(({ type, value }) => [type, value])), clock = +part.hour * 60 + +part.minute;
  const [kind, name] = clock >= 240 && clock < 570 ? ["pre", "프리마켓"] : clock >= 570 && clock < 960 ? ["regular", "정규장"] : clock >= 960 && clock < 1200 ? ["after", "애프터마켓"] : ["day", "주간거래"];
  const day = clock >= 1200 ? new Date(Date.UTC(+part.year, +part.month - 1, +part.day + 1)).toISOString().slice(0, 10) : `${part.year}-${part.month}-${part.day}`;
  return sessionTag(kind, `미국 ${day.slice(5, 7)}/${day.slice(8, 10)} ${name}, ${new Date(at + 9 * 3600e3).toISOString().slice(11, 16)} KST`);
};
// 내 자산 페이지의 그림 카드. 값(`perf`)은 계좌 요약의 `performance.sectors.{지수}`이고, 값이 없는 카드는 뺀다. 지수(`index`)는 이름 줄과 큰 값을 굴리는 자리 이름에 쓴다.
// `times`는 최신 날짜 점을 셈한 체결가의 시각(`live`)과 계좌 요약을 만든 시각(`summary`)이다. 체결가가 계좌 요약보다 이르면 Worker가 `live`를 빼고 최신 날짜 점을 요약 시각의 가격으로 셈하므로, 그때 `live`는 요약 시각이다. 카드 이름과 상자 목록(`cards`)과 다시 그리는 함수(`show`)를 돌려준다.
// 카드는 요약 절의 그림 카드처럼 맨 위 줄에 값의 기준 시각을, 그 아래 이름 줄 왼쪽에 "나스닥 100"처럼 지수 이름을 쓴다. 이름 줄 오른쪽에는 수익률 카드면 판단 보기 단추를,
// 배율 카드면 목표 배율을 흐린 글씨로 둔다. 판단 보기 단추는 두 수익률 카드에서 판단 선(지수색)을 함께 보이거나 감추고, 그 상태(`view.judge`)를 기기에 남긴다(`remember`).
// 카드 순서는 누적 수익률, 초과 수익률, 배율이다. 누적 수익률 카드는 첫날 대비 고정 배율·판단·집행 누적 수익률을,
// 초과 수익률 카드는 판단과 집행의 누적 수익률에서 고정 배율 누적 수익률을 뺀 값을 날짜 지점 축에 그린다. 큰 값은 집행 선의 값이다.
// 축은 정산한 거래일마다 한 점이고, Worker가 1분마다 다시 셈한 최신 날짜 지점의 값(`returns.now`)이 있으면 그 날짜 점을 하나 더 둔다.
// 최신 날짜 점의 고정 배율·판단 값은 기준 배율과 목표 배율을 그대로 들고 있다고 본 값이다. Worker가 판단 값을 셈하지 못하면 판단 선은 마지막 정산일에서 끝난다.
// 수익률 카드의 기준 시각은 최신 날짜 점이 있으면 체결가 시각, 없으면 마지막 거래일의 정규장 종가 시각이다.
// 배율 카드는 이름 줄 오른쪽에 목표 배율을, 큰 값에 현재 배율을 흰 글씨로 쓰고, 기준 시각은 계좌 요약을 만든 시각이다. 그림에는 오늘 가격 경로들의 배율 분포(지수색 면)와 이슈가 없을 때의 분포(회색 면)를 배율 축에 그리고,
// 목표 배율에 지수색 실선, 현재 배율에 흰 점선을 긋는다. 집행 선과 현재 배율 선은 다른 페이지의 가격 선과 같은 흰색(`PRICE`)이다.
// 누적 수익률·초과 수익률 카드는 그림을 누르면 누른 가로 자리에서 가장 가까운 날짜 점으로 '현재' 표시(`nowMark`)를 옮기고, 큰 값을 그 점의 값으로,
// 기준 시각을 그날 정규장 종가 시각으로 바꾼다. 선은 줄이지 않는다. 고른 점이 첫날이면 큰 값에 "기록 없음"을 쓰고, 가장 늦은 점을 누르면 처음 상태로 돌아간다.
// 두 카드는 같은 날짜를 함께 고르고, 고른 날짜(`pin.day`)는 호출하는 쪽이 들고 있어 카드를 다시 만들어도 이어진다. 가장 늦은 점을 고르면 `pin.day`를 비워 새 최신 점을 따른다.
// 배율 카드는 시간 축이 없어 누르기 동작이 없다.
export function assetCards(perf, index, times = {}, pin = { day: null }, view = { judge: true }, remember = () => {}) {
  const W = 320, H = 236, B = 212, L = 6, R = W - 6, T = 22, color = indexInk(W), NOW = PRICE, BASE = "#A7ABB0";
  const big = (text, unit) => [text, Object.assign(document.createElement("small"), { textContent: unit })];
  // 카드 틀에 이름 줄을 더한다. 이름 줄이 같은 높이를 차지해 카드를 넘겨도 값과 그림이 같은 높이에 있다.
  const card = (slot) => {
    const c = gaugeCard("", W, H, `${index}-${slot}`), title = c.box.insertBefore(Object.assign(document.createElement("div"), { className: "top title" }), c.value.parentNode);
    c.side = Object.assign(document.createElement("span"), { className: "ctx" });
    title.append(Object.assign(document.createElement("span"), { className: "name", textContent: INDEX_TITLE[index] || INDEX_NAME[index] }), c.side);
    return c;
  };
  // 날짜(`day`)의 정규장 종가 시각 글씨.
  const settled = (day) => sessionTag("regular", sessionAt("정규장", closeAt(day)));
  const cards = [];
  const lev = perf?.leverage;
  let lever = null;
  if (lev?.today?.length > 1) {
    const c = card("lever"), s = c.svg;
    const n = lev.today.length;
    c.value.className = "";
    c.head("", lev.current == null ? "기록 없음" : big(lev.current.toFixed(3), "배"), stamp(times.summary));
    c.side.textContent = `목표 ${lev.target.toFixed(3)}배`;
    c.value.style.color = lev.current == null ? DIMS : "";
    const xs = Array.from({ length: n }, (_, i) => lev.anchor * (1 + lev.low + (lev.high - lev.low) * i / (n - 1)));
    const X = (v) => Math.min(R, Math.max(L, L + (v - xs[0]) / (xs[n - 1] - xs[0]) * (R - L))), peak = Math.max(...lev.today, ...lev.quiet);
    const Y = (v) => B - v / peak * (B - T);
    const area = (values) => `M${X(xs[0])} ${B}L${values.map((v, i) => `${X(xs[i])} ${Y(v)}`).join("L")}L${X(xs[n - 1])} ${B}Z`;
    s.replaceChildren();
    s.append(shape("path", { d: area(lev.quiet), fill: "rgba(167, 171, 176, .14)" }));
    s.append(shape("path", { d: area(lev.today), fill: color, opacity: .2 }));
    if (lev.current != null) s.append(shape("line", { x1: X(lev.current), x2: X(lev.current), y1: T, y2: B, stroke: NOW, "stroke-width": 1.6, "stroke-dasharray": "4 3" }));
    s.append(shape("line", { x1: X(lev.target), x2: X(lev.target), y1: T, y2: B, stroke: color, "stroke-width": 1.6 }));
    s.append(shape("line", { x1: L, x2: R, y1: B, y2: B, stroke: DIMS }));
    const gap = xs[n - 1] - xs[0] > 3 ? 1 : 0.5;
    for (let v = Math.ceil(xs[0] / gap) * gap; v <= xs[n - 1] + 1e-9; v += gap) {
      s.append(shape("line", { x1: X(v), x2: X(v), y1: B, y2: B + 4, stroke: DIMS }));
      s.append(shape("text", { x: X(v), y: B + 18, "font-size": 11, fill: lev.current != null && Math.abs(v - lev.current) < gap / 4 ? "#EAEAEA" : DIMS, "text-anchor": "middle" }, `${v.toFixed(1)}배`));
    }
    lever = ["배율", c.box];
  }
  const ret = perf?.returns;
  // 선 그림은 값 범위를 1·2·5 단위 눈금 네댓 칸으로 나눠 오른쪽 끝에 눈금 값을 쓰고, 그림 아래에 첫날·가운데·마지막 거래일을 쓴다.
  // 고정 배율 선이 0인 초과 수익률 그림은 0 눈금을 회색 점선으로 긋는다.
  const lines = (c, series, unit, flat, days, at, tap) => {
    const s = c.svg, n = days.length, all = [0, ...series.flatMap(([values]) => values)], P = R - 40;
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
      s.append(shape("text", { x: X(i), y: B + 18, "font-size": 11, fill: DIMS, "text-anchor": anchor }, assetDay(days[i]))));
    nowMark(s, X(at), Y(series.at(-1)[0][at]), "regular");
    const spots = days.map((_, i) => X(i));
    onTap(s, (x) => tap(nearest(spots, x)));
  };
  // 고른 날짜 점이 첫날이면 그림은 그리되 큰 값에 "기록 없음"을 쓴다.
  const figureOf = (c, v, unit, at) => {
    c.value.className = v == null ? "" : tone(v);
    c.head("", v == null ? "기록 없음" : big(signed(v * 100, 2), unit), at);
  };
  if (ret?.days?.length > 1) {
    const cum = card("cum"), over = card("over"), toggles = [cum, over].map((c) => {
      const button = Object.assign(document.createElement("button"), { type: "button", className: "aim", innerHTML: "<span>판단 보기</span>" });
      c.side.replaceWith(button);
      button.addEventListener("click", () => { feelPress(); view.judge = !view.judge; remember(); paint(); });
      return button;
    });
    const now = ret.now && ret.now.day > ret.days.at(-1) ? ret.now : null;
    const days = now ? [...ret.days, now.day] : ret.days;
    const anchor = now ? [...ret.anchor, now.anchor] : ret.anchor, realized = now ? [...ret.realized, now.realized] : ret.realized;
    const target = now?.target != null ? [...ret.target, now.target] : ret.target;
    const gap = (values) => values.map((v, i) => v - anchor[i]);
    const paint = () => {
      const at = pin.day == null ? days.length - 1 : Math.max(0, days.filter((day) => day <= pin.day).length - 1), first = at < 1;
      const when = at < days.length - 1 || !now ? settled(days[at]) : stamp(times.live);
      figureOf(cum, first ? null : realized[at], "%", when);
      figureOf(over, first ? null : realized[at] - anchor[at], "%p", when.cloneNode(true));
      const tap = (i) => { feelPress(); pin.day = i === days.length - 1 ? null : days[i]; paint(); };
      toggles.forEach((button) => { button.classList.toggle("on", view.judge); button.setAttribute("aria-pressed", view.judge); });
      const judged = (values) => (view.judge ? [[values, color]] : []);
      lines(cum, [[anchor, BASE, true], ...judged(target), [realized, NOW]], "%", false, days, at, tap);
      lines(over, [...judged(gap(target)), [gap(realized), NOW]], "%p", true, days, at, tap);
    };
    paint();
    cards.push(["누적 수익률", cum.box], ["초과 수익률", over.box]);
  }
  if (lever) cards.push(lever);
  return cards;
}

// 내 자산 페이지(`page`)를 그리는 함수를 돌려준다. 공개 화면 `asset.ts`가 Worker가 건넨 계좌 요약(`data`)마다 이 함수를 부른다.
export function assetPage(page) {
  const view = assetView(), remember = () => assetRemember(view);
  const chevron = '<svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5l4.5 4.5L6 12.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  // 평가 금액의 가림을 벗겼는지(`bare`)는 미니 앱을 닫을 때까지만 기억하고 기기에는 적지 않으므로, 미니 앱을 열 때마다 보이는 채로 시작한다. 평가 금액을 누르면 가리고 다시 누르면 보인다.
  let last = null, bare = true;
  // 첫 절 내 투자는 보고 있는 리포트 지수의 종목(`sector`)만 모아 평가금 합계와 수익·수익률을 쓰고, 그 아래 그림 카드와 집행 신호등 카드를 둔다.
  // 제목 오른쪽 금액 단위 단추 옆의 총 자산 단추를 켜면(`whole`), 합계 자리에 두 지수 종목과 그 밖의 종목, 대기자금, 원화·달러 현금을 모두 더한 총 자산을 쓰고,
  // 수익·수익률은 모든 보유 종목의 수익과 매입액으로 쓴다. 값은 계좌 요약을 새로 받을 때(1분마다)마다 다시 쓴다.
  // 둘째 절 상세 보유 종목은 그 종목들의 종목 줄을 쓰고, 그 아래 거래 내역 단추를 둔다.
  // 맨 아래 절 내 계좌는 원화·달러 주문 가능 현금을 그 통화로, 대기자금(SGOV)을 고른 단위로 쓴다. SGOV를 들고 있지 않으면 대기자금 줄을 두지 않는다.
  // 그림 카드에서 고른 날짜는 화면을 닫을 때까지 기억해, 새 계좌 요약을 받아 다시 그려도 그 날짜로 그린다.
  const pin = { day: null };
  const fill = (data) => {
    last = data;
    const index = key.split("-")[1], { rate, accounts } = data, unit = view.unit;
    // 금액은 고른 단위로 바꿔 쓴다. 다른 통화 금액은 요약을 만든 시각의 환율로 바꾼다.
    const into = (v, currency) => (currency === unit ? v : unit === "KRW" ? v * rate : v / rate);
    const change = (v, r, bare) => `<span class="${tone(v)}">${assetSign(v)}${assetMoney(v, unit, bare)} (${Math.abs(r * 100).toFixed(1)}%)</span>`;
    const held = data.items.map((item) => ({ ...item, value: into(item.value, item.currency), profit: into(item.profit, item.currency), purchase: into(item.purchase, item.currency) }));
    const mine = held.filter((item) => item.sector === index), waiting = held.find((item) => item.sector === "sgov");
    const total = (field) => (view.whole ? held : mine).reduce((sum, item) => sum + item[field], 0), profit = total("profit"), purchase = total("purchase");
    const cash = Object.entries(accounts).reduce((sum, [currency, summed]) => sum + into(summed.cash, currency), 0), value = total("value") + (view.whole ? cash : 0);
    const item = (it, sub) => assetRow(assetText(it.name), sub, assetMoney(it.value, unit), change(it.profit, it.rate, true));
    const toggle = `<button type="button" class="whole${view.whole ? " on" : ""}" aria-pressed="${view.whole}">총 자산</button>`;
    page.innerHTML = `<h2 class="asset-head">내 투자<span class="tools">${toggle}${assetUnits(unit)}</span></h2><div class="asset-sum${bare ? "" : " veil"}" role="button" tabindex="0"><b class="veiled">평가 금액 보기</b>`
      + `<b>${assetMoney(value, unit)}</b>${change(profit, purchase ? profit / purchase : 0)}</div>`
      + `${assetSignal(data.trades?.signal, index)}<h2>상세 보유 종목</h2>`
      + (mine.length ? mine.map((it) => item(it, assetShares(it.quantity))).join("") : `<p class="status">${INDEX_NAME[index]} 종목을 들고 있지 않다.</p>`)
      + `<button type="button" class="asset-trades">거래 내역${chevron}</button><h2>내 계좌</h2>` + assetRow("원화", "주문 가능", assetMoney(accounts.KRW.cash, "KRW")) + assetRow("달러", "주문 가능", assetMoney(accounts.USD.cash, "USD"))
      + (waiting ? item({ ...waiting, name: "대기자금" }, `${waiting.symbol} ${assetShares(waiting.quantity)}`) : "");
    roll(page.querySelector(".asset-sum b:not(.veiled)"), `${view.whole ? "whole" : index}-sum-${unit}`);
    const perf = data.performance?.sectors?.[index], cards = assetCards(perf, index, { live: data.live?.time || data.time, summary: data.time }, pin, view, remember);
    if (!cards.length) return page.querySelector(".asset-sum").insertAdjacentHTML("afterend", '<p class="status">그림 값이 아직 없다.</p>');
    const bar = document.createElement("div");
    bar.className = "tabs";
    cards.forEach(([label], i) => {
      const button = Object.assign(document.createElement("button"), { textContent: label });
      button.addEventListener("click", () => box.go(i));
      bar.appendChild(button);
    });
    const pick = (i) => { [...bar.children].forEach((button, j) => button.classList.toggle("on", i === j)); if (view.card !== i) { view.card = i; remember(); } };
    const box = slider(cards.map(([, card]) => [card]), page.querySelector(".asset-sum"), { start: Math.min(view.card, cards.length - 1), change: pick, name: "asset-cards", feel: true });
    box.prepend(bar);
  };
  page.addEventListener("click", (event) => {
    const unit = event.target.closest("[data-unit]");
    if (unit && unit.dataset.unit !== view.unit) { feelSlide(); view.unit = unit.dataset.unit; remember(); fill(last); }
    if (event.target.closest(".asset-head .whole")) { feelSlide(); view.whole = !view.whole; remember(); fill(last); }
    if (event.target.closest(".asset-trades, .signal.go")) { feelPress(); visit(key, { trades: key.split("-")[1] }); }
    const sum = event.target.closest(".asset-sum");
    if (sum) { feelPress(); bare = !bare; sum.classList.toggle("veil", !bare); }
  });
  return fill;
}

// 거래 내역 화면의 집행 요청 절과 거래 내역 절. 블록의 출처(`source`)마다 카드 오른쪽 위 스티커 글씨를 두고, 출처가 없는 옛 블록은 스티커를 두지 않는다.
// 새 출처는 이 표와 서버의 출처 판정(`trades.py`)에만 더한다. 필터는 "전체"와 이 표의 출처 순서다.
export const TRADE_SOURCE = { llm: "LLM 매수", manual: "일반 매수" };
// 거래 내역 절 제목 오른쪽에 출처 필터 드롭다운과 금액 단위 단추를 둔다. 드롭다운은 고른 필터 이름과 아래 꺽쇠를 쓰고, 누르면 그 아래에 필터 목록을 펼친다.
// 목록에서 필터를 고르거나 목록 밖을 누르면 목록을 접는다. 체결 금액은 달러로만 받으므로, 원 단위에서는 계좌 요약을 만든 시각의 환율로 바꿔 쓴다.
// 거래 내역은 조회 기간 안의 블록만 쓰고, 기간 투자액도 그 블록만 더한다. 조회 기간은 처음에 오늘(서울 날짜)까지 최근 3개월이고, 화면을 닫으면 처음 값으로 돌아간다.
// 기간 투자액 아래 줄 오른쪽 끝의 기간 단추를 누르면 달력 상자를 띄운다. 달력은 가장 오래된 거래가 있는 달, 조회 시작 달, 최근 3개월의 시작 달 가운데 가장 이른 달부터 이번 달까지를 한 달씩 옆으로 놓고, 조회 끝 날짜의 달을 보이며 연다.
// 달은 좌우로 밀거나 달 이름 양옆의 꺽쇠를 눌러 넘기고, 날짜 판의 높이는 보이는 달의 줄 수에 맞춘다. 날짜를 처음 누르면 시작 날짜로 두고, 다음에 누른 날짜가 시작 날짜와 같거나 뒤면 끝 날짜로 둔다. 시작 날짜보다 앞을 누르면 시작 날짜를 다시 고른다.
// 최근 3개월 단추는 고른 기간을 최근 3개월로 바꾼다. 고른 기간은 끝 날짜까지 고른 뒤 아래 확인 단추를 눌러야 조회 기간이 되고, 닫기 단추나 상자 밖을 누르면 버린다.
export function tradesView(page, index) {
  const WEEK = "일월화수목금토", clock = (runAt) => runAt.slice(11, 16), due = (runAt) => Date.parse(`${runAt}:00+09:00`);
  const side = (value) => (value === "BUY" ? '<span class="side up">매수</span>' : '<span class="side down">매도</span>');
  const view = assetView(), filters = { all: "전체", ...TRADE_SOURCE }, closer = new AbortController();
  const today = new Date(Date.now() + 9 * 36e5).toISOString().slice(0, 10), recent = () => {
    const [y, m, d] = today.split("-").map(Number), end = new Date(Date.UTC(y, m - 3, 0)).getUTCDate();
    return { start: new Date(Date.UTC(y, m - 4, Math.min(d, end))).toISOString().slice(0, 10), end: today };
  };
  let last = null, timer = null, filter = "all", period = recent(), sheet = null;
  const gap = (v) => `${assetSign(v)}${Math.abs(v).toFixed(3)}배`;
  const span = ({ start, end }) => `${start.slice(0, 4) === end.slice(0, 4) ? "" : `${start.slice(2, 4)}.`}${assetDay(start)} ~ ${assetDay(end)}`;
  const icon = '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="3" width="12" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="1.4"/>'
    + '<path d="M2 6.5h12M5.5 1.8v2.6M10.5 1.8v2.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
  const shut = () => { sheet?.remove(); sheet = null; };
  const calendar = () => {
    const blocks = last?.trades?.sectors?.[index] || [], first = [period.start, recent().start, ...blocks.map((b) => b.date)].sort()[0];
    let start = period.start, end = period.end;
    const months = [], names = [];
    for (let y = +first.slice(0, 4), m = +first.slice(5, 7); `${y}-${String(m).padStart(2, "0")}` <= today.slice(0, 7); m === 12 ? (y++, m = 1) : m++) {
      const lead = new Date(Date.UTC(y, m - 1, 1)).getUTCDay(), days = new Date(Date.UTC(y, m, 0)).getUTCDate();
      names.push(`${y}년 ${m}월`);
      months.push(`<section data-month="${y}-${String(m).padStart(2, "0")}"><div class="grid">${"<i></i>".repeat(lead)}` + Array.from({ length: days }, (_, i) => {
        const day = `${y}-${String(m).padStart(2, "0")}-${String(i + 1).padStart(2, "0")}`;
        return `<button type="button" data-day="${day}"${day > today ? " disabled" : ""}${day === today ? ' class="today"' : ""}><span>${i + 1}</span></button>`;
      }).join("") + "</div></section>");
    }
    const box = sheet = document.createElement("div");
    box.className = "help-card period-card";
    box.innerHTML = `<div class="card"><h3>조회 기간<span><button type="button" class="reset">최근 3개월</button><button type="button" class="close" aria-label="닫기">✕</button></span></h3>`
      + `<p class="hint"></p><div class="month"><button type="button" class="prev" aria-label="앞 달">${caret}</button><h4></h4><button type="button" class="next" aria-label="다음 달">${caret}</button></div>`
      + `<div class="week">${[...WEEK].map((d) => `<i>${d}</i>`).join("")}</div><div class="months">${months.join("")}</div><button type="button" class="ok">확인</button></div>`;
    const track = box.querySelector(".months"), at = () => Math.round(track.scrollLeft / track.clientWidth);
    const turn = () => {
      const i = at();
      box.querySelector(".month h4").textContent = names[i];
      box.querySelector(".prev").disabled = i === 0;
      box.querySelector(".next").disabled = i === names.length - 1;
      track.style.height = `${track.children[i].offsetHeight}px`;
    };
    const go = (month, smooth) => {
      const i = Math.max(0, [...track.children].findIndex((s) => s.dataset.month === month));
      track.scrollTo({ left: i * track.clientWidth, behavior: smooth ? "smooth" : "instant" });
      turn();
    };
    const paint = () => {
      box.querySelector(".hint").textContent = end ? span({ start, end }) : "끝 날짜를 눌러요";
      box.querySelector(".ok").disabled = !end;
      box.querySelector(".months").classList.toggle("ranged", !!end && end > start);
      box.querySelectorAll("[data-day]").forEach((cell) => {
        const day = cell.dataset.day;
        cell.classList.toggle("start", day === start);
        cell.classList.toggle("end", day === end);
        cell.classList.toggle("in", !!end && day > start && day < end);
      });
    };
    box.addEventListener("click", (event) => {
      if (event.target === box || event.target.closest(".close")) return shut();
      const step = event.target.closest(".prev, .next");
      if (step) {
        feelSlide();
        return track.scrollTo({ left: (at() + (step.classList.contains("next") ? 1 : -1)) * track.clientWidth, behavior: "smooth" });
      }
      if (event.target.closest(".ok")) {
        feelPress();
        period = { start, end };
        render(last);
        return shut();
      }
      if (event.target.closest(".reset")) {
        feelSlide();
        ({ start, end } = recent());
        go(end.slice(0, 7), true);
        return paint();
      }
      const cell = event.target.closest("[data-day]:not(:disabled)");
      if (!cell) return;
      feelSlide();
      const day = cell.dataset.day;
      if (end || day < start) [start, end] = [day, null];
      else end = day;
      paint();
    });
    track.addEventListener("scroll", turn, { passive: true });
    paint();
    document.body.append(box);
    go(end.slice(0, 7), false);
  };
  const caret = '<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 6l4.5 4.5L12.5 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const menu = (open) => {
    page.querySelector(".pick")?.classList.toggle("open", open);
    page.querySelector(".pick > button")?.setAttribute("aria-expanded", String(open));
  };
  document.addEventListener("click", (event) => page.querySelector(".pick")?.contains(event.target) || menu(false), { signal: closer.signal });
  const render = (data) => {
    last = data;
    clearTimeout(timer);
    const unit = view.unit, money = (usd) => assetMoney(unit === "USD" ? usd : usd * data.rate, unit);
    const trades = data.trades, request = trades?.request, now = Date.now();
    const asked = request && (request.sectors?.[index]?.order_count || 0) > 0 && now < due(request.run_at) ? request : null;
    const decided = data.decisions?.date === request?.date ? data.decisions.sectors?.[index]?.decision : null;
    const blocks = trades?.sectors?.[index] || [];
    const open = asked && blocks.find((block) => block.date === asked.date && block.source !== "manual");
    const block = (b, live) => {
      const state = live ? ({ approve: "approved", cancel: "rejected" }[decided] || asked.sectors[index].status) : b.state;
      const rows = b.executions?.length
        ? b.executions.map((e) => assetRow(`${e.symbol}${side(e.side)}`, e.quantity != null ? assetShares(e.quantity) : "", e.amount != null ? money(e.amount) : "",
          e.at.slice(11, 16)).replace('"asset-item"', e.filled ? '"asset-item"' : '"asset-item miss"'))
        // 보낼 주문은 원화 금액으로 정하고, 달러 금액은 어림값이다. 고른 단위의 금액을 위 줄에, 다른 통화의 금액을 아래 줄에 쓴다.
        : (b.orders || []).map((o) => assetRow(`${o.symbol}${side(o.side)}`, o.shares != null ? `약 ${assetShares(o.shares)}` : "",
          unit === "USD" && o.usd != null ? `약 $${figure(o.usd)}` : assetMoney(o.krw, "KRW"),
          o.usd == null ? "" : unit === "USD" ? assetMoney(o.krw, "KRW") : `약 $${figure(o.usd)}`));
      const act = live ? `<p class="note">${{ approved: `${clock(asked.run_at)}에 집행한다. 그 전까지 취소할 수 있다.`,
        rejected: `이 지수는 집행하지 않는다. ${clock(asked.run_at)} 전까지 다시 승인할 수 있다.` }[state] || `${clock(asked.run_at)}까지 취소하지 않으면 그대로 집행한다.`}</p>`
        + `<div class="act"><button type="button" data-decision="cancel"${state === "rejected" ? ' class="on" disabled' : ""}>${state === "rejected" ? "취소함" : "취소"}</button>`
        + `<button type="button" data-decision="approve" class="go${state === "approved" ? ' on" disabled' : '"'}>${state === "approved" ? "승인함" : "승인"}</button></div>` : "";
      return `<div class="trade" data-date="${b.date}"><div class="top"><b>${assetDay(b.date)} (${WEEK[new Date(`${b.date}T12:00:00Z`).getUTCDay()]})</b>`
        + (TRADE_SOURCE[b.source] ? `<span class="badge ${b.source}">${TRADE_SOURCE[b.source]}</span>` : "") + "</div>"
        + (b.target != null && b.after != null ? `<div class="lev">목표 배율 갭 ${gap(b.target - b.after)}</div>` : "")
        + (b.reason ? `<p class="why">${assetText(b.reason)}</p>` : "") + (rows.length ? `<div class="rows">${rows.join("")}</div>` : "") + act + "</div>";
    };
    const past = blocks.filter((b) => b !== open && (filter === "all" || b.source === filter) && b.date >= period.start && b.date <= period.end);
    // 기간 투자액은 체결한 행만 센다. 체결하지 못한 주문은 금액이 있어도 돈이 나가지 않았다.
    const invested = past.reduce((sum, b) => sum + (b.executions || []).reduce((inner, e) => inner + (e.filled && e.amount != null ? (e.side === "BUY" ? e.amount : -e.amount) : 0), 0), 0);
    page.innerHTML = (open ? `<h2>집행 요청</h2>${block(open, true)}` : "")
      + `<h2 class="trade-head">거래 내역<div class="tools"><div class="pick"><button type="button" aria-haspopup="listbox" aria-expanded="false">${filters[filter]}${caret}</button>`
      + `<div class="menu" role="listbox">` + Object.entries(filters).map(([name, label]) =>
        `<button type="button" role="option" data-filter="${name}"${name === filter ? ' class="on" aria-selected="true"' : ""}>${label}</button>`).join("") + "</div></div>"
      + `${assetUnits(unit)}</div></h2><div class="asset-sum trade-sum"><b>${assetSign(invested)}${money(invested)}</b>`
      + `<button type="button" class="period" aria-label="조회 기간 바꾸기">${icon}${span(period)}</button></div>`
      + (past.length ? past.map((b) => block(b)).join("") : '<p class="status">거래 내역이 없다.</p>');
    roll(page.querySelector(".trade-sum b"), `${index}-trade-${filter}-${unit}-${period.start}-${period.end}`);
    if (open) timer = setTimeout(() => render(last), due(asked.run_at) - now + 1000);
  };
  page.addEventListener("click", async (event) => {
    if (event.target.closest(".pick > button")) {
      feelPress();
      return menu(!page.querySelector(".pick").classList.contains("open"));
    }
    if (event.target.closest(".trade-sum .period")) {
      feelPress();
      return calendar();
    }
    const pick = event.target.closest(".menu button[data-filter]");
    if (pick) {
      if (pick.dataset.filter === filter) return menu(false);
      feelSlide();
      filter = pick.dataset.filter;
      return render(last);
    }
    // 금액 단위는 내 자산 페이지가 적어 둔 그림 카드 번호를 지우지 않게, 기기에 적힌 값을 다시 읽어 단위만 바꿔 적는다.
    const unit = event.target.closest("[data-unit]");
    if (unit) {
      if (unit.dataset.unit === view.unit) return;
      feelSlide();
      Object.assign(view, assetView(), { unit: unit.dataset.unit });
      assetRemember(view);
      return render(last);
    }
    const button = event.target.closest(".act button:not(:disabled)");
    if (!button) return;
    feelPress();
    const card = button.closest(".trade");
    card.querySelectorAll(".act button").forEach((other) => (other.disabled = true));
    let error = "결정을 적지 못했다. 다시 눌러 달라.";
    try {
      const response = await fetch(`${ASSET_URL}/decide`, { method: "POST", cache: "no-store",
        body: JSON.stringify({ initData: tg.initData, date: card.dataset.date, sector: index, decision: button.dataset.decision }) });
      const answer = await response.json().catch(() => null);
      if (response.ok && answer) return render({ ...last, decisions: answer });
      if (response.status === 403) error = "본인 확인에 실패했다. 미니 앱을 다시 열어 달라.";
      else if (answer?.error) error = `결정을 적지 못했다. ${answer.error}.`;
    } catch {}
    render(last);
    page.querySelector(`.trade[data-date="${card.dataset.date}"] .note`)?.replaceChildren(error);
  });
  return { render, stop: () => { clearTimeout(timer); closer.abort(); shut(); } };
}
