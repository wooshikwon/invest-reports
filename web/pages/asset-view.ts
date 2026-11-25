// @ts-nocheck
import "./asset-view.css";
import { ASSET_URL } from "../shared/account";
import { gaugeCard, indexInk } from "../shared/card";
import { INDEX_NAME, INDEX_TITLE } from "../shared/chrome";
import { figure, signed, tone } from "../shared/format";
import { slider } from "../shared/motion";
import { roll } from "../shared/roll";
import { SESSION_NAME, closeAt, closedTag, sessionAt, sessionTag, stale } from "../shared/session";
import { keep, kept } from "../shared/keep";
import { key, life, visit } from "../shared/route";
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
// 내 자산 페이지와 거래 내역 화면의 고른 상태. 금액 단위(`unit`), 총 자산 단추를 켰는지(`whole`), 판단 선을 보이는지(`judge`), 수익률 카드를 금액가중으로 그리는지(`money`),
// 수익률 카드의 기준일(`since`, 첫날이면 `null`), 거래 내역의 출처 필터(`filter`)와 조회 기간(`period`, 최근 3개월이면 `null`)을 기기의 `asset-view`에 남긴다(`keep.ts`). 두 화면은 같은 금액 단위를 쓴다.
// 상태를 바꾼 화면은 바꾼 값(`change`)만 넘기고, 남기는 쪽이 기기에 적힌 값을 다시 읽어 그 값만 바꿔 적는다.
export const assetView = () => {
  const saved = kept("asset-view") || {};
  return { unit: saved.unit === "USD" ? "USD" : "KRW", whole: saved.whole === true, judge: saved.judge !== false, money: saved.money === true,
           since: /^\d{4}-\d{2}-\d{2}$/.test(saved.since) ? saved.since : null,
           filter: TRADE_SOURCE[saved.filter] ? saved.filter : "all", period: saved.period?.start && saved.period?.end ? saved.period : null };
};
export const assetRemember = (change) => keep("asset-view", { ...assetView(), ...change });
// 금액 단위 단추. 칸마다 `data-unit`에 통화를 적고, 고른 칸을 밝게 칠한다.
export const assetUnits = (unit) => '<div class="seg">' + [["USD", "$"], ["KRW", "원"]].map(([currency, label]) =>
  `<button type="button" data-unit="${currency}"${currency === unit ? ' class="on"' : ""}>${label}</button>`).join("") + "</div>";
// 집행 신호등. 값(`signal`)은 거래 내역 값의 `signal`이고, 그 지수(`index`)의 값이 없으면 `null`이다. 옵티마이저 게이트와 조건부 게이트 가운데
// 더 묶는 관문(빨강 > 주황 > 초록) 하나의 이름(`name`), 색(`color`), 배치가 쓴 이유(`reason`)를 돌려주고, 두 관문의 색이 같으면 옵티마이저 게이트를 쓴다.
const assetGate = (signal, index) => {
  const sector = signal?.sectors?.[index];
  if (!sector) return null;
  const rank = ["green", "orange", "red"], { optimizer, conditional } = sector;
  const [name, value] = rank.indexOf(conditional.color) > rank.indexOf(optimizer.color) ? ["조건부 게이트", conditional] : ["옵티마이저 게이트", optimizer];
  return { name, color: value.color, reason: value.reason };
};
// 그 지수(`index`)의 가장 늦은 게이트 판정 날에 사용자가 수기 리밸런싱 요청을 승인했는지. 승인한 요청이 그날 게이트 판정을 대신하므로,
// 집행 시각이 지난 뒤에도 다음 판정 전까지 집행 신호등 카드를 두지 않는다.
const overruled = (data, index) => {
  const request = data.trades?.request, forced = `forced-${index}`;
  if (!request || !data.trades.forced?.[index] || request.date !== data.trades.signal?.date) return false;
  const pressed = data.decisions?.date === request.date ? data.decisions.sectors?.[forced]?.decision : null;
  return (pressed ?? (request.sectors?.[forced]?.status === "approved" ? "approve" : null)) === "approve";
};
// 신호등 카드 한 장의 속. 신호등 색(`color`)과 이름(`name`), 한 문단(`text`)을 쓴다.
const gateBody = (color, name, text) => `<div class="gate"><i class="lamp ${color}"></i><div><strong>${name}</strong><p>${assetText(text)}</p></div></div>`;
// 수기 요청의 설명 한 문단. SGOV 매도액과 지수마다 투입 몫의 매수액을 고른 단위(`unit`)로 쓰고, 원 금액을 요약을 만든 시각의 환율(`rate`)로 달러로 바꾼다.
// 알림 카드와 거래 내역 화면의 수기 요청 블록이 같은 문단을 쓴다.
const instructedText = (data, unit) => {
  const money = (krw) => assetMoney(unit === "KRW" ? krw : krw / data.rate, unit), orders = data.trades.instructed.orders;
  const sold = orders.filter((o) => o.symbol === "SGOV" && o.side === "SELL").reduce((sum, o) => sum + o.krw, 0);
  const shares = Object.keys(INDEX_TITLE).map((key) => [key, orders.filter((o) => o.sector === key && o.side === "BUY").reduce((sum, o) => sum + o.krw, 0)])
    .filter(([, krw]) => krw > 0).map(([key, krw]) => `${INDEX_TITLE[key]}에 ${money(krw)}`);
  return `대기자금(SGOV) ${money(sold)}을 팔아 ${shares.join(", ")}을 넣는다.`;
};
// 수기 리밸런싱 요청서의 설명 한 문단. 게이트에 막힌 지수(`index`)를 게이트와 관계없이 목표 배율 쪽으로 옮긴다는 것과 현재·목표 배율을 쓴다.
// 알림 카드와 거래 내역 화면의 요청 블록이 같은 문단을 쓴다.
const forcedText = (data, index) => {
  const { current, target } = data.trades.forced[index];
  const shift = current != null && target != null ? ` 배율을 ${current.toFixed(3)}배에서 목표 ${target.toFixed(3)}배 쪽으로` : "";
  return `게이트와 관계없이 ${INDEX_TITLE[index]}${shift} 옮긴다. 한 번에 옮기는 폭은 1회 이동 천장을 지킨다.`;
};
// 알림 카드 묶음. 내 투자 큰 값 아래에 카드 한 장씩을 옆으로 이어 놓고, 다음 카드가 오른쪽 끝에 조금 보이게 한다. 순서는 주문 요청, 집행 신호등이다.
// 주문 요청 카드는 그날 승인 요청이 집행 시각(`run_at`) 전일 때만 두고, 초록 신호등과 "23:30 리밸런싱 주문 요청"처럼 집행 시각을 앞에 붙인 요청 이름 아래에
// 거래 내역 화면의 그 요청 블록과 같은 설명 문단을 쓴다. 리밸런싱 요청은 블록의 이유(`reason`)를, 수기 요청은 `instructedText`를,
// 사용자가 거래 내역 화면에서 [수기 요청]을 눌러 승인한 수기 리밸런싱 요청은 `forcedText`를 쓴다.
// 집행 신호등 카드는 가장 늦은 날의 게이트 판정(`assetGate`)이 주황이나 빨강일 때만 둔다. 초록이면 주문 요청 카드가 그날 집행을 알리고,
// 그날 그 지수의 수기 리밸런싱 요청을 승인했으면(`overruled`) 집행 시각 전에는 그 요청 카드가 게이트 판정을 대신하고, 집행 시각 뒤에는 다음 판정 전까지 카드를 두지 않는다.
// 카드는 신호등 색과 관계없이 모두 지수색 테두리를 두른다.
// 카드를 누르면 주문 요청 절을 맨 위에 둔 거래 내역 화면을 연다. 오른쪽 위 ✕는 결정을 바꾸지 않고 그 카드만 걷으며, 걷은 카드는 날짜와 함께 기기에 남긴다(`asset-asks`).
const ASKS = "asset-asks";
export const assetAsks = (data, index, unit) => {
  const trades = data.trades, request = trades?.request, cards = [];
  if (request && Date.now() < Date.parse(`${request.run_at}:00+09:00`)) {
    const at = request.run_at.slice(11, 16);
    const block = request.sectors?.[index]?.order_count > 0 && (trades.sectors?.[index] || []).find((b) => b.date === request.date && b.source === "llm");
    if (block) cards.push([request.date, index, "green", `${at} 리밸런싱 주문 요청`, block.reason || ""]);
    if (trades.instructed && request.sectors?.instructed?.order_count > 0) cards.push([request.date, "instructed", "green", `${at} 수기 주문 요청`, instructedText(data, unit)]);
    // 수기 리밸런싱 요청서는 사용자가 [수기 요청]을 눌러 승인한 뒤에만 카드로 둔다.
    if (overruled(data, index)) cards.push([request.date, `forced-${index}`, "green", `${at} 수기 리밸런싱 주문 요청`, forcedText(data, index)]);
  }
  // 수기 리밸런싱 요청을 승인한 지수는 집행 시각 전에는 그 요청 카드가, 집행 시각이 지난 뒤에는 다음 판정 전까지 아무 카드도 게이트 판정을 대신한다.
  const gate = assetGate(trades?.signal, index);
  if (gate && gate.color !== "green" && !overruled(data, index)) cards.push([trades.signal.date, `gate-${index}`, gate.color, gate.name, gate.reason]);
  const hidden = kept(ASKS) || [], shown = cards.filter(([date, key]) => !hidden.includes(`${date}:${key}`));
  if (!shown.length) return "";
  return '<div class="carousel asks"><div class="track">' + shown.map(([date, key, color, name, text]) =>
    `<div class="slide"><div class="signal" role="button" tabindex="0" data-ask="${date}:${key}">`
    + '<button type="button" class="hide" aria-label="이 알림 끄기"><svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">'
    + '<path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg></button>'
    + `${gateBody(color, name, text)}</div></div>`).join("") + "</div></div>";
};
// 걷은 알림 카드(`날짜:카드`)를 기기의 목록에 더한다. 목록은 최근 30장만 남긴다.
const hideAsk = (ask) => keep(ASKS, [...(kept(ASKS) || []), ask].slice(-30));
// 시각 `time`의 기준 시각 글씨. 요약 절의 그림 카드처럼 "정규장, 2026.11.21. 23:43 KST"로 쓰고, 뉴욕 시각으로 세션을 정해 그 세션의 색으로 칠한다.
// 04:00~09:30 ET는 프리마켓, 09:30~16:00 ET는 정규장이고, 그 밖은 애프터마켓이다.
// 선물 시간대의 주간거래 체결가이면(`futures`) 종목 상세 주가 카드처럼 "주간거래, 2026.11.24. 13:05 KST"라고 회색으로 쓴다. 체결가가 멈춘 휴장이면(`stale`) "휴장"과 지금 시각을 쓴다.
const NY_CLOCK = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
// `kindOf(time, futures)`는 그 시각 체결가의 세션(`pre`, `regular`, `after`, `overnight`)이다. `futures`는 그 체결가가 대신한 애프터장의 세션 날짜다.
const kindOf = (time, futures) => {
  if (futures) return "overnight";
  const part = Object.fromEntries(NY_CLOCK.formatToParts(Date.parse(time)).map(({ type, value }) => [type, value])), clock = +part.hour * 60 + +part.minute;
  return clock >= 240 && clock < 570 ? "pre" : clock >= 570 && clock < 960 ? "regular" : "after";
};
const stamp = (time, futures) => {
  const kind = kindOf(time, futures);
  if (stale(time, kind)) return closedTag();
  return sessionTag(kind, sessionAt(SESSION_NAME[kind], time));
};
// 내 자산 페이지의 그림 카드. 값(`perf`)은 계좌 요약의 `performance.sectors.{지수}`이고, 값이 없는 카드는 뺀다. 지수(`index`)는 이름 줄과 큰 값을 굴리는 자리 이름에 쓴다.
// `times`는 최신 날짜 점과 현재 배율을 셈한 체결가의 시각(`live`)과, 그 체결가가 선물 시간대의 주간거래 값이면 그 체결가로 대신한 애프터장의 세션 날짜(`futures`)다.
// 실시간 체결가가 없으면 Worker가 최신 날짜 점을 요약의 가격으로 셈하므로, 그때 `live`는 요약 시각이다. 카드 이름과 상자 목록(`cards`)과 다시 그리는 함수(`show`)를 돌려준다.
// 카드는 요약 절의 그림 카드처럼 맨 위 줄에 값의 기준 시각을, 그 아래 이름 줄 왼쪽에 "나스닥 100"처럼 지수 이름을 쓴다. 이름 줄 오른쪽에는 수익률 카드면 판단 보기·금액가중 체크 단추를
// 그 순서로, 배율 카드면 목표 배율을 흐린 글씨로 둔다. 판단 보기 체크 단추는 두 수익률 카드에서 판단 선(지수색)을 함께 보이거나 감추고,
// 그 상태(`view.judge`)를 기기에 남긴다(`remember`).
// 금액가중 체크 단추는 계좌 요약에 금액가중 누적 수익률과 날짜 점마다의 평가액(`returns.mwr.values`)이 있을 때만 둔다. 켜면 두 수익률 카드의 집행 선과 큰 값을 시간가중 대신 금액가중
// 누적 수익률로 그리고, 그 상태(`view.money`)를 기기에 남긴다. 고정 배율·판단 선은 돈을 처음 규모 그대로 둔 계좌의 값이라 그대로 두므로, 초과 수익률은
// 배율 판단의 효과와 돈을 넣고 뺀 시점의 효과를 함께 보인다.
// 카드 순서는 누적 수익률, 초과 수익률, 배율이다. 누적 수익률 카드는 기준일 대비 고정 배율·판단·집행 누적 수익률을,
// 초과 수익률 카드는 판단과 집행의 누적 수익률에서 고정 배율 누적 수익률을 뺀 값을 날짜 지점 축에 그린다. 큰 값은 집행 선의 값이다.
// 기준일은 첫날이고, 사용자가 고른 기준일(`view.since`)이 있으면 그날(그날이 거래일이 아니면 그 앞 거래일) 종가부터 그린다. 시간가중 선은 첫날 대비 누적값을
// 기준일 값으로 나눠 다시 잇고, 금액가중 집행 선은 날짜 점마다의 집행 계좌 평가액(`mwr.values`, 날짜 점은 `mwr.value`)과 들어온 돈(`mwr.flows`)으로 기준일부터 다시 셈한다.
// 날짜 점이 둘 넘게 남도록 기준일은 마지막 날짜 점 바로 앞까지만 옮긴다.
// 축은 정산한 거래일마다 한 점이고, Worker가 1분마다 다시 셈한 최신 날짜 지점의 값(`returns.now`)이 있으면 그 날짜 점을 하나 더 둔다.
// 정산 전에 정규장이 끝난 세션은 Worker가 그 세션의 공식 종가로 확정한 점(`returns.closed`)을 그 세션 자리에 두고, 최신 날짜 점은 다음 세션 자리에 둔다.
// 그래서 주가 카드처럼 정규장이 끝난 뒤의 애프터마켓·주간거래·프리마켓 값은 다음 세션 자리에 그린다.
// 최신 날짜 점의 고정 배율·판단 값은 기준 배율과 목표 배율을 그대로 들고 있다고 본 값이다. Worker가 판단 값을 셈하지 못하면 판단 선은 마지막 정산일에서 끝난다.
// 최신 날짜 점의 값이 정규장이 아닌 세션(애프터마켓, 주간거래, 프리마켓)의 체결가로 셈한 값이면, 주가 카드처럼 마지막 정산일에서 그 점까지를 점선으로 잇고 그 점의 '현재' 표시를 그 세션 색으로 찍는다.
// 수익률 카드의 기준 시각은 최신 날짜 점이 있으면 체결가 시각, 없으면 마지막 거래일의 정규장 종가 시각이다.
// 배율 카드는 이름 줄 오른쪽에 목표 배율을, 큰 값에 현재 배율을 흰 글씨로 쓴다. 현재 배율(`leverage.current`)은 내 자산 페이지가 Worker가 실시간 체결가로 다시 평가한
// 그 지수 종목의 평가액으로 셈한 값이므로, 기준 시각은 수익률 카드의 최신 날짜 점과 같은 체결가 시각이다. 그림에는 오늘 가격 경로들의 배율 분포(지수색 면)와 이슈가 없을 때의 분포(회색 면)를
// 배율 축에 그리고, 기준 배율에 회색 점선, 목표 배율에 지수색 실선, 현재 배율에 흰 실선을 긋는다. 현재 배율 선과 수익률 카드의 집행 선은 다른 페이지의 가격 선과 같은 흰색(`PRICE`)이다.
// 누적 수익률·초과 수익률 카드는 그림을 누르면 누른 가로 자리에서 가장 가까운 날짜 점으로 '현재' 표시(`nowMark`)를 옮기고, 큰 값을 그 점의 값으로,
// 기준 시각을 그날 정규장 종가 시각으로 바꾼다. 선은 줄이지 않는다. 고른 점이 첫날이면 큰 값에 "기록 없음"을 쓰고, 가장 늦은 점을 누르면 처음 상태로 돌아간다.
// 두 카드는 같은 날짜를 함께 고르고, 고른 날짜(`pin.day`)는 호출하는 쪽이 들고 있어 카드를 다시 만들어도 이어진다. 가장 늦은 점을 고르면 `pin.day`를 비워 새 최신 점을 따른다.
// 배율 카드는 시간 축이 없어 누르기 동작이 없다.
// 시작 평가액 `book[0]`부터 날마다의 금액가중 누적 수익률(Modified Dietz). `flows[k]`는 k번째 날 종가에 들어온 돈이고, 그 돈은 그날 수익에 들지 않는다.
// `exec_figures.py`의 `money_weighted`와 같은 식이다.
const dietz = (book, flows) => {
  let total = 0, timed = 0;
  return book.map((value, k) => {
    total += flows[k];
    timed += k * flows[k];
    const base = k ? book[0] + total - timed / k : book[0];
    return base > 0 ? (value - book[0] - total) / base : 0;
  });
};
export function assetCards(perf, index, times = {}, pin = { day: null }, view = { judge: true, money: false, since: null }, remember = () => {}) {
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
    c.head("", lev.current == null ? "기록 없음" : big(lev.current.toFixed(3), "배"), stamp(times.live, times.futures));
    c.side.textContent = `목표 ${lev.target.toFixed(3)}배`;
    c.value.style.color = lev.current == null ? DIMS : "";
    const xs = Array.from({ length: n }, (_, i) => lev.anchor * (1 + lev.low + (lev.high - lev.low) * i / (n - 1)));
    const X = (v) => Math.min(R, Math.max(L, L + (v - xs[0]) / (xs[n - 1] - xs[0]) * (R - L))), peak = Math.max(...lev.today, ...lev.quiet);
    const Y = (v) => B - v / peak * (B - T);
    const area = (values) => `M${X(xs[0])} ${B}L${values.map((v, i) => `${X(xs[i])} ${Y(v)}`).join("L")}L${X(xs[n - 1])} ${B}Z`;
    s.replaceChildren();
    s.append(shape("path", { d: area(lev.quiet), fill: "rgba(167, 171, 176, .14)" }));
    s.append(shape("path", { d: area(lev.today), fill: color, opacity: .2 }));
    s.append(shape("line", { x1: X(lev.anchor), x2: X(lev.anchor), y1: T, y2: B, stroke: BASE, "stroke-width": 1.2, "stroke-dasharray": "4 3" }));
    s.append(shape("line", { x1: X(lev.target), x2: X(lev.target), y1: T, y2: B, stroke: color, "stroke-width": 1.6 }));
    if (lev.current != null) s.append(shape("line", { x1: X(lev.current), x2: X(lev.current), y1: T, y2: B, stroke: NOW, "stroke-width": 1.6 }));
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
  const lines = (c, series, unit, flat, days, at, tap, late) => {
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
    const path = (values) => `M${values.map((v, i) => `${X(i)} ${Y(v)}`).join("L")}`;
    series.forEach(([values, stroke, dash]) => {
      const cut = late !== "regular" && !dash ? n - 1 : n;
      s.append(shape("path", { d: path(values.slice(0, cut)), fill: "none", stroke, "stroke-width": dash ? 1.2 : 1.8, "stroke-linejoin": "round", ...(dash ? { "stroke-dasharray": "3 3" } : {}) }));
      if (cut < n) s.append(shape("path", { d: `M${X(n - 2)} ${Y(values[n - 2])}L${X(n - 1)} ${Y(values[n - 1])}`, fill: "none", stroke, "stroke-width": 1.4, "stroke-dasharray": "2 2" }));
    });
    [[0, "start"], [Math.floor((n - 1) / 2), "middle"], [n - 1, "end"]].forEach(([i, anchor]) =>
      s.append(shape("text", { x: X(i), y: B + 18, "font-size": 11, fill: DIMS, "text-anchor": anchor }, assetDay(days[i]))));
    nowMark(s, X(at), Y(series.at(-1)[0][at]), at === n - 1 ? late : "regular");
    const spots = days.map((_, i) => X(i));
    onTap(s, (x) => tap(nearest(spots, x)));
  };
  // 고른 날짜 점이 첫날이면 그림은 그리되 큰 값에 "기록 없음"을 쓴다.
  const figureOf = (c, v, unit, at) => {
    c.value.className = v == null ? "" : tone(v);
    c.head("", v == null ? "기록 없음" : big(signed(v * 100, 2), unit), at);
  };
  if (ret?.days?.length > 1) {
    const money = !!ret.mwr?.values, check = '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.6"/><path d="M5.2 8.2l1.9 1.9 3.7-3.9"/></svg>';
    const toggle = (label, flip) => {
      const button = Object.assign(document.createElement("button"), { type: "button", className: "check", innerHTML: `${check}<span>${label}</span>` });
      button.addEventListener("click", () => { feelPress(); flip(); remember(); paint(); });
      return button;
    };
    const cum = card("cum"), over = card("over"), toggles = [cum, over].map((c) => {
      const judge = toggle("판단 보기", () => { view.judge = !view.judge; });
      const weigh = money ? toggle("금액가중", () => { view.money = !view.money; }) : null;
      const checks = Object.assign(document.createElement("span"), { className: "checks" });
      checks.append(...[judge, weigh].filter(Boolean));
      c.side.replaceWith(checks);
      return [judge, weigh];
    });
    const closed = ret.closed && ret.closed.day > ret.days.at(-1) ? ret.closed : null;
    const now = ret.now && ret.now.day > (closed?.day ?? ret.days.at(-1)) ? ret.now : null;
    // 선 값. 금액가중이면 집행 선만 `returns.mwr.realized`와 날짜 점마다의 `mwr.realized`를 쓰고, 금액가중 값이 없는 날짜 점부터는 그리지 않는다.
    // 고정 배율·판단 선의 비교 기준은 돈을 처음 규모 그대로 둔 계좌라, 그 금액가중 수익률은 시간가중 수익률과 같다.
    const pick = (weighed) => {
      const extra = [];
      for (const point of [closed, now].filter(Boolean)) {
        const realized = weighed ? point.mwr?.realized : point.realized;
        if (realized == null) break;
        extra.push([point, realized]);
      }
      const target = [...ret.target];
      for (const [point] of extra) { if (point.target == null) break; target.push(point.target); }
      const days = [...ret.days, ...extra.map(([point]) => point.day)], anchor = [...ret.anchor, ...extra.map(([point]) => point.anchor)];
      const realized = [...(weighed ? ret.mwr.realized : ret.realized), ...extra.map(([, value]) => value)];
      const s = view.since ? Math.min(days.length - 2, Math.max(0, days.filter((day) => day <= view.since).length - 1)) : 0;
      const again = (values) => values.slice(s).map((v) => (1 + v) / (1 + values[s]) - 1);
      const from = (values) => (s ? again(values) : values);
      // 금액가중 집행 선은 기준일 평가액에서 시작해, 기준일 뒤 들어온 돈으로 같은 Modified Dietz 식을 다시 셈한다. 날짜 점 뒤로는 들어온 돈이 없다.
      const book = weighed && s ? [...ret.mwr.values, ...extra.map(([point]) => point.mwr.value)].slice(s) : null;
      const flows = book && [0, ...[...ret.mwr.flows, ...extra.map(() => 0)].slice(s + 1)];
      return { days: days.slice(s), anchor: from(anchor), target: from(target), realized: book ? dietz(book, flows) : from(realized),
               now: extra.at(-1)?.[0] === now ? now : null };
    };
    const paint = () => {
      const { days, anchor, realized, target, now } = pick(money && view.money), gap = (values) => values.map((v, i) => v - anchor[i]);
      const at = pin.day == null ? days.length - 1 : Math.max(0, days.filter((day) => day <= pin.day).length - 1), first = at < 1;
      const when = at < days.length - 1 || !now ? settled(days[at]) : stamp(times.live, times.futures);
      figureOf(cum, first ? null : realized[at], "%", when);
      figureOf(over, first ? null : realized[at] - anchor[at], "%p", when.cloneNode(true));
      const tap = (i) => { feelPress(); pin.day = i === days.length - 1 ? null : days[i]; paint(); };
      toggles.forEach(([judge, weigh]) => [[judge, view.judge], [weigh, view.money]].forEach(([button, on]) => {
        button?.classList.toggle("on", on);
        button?.setAttribute("aria-pressed", on);
      }));
      const judged = (values) => (view.judge ? [[values, color]] : []);
      const late = now ? kindOf(times.live, times.futures) : "regular";
      lines(cum, [[anchor, BASE, true], ...judged(target), [realized, NOW]], "%", false, days, at, tap, late);
      lines(over, [...judged(gap(target)), [gap(realized), NOW]], "%p", true, days, at, tap, late);
    };
    paint();
    cards.push(["누적 수익률", cum.box], ["초과 수익률", over.box]);
  }
  if (lever) cards.push(lever);
  return cards;
}

// 내 자산 페이지(`page`)를 그리는 함수를 돌려준다. 공개 화면 `asset.ts`가 Worker가 건넨 계좌 요약(`data`)마다 이 함수를 부른다.
export function assetPage(page) {
  // 보고 있는 그림 카드(`card`)는 기기에 남기지 않고, 페이지를 1분마다 다시 그리는 동안만 쓴다. 처음 항목으로 돌리는 규칙은 `motion.ts` `homing`이 정한다.
  const view = { ...assetView(), card: 0 }, remember = () => assetRemember({ unit: view.unit, whole: view.whole, judge: view.judge, money: view.money, since: view.since });
  const chevron = '<svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5l4.5 4.5L6 12.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  // 평가 금액의 가림을 벗겼는지(`bare`)는 미니 앱을 닫을 때까지만 기억하고 기기에는 적지 않으므로, 미니 앱을 열 때마다 보이는 채로 시작한다. 평가 금액을 누르면 가리고 다시 누르면 보인다.
  let last = null, bare = true;
  // 첫 절 내 투자는 보고 있는 리포트 지수의 종목(`sector`)만 모아 평가금 합계를 쓰고, 그 아래 회색 글씨로 그 합계가 총 자산에서 차지하는 비중을 "전체 투자 대비 N%"로 쓴다.
  // 총 자산은 두 지수 종목과 그 밖의 종목, 대기자금, 원화·달러 현금을 모두 더한 값이다. 그 아래에는 알림 카드 묶음(주문 요청과 집행 신호등)과 그림 카드를 둔다.
  // 제목 오른쪽 금액 단위 단추 옆의 총 자산 단추를 켜면(`whole`), 합계 자리에 총 자산을 쓰고 비중은 100%다. 값은 계좌 요약을 새로 받을 때(1분마다)마다 다시 쓴다.
  // 둘째 절 상세 보유 종목은 그 종목들의 종목 줄을 쓰고, 그 아래 거래 내역 단추를 둔다.
  // 맨 아래 절 내 계좌는 원화·달러 주문 가능 현금을 그 통화로, 대기자금(SGOV)을 고른 단위로 쓴다. SGOV를 들고 있지 않으면 대기자금 줄을 두지 않는다.
  // 그림 카드에서 고른 날짜는 화면을 닫을 때까지 기억해, 새 계좌 요약을 받아 다시 그려도 그 날짜로 그린다.
  const pin = { day: null };
  const fill = (data) => {
    last = data;
    const index = key.split("-")[1], { rate, accounts } = data, unit = view.unit;
    // 금액은 고른 단위로 바꿔 쓴다. 다른 통화 금액은 요약을 만든 시각의 환율로 바꾼다.
    const into = (v, currency) => (currency === unit ? v : unit === "KRW" ? v * rate : v / rate);
    const change = (v, r) => `<span class="${tone(v)}">${assetSign(v)}${assetMoney(v, unit, true)} (${Math.abs(r * 100).toFixed(1)}%)</span>`;
    const held = data.items.map((item) => ({ ...item, value: into(item.value, item.currency), profit: into(item.profit, item.currency) }));
    const mine = held.filter((item) => item.sector === index), waiting = held.find((item) => item.sector === "sgov");
    const cash = Object.entries(accounts).reduce((sum, [currency, summed]) => sum + into(summed.cash, currency), 0);
    const whole = held.reduce((sum, item) => sum + item.value, 0) + cash, value = view.whole ? whole : mine.reduce((sum, item) => sum + item.value, 0);
    const item = (it, sub) => assetRow(assetText(it.name), sub, assetMoney(it.value, unit), change(it.profit, it.rate));
    const toggle = `<button type="button" class="whole${view.whole ? " on" : ""}" aria-pressed="${view.whole}">총 자산</button>`;
    page.innerHTML = `<h2 class="asset-head">내 투자<span class="tools">${toggle}${assetUnits(unit)}</span></h2><div class="asset-sum${bare ? "" : " veil"}" role="button" tabindex="0"><b class="veiled">평가 금액 보기</b>`
      + `<b>${assetMoney(value, unit)}</b><span class="share">전체 투자 대비 ${+(whole > 0 ? value / whole * 100 : 0).toFixed(1)}%</span></div>${assetAsks(data, index, unit)}`
      + `<h2>상세 보유 종목</h2>`
      + (mine.length ? mine.map((it) => item(it, assetShares(it.quantity))).join("") : `<p class="status">${INDEX_NAME[index]} 종목을 들고 있지 않다.</p>`)
      + `<button type="button" class="asset-trades">거래 내역${chevron}</button><h2>내 계좌</h2>` + assetRow("원화", "주문 가능", assetMoney(accounts.KRW.cash, "KRW")) + assetRow("달러", "주문 가능", assetMoney(accounts.USD.cash, "USD"))
      + (waiting ? item({ ...waiting, name: "대기자금" }, `${waiting.symbol} ${assetShares(waiting.quantity)}`) : "");
    roll(page.querySelector(".asset-sum b:not(.veiled)"), `${view.whole ? "whole" : index}-sum-${unit}`);
    // 배율 카드의 현재 배율은 그 지수 종목의 평가액(Worker가 실시간 체결가로 다시 평가한 값)으로 셈한 섹터 배율(지수 노출 ÷ 평가액 합)이다. 종목마다 지수 대비 배수(`multiple`)는 계좌 요약에 있다.
    const sector = data.items.filter((item) => item.sector === index), capital = sector.reduce((sum, item) => sum + item.value, 0);
    const current = capital > 0 && sector.every((item) => Number.isFinite(item.multiple)) ? sector.reduce((sum, item) => sum + item.value * item.multiple, 0) / capital : null;
    const base = data.performance?.sectors?.[index], perf = base?.leverage ? { ...base, leverage: { ...base.leverage, current } } : base;
    const cards = assetCards(perf, index, { live: data.live?.time || data.time, futures: data.live?.futures }, pin, view, remember);
    const above = page.querySelector(".asks") || page.querySelector(".asset-sum");
    if (!cards.length) return above.insertAdjacentHTML("afterend", '<p class="status">그림 값이 아직 없다.</p>');
    const bar = document.createElement("div");
    bar.className = "tabs";
    cards.forEach(([label], i) => {
      const button = Object.assign(document.createElement("button"), { textContent: label });
      button.addEventListener("click", () => box.go(i));
      bar.appendChild(button);
    });
    // 그림 카드 아래 가운데의 기준일 단추는 수익률 카드의 기준일을 고르는 달력 상자(`dateSheet`)를 띄운다. 첫날부터 마지막 정산일까지의 거래일만 고를 수 있고,
    // 고른 기준일은 기기에 남아 두 지수 화면이 함께 쓰고, 다음에 열어도 이어진다. 최고점·최저점 단추는 기준일을 첫날 뒤 지수(`returns.index`, 기초 ETF 1배 누적 수익률)의
    // 종가가 가장 높은 날과 가장 낮은 날로 옮긴다. 지수 값이 없으면 두 단추를 두지 않는다.
    // 배율 카드를 보는 동안에는 단추를 감추고 그 자리 높이만 남긴다.
    const days = perf?.returns?.days || [], row = Object.assign(document.createElement("div"), { className: "since-row" });
    if (days.length > 1) {
      const base = view.since ? days.filter((day) => day <= view.since).at(-1) || days[0] : days[0];
      const since = Object.assign(document.createElement("button"), { type: "button", className: `since${view.since ? " on" : ""}`, innerHTML: `${CALENDAR}<span>${assetDay(base)}</span>` });
      since.setAttribute("aria-label", "수익률 기준일 바꾸기");
      since.addEventListener("click", () => {
        feelPress();
        const index = perf.returns.index || [], extreme = (better) => {
          const at = index.reduce((best, value, i) => (better(value, index[best]) ? i : best), 0);
          return () => ({ start: days[at], end: days[at] });
        };
        dateSheet({ title: "수익률 기준일", first: days[0], start: base, single: true, can: (day) => days.includes(day),
                    resets: index.length === days.length ? [["최고점", extreme((a, b) => a > b)], ["최저점", extreme((a, b) => a < b)]] : [],
                    done: ({ start }) => { view.since = start === days[0] ? null : start; pin.day = null; remember(); fill(last); } }, life.signal);
      });
      row.append(since);
    }
    const pick = (i) => {
      [...bar.children].forEach((button, j) => button.classList.toggle("on", i === j));
      row.classList.toggle("off", cards[i][0] === "배율");
      view.card = i;
    };
    const box = slider(cards.map(([, card]) => [card]), above, { start: Math.min(view.card, cards.length - 1), change: pick, name: "asset-cards", feel: true, home: 0 });
    box.prepend(bar);
    if (row.children.length) box.append(row);
  };
  page.addEventListener("click", (event) => {
    const unit = event.target.closest("[data-unit]");
    if (unit && unit.dataset.unit !== view.unit) { feelSlide(); view.unit = unit.dataset.unit; remember(); fill(last); }
    if (event.target.closest(".asset-head .whole")) { feelSlide(); view.whole = !view.whole; remember(); fill(last); }
    const hide = event.target.closest(".asks .hide");
    if (hide) { feelPress(); hideAsk(hide.closest("[data-ask]").dataset.ask); return fill(last); }
    if (event.target.closest(".asset-trades, .asks [data-ask]")) { feelPress(); visit(key, { trades: key.split("-")[1] }); }
    const sum = event.target.closest(".asset-sum");
    if (sum) { feelPress(); bare = !bare; sum.classList.toggle("veil", !bare); }
  });
  return fill;
}

// 거래 내역 화면의 주문 요청 절과 거래 내역 절. 주문 요청 절은 맨 위에 그 지수의 집행 신호등 카드를 주황이나 빨강일 때만 두고, 그 아래에 요청 블록을 둔다.
// 주문 요청 절의 카드는 모두 알림 카드와 같은 머리(신호등, 제목, 오른쪽 날짜)와 같은 설명 상자를 쓴다. 블록의 출처(`source`)마다 카드 오른쪽 위 스티커 글씨를 두고, 출처가 없는 옛 블록은 스티커를 두지 않는다.
// 새 출처는 이 표와 서버의 출처 판정(`trades.py`)에만 더한다. 필터는 "전체"와 이 표의 출처 순서다.
export const TRADE_SOURCE = { llm: "LLM 매수", manual: "일반 매수" };
// 거래 내역 절 제목 오른쪽에 출처 필터 드롭다운과 금액 단위 단추를 둔다. 드롭다운은 고른 필터 이름과 아래 꺽쇠를 쓰고, 누르면 그 아래에 필터 목록을 펼친다.
// 목록에서 필터를 고르거나 목록 밖을 누르면 목록을 접는다. 체결 금액은 달러로만 받으므로, 원 단위에서는 계좌 요약을 만든 시각의 환율로 바꿔 쓴다.
// 거래 내역은 조회 기간 안의 블록만 쓰고, 기간 투자액도 그 블록만 더한다. 조회 기간은 처음에 오늘(서울 날짜)까지 최근 3개월이다.
// 달력 아이콘. 거래 내역의 기간 단추와 내 자산 그림 카드의 기준일 단추가 쓴다.
const CALENDAR = '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="3" width="12" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="1.4"/>'
  + '<path d="M2 6.5h12M5.5 1.8v2.6M10.5 1.8v2.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>';
const WEEK = "일월화수목금토";
const CARET = '<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 6l4.5 4.5L12.5 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
// 날짜를 고르는 달력 상자. 날짜(`first`)의 달부터 이번 달(서울 날짜)까지를 한 달씩 옆으로 놓고, 고른 끝 날짜(없으면 시작 날짜)의 달을 보이며 연다.
// 달은 좌우로 밀거나 달 이름 양옆의 꺽쇠를 눌러 넘기고, 날짜 판의 높이는 보이는 달의 줄 수에 맞춘다. 오늘 뒤의 날짜와 `can`이 거짓인 날짜는 누르지 못한다.
// `single`이면 날짜 하나를 고르고, 아니면 기간을 고른다. 기간은 날짜를 처음 누르면 시작 날짜로 두고, 다음에 누른 날짜가 시작 날짜와 같거나 뒤면 끝 날짜로 둔다.
// 시작 날짜보다 앞을 누르면 시작 날짜를 다시 고른다. 제목(`title`) 옆의 되돌리기 단추(`resets`: [이름, 되돌릴 {start, end}] 목록)는 고른 값을 그 값으로 바꾸고,
// `hint`를 주면 제목 아래 줄에 고른 값의 글씨를 쓴다. 고른 값은 아래 확인 단추를 눌러야 `done({start, end})`로 넘어가고, 닫기 단추나 상자 밖을 누르거나 `signal`이 끊기면 버린다.
function dateSheet({ title, first, start, end = null, single = false, can = () => true, hint = null, resets, done }, signal) {
  const today = new Date(Date.now() + 9 * 36e5).toISOString().slice(0, 10);
  if (single) end = start;
  const months = [], names = [];
  for (let y = +first.slice(0, 4), m = +first.slice(5, 7); `${y}-${String(m).padStart(2, "0")}` <= today.slice(0, 7); m === 12 ? (y++, m = 1) : m++) {
    const lead = new Date(Date.UTC(y, m - 1, 1)).getUTCDay(), days = new Date(Date.UTC(y, m, 0)).getUTCDate();
    names.push(`${y}년 ${m}월`);
    months.push(`<section data-month="${y}-${String(m).padStart(2, "0")}"><div class="grid">${"<i></i>".repeat(lead)}` + Array.from({ length: days }, (_, i) => {
      const day = `${y}-${String(m).padStart(2, "0")}-${String(i + 1).padStart(2, "0")}`;
      return `<button type="button" data-day="${day}"${day > today || !can(day) ? " disabled" : ""}${day === today ? ' class="today"' : ""}><span>${i + 1}</span></button>`;
    }).join("") + "</div></section>");
  }
  const box = document.createElement("div"), shut = () => box.remove();
  signal.addEventListener("abort", shut, { once: true });
  box.className = "help-card period-card";
  box.innerHTML = `<div class="card"><h3>${title}<span>${resets.map(([name], i) => `<button type="button" class="reset" data-reset="${i}">${name}</button>`).join("")}<button type="button" class="close" aria-label="닫기">✕</button></span></h3>`
    + `${hint ? '<p class="hint"></p>' : ""}<div class="month"><button type="button" class="prev" aria-label="앞 달">${CARET}</button><h4></h4><button type="button" class="next" aria-label="다음 달">${CARET}</button></div>`
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
    if (hint) box.querySelector(".hint").textContent = hint({ start, end });
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
      done({ start, end });
      return shut();
    }
    const reset = event.target.closest(".reset");
    if (reset) {
      feelSlide();
      ({ start, end } = resets[+reset.dataset.reset][1]());
      go((end || start).slice(0, 7), true);
      return paint();
    }
    const cell = event.target.closest("[data-day]:not(:disabled)");
    if (!cell) return;
    feelSlide();
    const day = cell.dataset.day;
    if (single) start = end = day;
    else if (end || day < start) [start, end] = [day, null];
    else end = day;
    paint();
  });
  track.addEventListener("scroll", turn, { passive: true });
  paint();
  document.body.append(box);
  go((end || start).slice(0, 7), false);
}

// 기간 투자액 아래 줄 오른쪽 끝의 기간 단추를 누르면 조회 기간을 고르는 달력 상자(`dateSheet`)를 띄운다. 최근 3개월 단추는 고른 기간을 최근 3개월로 바꾼다.
export function tradesView(page, index) {
  const clock = (runAt) => runAt.slice(11, 16), due = (runAt) => Date.parse(`${runAt}:00+09:00`);
  const side = (value) => (value === "BUY" ? '<span class="side up">매수</span>' : '<span class="side down">매도</span>');
  const view = assetView(), filters = { all: "전체", ...TRADE_SOURCE }, closer = new AbortController();
  const today = new Date(Date.now() + 9 * 36e5).toISOString().slice(0, 10), recent = () => {
    const [y, m, d] = today.split("-").map(Number), end = new Date(Date.UTC(y, m - 3, 0)).getUTCDate();
    return { start: new Date(Date.UTC(y, m - 4, Math.min(d, end))).toISOString().slice(0, 10), end: today };
  };
  let last = null, timer = null, filter = view.filter, period = view.period || recent();
  // 최근 3개월과 같은 조회 기간은 `null`로 적어 다음에 열 때 그날의 최근 3개월을 쓴다.
  const rememberTrades = () => {
    const fresh = recent();
    assetRemember({ filter, period: period.start === fresh.start && period.end === fresh.end ? null : period });
  };
  const gap = (v) => `${assetSign(v)}${Math.abs(v).toFixed(3)}배`;
  const span = ({ start, end }) => `${start.slice(0, 4) === end.slice(0, 4) ? "" : `${start.slice(2, 4)}.`}${assetDay(start)} ~ ${assetDay(end)}`;
  // 달력은 가장 오래된 거래가 있는 달, 조회 시작 달, 최근 3개월의 시작 달 가운데 가장 이른 달부터 연다.
  const calendar = () => {
    const blocks = last?.trades?.sectors?.[index] || [];
    dateSheet({ title: "조회 기간", first: [period.start, recent().start, ...blocks.map((b) => b.date)].sort()[0], start: period.start, end: period.end,
                hint: ({ start, end }) => (end ? span({ start, end }) : "끝 날짜를 눌러요"), resets: [["최근 3개월", recent]],
                done: (picked) => { period = picked; rememberTrades(); render(last); } }, closer.signal);
  };
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
    const asking = (key) => request && (request.sectors?.[key]?.order_count || 0) > 0 && now < due(request.run_at);
    const forcedKey = `forced-${index}`;
    const asked = asking(index) || asking("instructed") || asking(forcedKey) ? request : null;
    const decided = (key) => (data.decisions?.date === request?.date ? data.decisions.sectors?.[key]?.decision : null);
    const stateOf = (key) => ({ approve: "approved", cancel: "rejected" }[decided(key)] || asked.sectors[key].status);
    const blocks = trades?.sectors?.[index] || [];
    const open = asking(index) && blocks.find((block) => block.date === asked.date && block.source !== "manual");
    // 사용자가 SGOV 투입을 지시한 날의 수기 요청 블록. 두 지수의 화면에 같은 블록을 두고, 결정은 지수의 리밸런싱과 따로 받는다.
    const instructed = asking("instructed") && trades.instructed ? { date: asked.date, source: "instructed", orders: trades.instructed.orders,
      reason: instructedText(data, unit) } : null;
    // 게이트에 막힌 지수의 수기 리밸런싱 요청서. 아침 배치가 미리 산출해 두고, 사용자가 [수기 요청]을 눌러 승인하면 요청 블록으로 연다.
    const offer = asking(forcedKey) && trades.forced?.[index], pressed = offer && stateOf(forcedKey) === "approved";
    const forced = pressed ? { date: asked.date, source: "forced", orders: trades.forced[index].orders, reason: forcedText(data, index) } : null;
    const day = (date) => `${assetDay(date)} (${WEEK[new Date(`${date}T12:00:00Z`).getUTCDay()]})`;
    const head = (date, color, name) => `<div class="top ask"><span><i class="lamp ${color}"></i><b>${name}</b></span><span class="day">${day(date)}</span></div>`;
    // 주문 요청 절 맨 위의 집행 신호등 카드. 신호등이 주황이나 빨강일 때만 두고, 요청 블록과 같은 머리와 설명 상자를 쓴다. 초록이면 요청 블록이 그날 집행을 알린다.
    // 그 지수의 수기 리밸런싱 요청서가 있고 아직 누르지 않았으면 카드 아래에 [수기 요청] 단추를 둔다. 누르면 그 요청을 승인으로 적고 이 카드 대신 요청 블록을 연다.
    // 요청 블록에서 취소하면 이 카드와 단추가 다시 선다. 승인한 요청을 집행 시각에 보낸 뒤에는 다음 판정 전까지 이 카드를 두지 않는다.
    const gateCard = () => {
      const gate = assetGate(trades?.signal, index);
      if (!gate || gate.color === "green" || pressed || overruled(data, index)) return "";
      const ask = offer && !pressed ? '<p class="note">게이트와 관계없이 목표 배율로 옮기는 요청서를 연다. 누르기 전에는 집행하지 않는다.</p>'
        + '<div class="act one"><button type="button" data-decision="approve">수기 요청</button></div>' : "";
      return `<div class="trade gate"${ask ? ` data-date="${asked.date}" data-sector="${forcedKey}"` : ""}>${head(trades.signal.date, gate.color, gate.name)}`
        + `<p class="why">${assetText(gate.reason)}</p>${ask}</div>`;
    };
    const block = (b, live) => {
      const key = { instructed: "instructed", forced: forcedKey }[b.source] ?? index;
      const state = live ? stateOf(key) : b.state;
      const rows = b.executions?.length
        ? b.executions.map((e) => assetRow(`${e.symbol}${side(e.side)}`, e.quantity != null ? assetShares(e.quantity) : "", e.amount != null ? money(e.amount) : "",
          e.at.slice(11, 16)).replace('"asset-item"', e.filled ? '"asset-item"' : '"asset-item miss"'))
        // 보낼 주문은 원화 금액으로 정하고, 달러 금액은 어림값이다. 고른 단위의 금액을 위 줄에, 다른 통화의 금액을 아래 줄에 쓴다.
        : (b.orders || []).map((o) => assetRow(`${o.symbol}${side(o.side)}`, o.shares != null ? `약 ${assetShares(o.shares)}` : "",
          unit === "USD" && o.usd != null ? `약 $${figure(o.usd)}` : assetMoney(o.krw, "KRW"),
          o.usd == null ? "" : unit === "USD" ? assetMoney(o.krw, "KRW") : `약 $${figure(o.usd)}`));
      const act = live ? `<p class="note">${{ approved: `${clock(asked.run_at)}에 집행한다. 그 전까지 취소할 수 있다.`,
        rejected: `${key === "instructed" ? "이 수기 요청은" : "이 지수는"} 집행하지 않는다. ${clock(asked.run_at)} 전까지 다시 승인할 수 있다.` }[state]
          || `${clock(asked.run_at)}까지 취소하지 않으면 그대로 집행한다.`}</p>`
        + `<div class="act"><button type="button" data-decision="cancel"${state === "rejected" ? ' class="on" disabled' : ""}>${state === "rejected" ? "취소함" : "취소"}</button>`
        + `<button type="button" data-decision="approve"${state === "approved" ? ' class="on" disabled' : ""}>${state === "approved" ? "승인함" : "승인"}</button></div>` : "";
      // 주문 요청 절의 블록은 알림 카드와 같은 머리(신호등과 "23:30 리밸런싱 주문 요청" 같은 제목, 오른쪽 날짜)를 쓰고, 지난 블록은 날짜와 출처 스티커를 쓴다.
      const top = live ? head(b.date, "green", `${clock(asked.run_at)} ${{ instructed: "수기", forced: "수기 리밸런싱" }[b.source] ?? "리밸런싱"} 주문 요청`)
        : `<div class="top"><b>${day(b.date)}</b>` + (TRADE_SOURCE[b.source] ? `<span class="badge ${b.source}">${TRADE_SOURCE[b.source]}</span>` : "") + "</div>";
      return `<div class="trade" data-date="${b.date}" data-sector="${key}">${top}`
        + (b.target != null && b.after != null ? `<div class="lev">목표 배율 갭 ${gap(b.target - b.after)}</div>` : "")
        + (b.reason ? `<p class="why">${assetText(b.reason)}</p>` : "") + (rows.length ? `<div class="rows">${rows.join("")}</div>` : "") + act + "</div>";
    };
    const past = blocks.filter((b) => b !== open && (filter === "all" || b.source === filter) && b.date >= period.start && b.date <= period.end);
    // 기간 투자액은 체결한 행만 센다. 체결하지 못한 주문은 금액이 있어도 돈이 나가지 않았다.
    const invested = past.reduce((sum, b) => sum + (b.executions || []).reduce((inner, e) => inner + (e.filled && e.amount != null ? (e.side === "BUY" ? e.amount : -e.amount) : 0), 0), 0);
    const gate = gateCard();
    page.innerHTML = (gate || open || forced || instructed
      ? `<h2>주문 요청</h2>${gate}${open ? block(open, true) : ""}${forced ? block(forced, true) : ""}${instructed ? block(instructed, true) : ""}` : "")
      + `<h2 class="trade-head">거래 내역<div class="tools"><div class="pick"><button type="button" aria-haspopup="listbox" aria-expanded="false">${filters[filter]}${CARET}</button>`
      + `<div class="menu" role="listbox">` + Object.entries(filters).map(([name, label]) =>
        `<button type="button" role="option" data-filter="${name}"${name === filter ? ' class="on" aria-selected="true"' : ""}>${label}</button>`).join("") + "</div></div>"
      + `${assetUnits(unit)}</div></h2><div class="asset-sum trade-sum"><b>${assetSign(invested)}${money(invested)}</b>`
      + `<button type="button" class="period" aria-label="조회 기간 바꾸기">${CALENDAR}${span(period)}</button></div>`
      + (past.length ? past.map((b) => block(b)).join("") : '<p class="status">거래 내역이 없다.</p>');
    roll(page.querySelector(".trade-sum b"), `${index}-trade-${filter}-${unit}-${period.start}-${period.end}`);
    if (open || offer || instructed) timer = setTimeout(() => render(last), due(asked.run_at) - now + 1000);
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
      rememberTrades();
      return render(last);
    }
    const unit = event.target.closest("[data-unit]");
    if (unit) {
      if (unit.dataset.unit === view.unit) return;
      feelSlide();
      view.unit = unit.dataset.unit;
      assetRemember({ unit: view.unit });
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
        body: JSON.stringify({ initData: tg.initData, date: card.dataset.date, sector: card.dataset.sector, decision: button.dataset.decision }) });
      const answer = await response.json().catch(() => null);
      if (response.ok && answer) return render({ ...last, decisions: answer });
      if (response.status === 403) error = "본인 확인에 실패했다. 미니 앱을 다시 열어 달라.";
      else if (answer?.error) error = `결정을 적지 못했다. ${answer.error}.`;
    } catch {}
    render(last);
    page.querySelector(`.trade[data-date="${card.dataset.date}"][data-sector="${card.dataset.sector}"] .note`)?.replaceChildren(error);
  });
  return { render, stop: () => { clearTimeout(timer); closer.abort(); } };
}
