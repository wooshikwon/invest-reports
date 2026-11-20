// @ts-nocheck
import "./asset-view.css";
import { ASSET_URL } from "../shared/account";
import { gaugeCard, indexInk } from "../shared/card";
import { INDEX_NAME } from "../shared/chrome";
import { figure, signed, tone } from "../shared/format";
import { slider } from "../shared/motion";
import { dial, rewindFrames, rewindOffset } from "../shared/rewind";
import { key, visit } from "../shared/route";
import { DIMS, nowMark, shape } from "../shared/svg";
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
// 카드 순서는 누적 수익률, 초과 수익률, 배율이다. 누적 수익률 카드는 첫날 대비 고정 배율·판단·집행 누적 수익률을,
// 초과 수익률 카드는 판단과 집행의 누적 수익률에서 고정 배율 누적 수익률을 뺀 값을 날짜 지점 축에 그린다. 큰 값은 집행 선의 값이다.
// 축은 정산한 거래일마다 한 점이고, Worker가 1분마다 다시 셈한 최신 날짜 지점의 값(`returns.now`)이 있으면 그 날짜 점을 하나 더 둔다.
// 최신 날짜 점은 고정 배율과 집행 선에만 있고 판단 선은 마지막 정산일에서 끝난다.
// 배율 카드는 위 줄에 목표 배율을, 큰 값에 현재 배율을 현재 배율 선과 같은 주황 글씨로 쓴다. 그림에는 오늘 가격 경로들의 배율 분포(지수색 면)와 이슈가 없을 때의 분포(회색 면)를 배율 축에 그리고,
// 목표 배율에 지수색 실선, 현재 배율에 주황 점선을 긋는다.
// `show(past)`는 `past`가 없으면 받은 값으로 그린다. 지난 날짜면 수익률 카드는 선을 줄이지 않고 그날 기준 가격 날짜(`past.base_date`) 점에 '현재' 표시(`nowMark`)를 찍어
// 큰 값을 그 점의 값으로 쓴다. 그 점이 첫날이면 큰 값에 "기록 없음"을 쓴다. 배율 카드는 그날 판단의 배율 분포(`past.chart`)에 그날 현재·목표 배율(`past.current`, `past.target`)을 긋고,
// 그날 현재 배율을 모르면 현재 배율 선을 긋지 않고 큰 값에 "기록 없음"을 쓴다.
export function assetCards(perf) {
  const W = 320, H = 236, B = 212, L = 6, R = W - 6, T = 22, color = indexInk(W), NOW = "#FF9F1C", BASE = "#A7ABB0";
  const big = (text, unit) => [text, Object.assign(document.createElement("small"), { textContent: unit })];
  const cards = [], draws = [];
  const lev = perf?.leverage;
  let lever = null;
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
    lever = ["배율", c.box];
  }
  const ret = perf?.returns;
  // 선 그림은 값 범위를 1·2·5 단위 눈금 네댓 칸으로 나눠 오른쪽 끝에 눈금 값을 쓰고, 그림 아래에 첫날·가운데·마지막 거래일을 쓴다.
  // 고정 배율 선이 0인 초과 수익률 그림은 0 눈금을 회색 점선으로 긋는다.
  const lines = (c, series, unit, flat, days, at) => {
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
    if (at != null) nowMark(s, X(at), Y(series.at(-1)[0][at]), "regular");
  };
  // 고른 날짜 점이 첫날이면 그림은 그리되 큰 값에 "기록 없음"을 쓴다.
  const figureOf = (c, v, unit) => {
    if (v == null) { c.head("", "기록 없음"); c.value.className = ""; return; }
    c.head("", big(signed(v * 100, 2), unit)); c.value.className = tone(v);
  };
  if (ret?.days?.length > 1) {
    const cum = gaugeCard(`첫날 ${assetDay(ret.days[0])} 대비 집행 누적 수익률`, W, H), over = gaugeCard("고정 배율 대비 집행 초과 수익률", W, H);
    const now = ret.now && ret.now.day > ret.days.at(-1) ? ret.now : null;
    const days = now ? [...ret.days, now.day] : ret.days;
    const anchor = now ? [...ret.anchor, now.anchor] : ret.anchor, realized = now ? [...ret.realized, now.realized] : ret.realized, target = ret.target;
    const gap = (values) => values.map((v, i) => v - anchor[i]);
    draws.push((past) => {
      const at = past ? days.filter((day) => day <= past.base_date).length - 1 : days.length - 1, first = at < 1;
      figureOf(cum, first ? null : realized[at], "%");
      figureOf(over, first ? null : realized[at] - anchor[at], "%p");
      const mark = past ? at : null;
      lines(cum, [[anchor, BASE, true], [target, color], [realized, NOW]], "%", false, days, mark ?? days.length - 1);
      lines(over, [[gap(target), color], [gap(realized), NOW]], "%p", true, days, mark ?? days.length - 1);
    });
    cards.push(["누적 수익률", cum.box], ["초과 수익률", over.box]);
  }
  if (lever) cards.push(lever);
  const show = (past) => draws.forEach((draw) => draw(past));
  show(null);
  return { cards, show };
}

// 내 자산 페이지(`page`)를 그리는 함수를 돌려준다. 공개 화면 `asset.ts`가 Worker가 건넨 계좌 요약(`data`)마다 이 함수를 부른다.
export function assetPage(page) {
  // 금액 단위와 보던 그림 카드는 기기에 적어 두고 다음에 열 때도 그대로 쓴다.
  const view = { unit: "KRW", card: 0 };
  try { const kept = JSON.parse(localStorage.getItem("asset-view")); view.unit = kept.unit === "USD" ? "USD" : "KRW"; view.card = kept.card | 0; } catch {}
  const remember = () => { try { localStorage.setItem("asset-view", JSON.stringify(view)); } catch {} };
  const chevron = '<svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5l4.5 4.5L6 12.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  // 평가 금액의 가림을 벗겼는지(`bare`)는 미니 앱을 닫을 때까지만 기억하고 기기에는 적지 않으므로, 미니 앱을 열 때마다 가려진 채로 시작한다.
  let last = null, bare = false, chosen = null;
  // 첫 절 내 투자는 보고 있는 리포트 지수의 종목(`sector`)만 모아 평가금 합계와 수익·수익률을 쓰고, 그 아래 그림 카드와 집행 신호등 카드를 둔다.
  // 둘째 절 상세 보유 종목은 그 종목들의 종목 줄을 쓰고, 그 아래 거래 내역 단추를 둔다.
  // 맨 아래 절 내 계좌는 원화·달러 주문 가능 현금을 그 통화로, 대기자금(SGOV)을 고른 단위로 쓴다. SGOV를 들고 있지 않으면 대기자금 줄을 두지 않는다.
  const fill = (data) => {
    last = data;
    const index = key.split("-")[1], { rate, accounts } = data, unit = view.unit;
    // 금액은 고른 단위로 바꿔 쓴다. 다른 통화 금액은 요약을 만든 시각의 환율로 바꾼다.
    const into = (v, currency) => (currency === unit ? v : unit === "KRW" ? v * rate : v / rate);
    const change = (v, r, bare) => `<span class="${tone(v)}">${assetSign(v)}${assetMoney(v, unit, bare)} (${Math.abs(r * 100).toFixed(1)}%)</span>`;
    const held = data.items.map((item) => ({ ...item, value: into(item.value, item.currency), profit: into(item.profit, item.currency), purchase: into(item.purchase, item.currency) }));
    const mine = held.filter((item) => item.sector === index), waiting = held.find((item) => item.sector === "sgov");
    const total = (field) => mine.reduce((sum, item) => sum + item[field], 0), profit = total("profit"), purchase = total("purchase");
    const item = (it, sub) => assetRow(assetText(it.name), sub, assetMoney(it.value, unit), change(it.profit, it.rate, true));
    page.innerHTML = `<h2 class="asset-head">내 투자<div class="seg">`
      + [["USD", "$"], ["KRW", "원"]].map(([currency, label]) => `<button type="button" data-unit="${currency}"${currency === unit ? ' class="on"' : ""}>${label}</button>`).join("")
      + `</div></h2><div class="asset-sum${bare ? "" : " veil"}" role="button" tabindex="0"><b class="veiled">평가 금액 보기</b>`
      + `<b>${assetMoney(total("value"), unit)}</b>${change(profit, purchase ? profit / purchase : 0)}</div>`
      + `${assetSignal(data.trades?.signal, index)}<h2>상세 보유 종목</h2>`
      + (mine.length ? mine.map((it) => item(it, assetShares(it.quantity))).join("") : `<p class="status">${INDEX_NAME[index]} 종목을 들고 있지 않다.</p>`)
      + `<button type="button" class="asset-trades">거래 내역${chevron}</button><h2>내 계좌</h2>` + assetRow("원화", "주문 가능", assetMoney(accounts.KRW.cash, "KRW")) + assetRow("달러", "주문 가능", assetMoney(accounts.USD.cash, "USD"))
      + (waiting ? item({ ...waiting, name: "대기자금" }, `${waiting.symbol} ${assetShares(waiting.quantity)}`) : "");
    const perf = data.performance?.sectors?.[index], { cards, show } = assetCards(perf);
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
    // 그림 카드 묶음 아래에 리포트 그림 카드와 같은 기준 날짜 슬라이더를 둔다. 고를 수 있는 날짜는 되감기 자료의 판단 날짜 가운데
    // 기준 가격 날짜가 집행 성과의 마지막 거래일을 넘지 않는 날이고, 마지막 날짜는 받은 값 그대로 그린다.
    // 지난 날짜의 현재·목표 배율은 거래 내역의 그날 블록에서 읽고, 블록이 없으면 목표 배율을 그날 판단의 평균 배율로 쓴다.
    // 고른 날짜는 화면을 닫을 때까지 기억해, 금액 단위를 바꾸거나 새 계좌 요약을 받아 다시 그려도 그 날짜로 그린다.
    const blocks = data.trades?.sectors?.[index] || [], end = perf?.returns?.days?.at(-1);
    rewindFrames(index).then((all) => {
      if (!all || !box.isConnected) return;
      const frames = all.filter((frame) => frame.chart && (!end || frame.base_date <= end)), latest = frames.at(-1)?.day;
      const days = frames.filter((frame) => rewindOffset(frame.day, latest) >= 0).map((frame) => frame.day);
      if (days.length < 2) return;
      const past = (day) => {
        if (day === latest) return null;
        const frame = frames.find((f) => f.day === day), block = blocks.find((b) => b.date === day);
        return { chart: frame.chart, base_date: frame.base_date, current: block?.current ?? null, target: block?.target ?? null };
      };
      const at = days.indexOf(chosen);
      let frame = 0;
      dial(box, latest, days, at < 0 ? days.length - 1 : at, (i) => {
        chosen = days[i];
        if (!frame) frame = requestAnimationFrame(() => { frame = 0; show(past(chosen)); });
      });
    });
  };
  page.addEventListener("click", (event) => {
    const unit = event.target.closest("[data-unit]");
    if (unit && unit.dataset.unit !== view.unit) { feelSlide(); view.unit = unit.dataset.unit; remember(); fill(last); }
    if (event.target.closest(".asset-trades, .signal.go")) { feelPress(); visit(key, { trades: key.split("-")[1] }); }
    const sum = event.target.closest(".asset-sum");
    if (sum) { feelPress(); bare = !bare; sum.classList.toggle("veil", !bare); }
  });
  return fill;
}

// 거래 내역 화면의 집행 요청 절과 거래 내역 절. 블록의 출처(`source`)마다 카드 오른쪽 위 스티커 글씨를 두고, 출처가 없는 옛 블록은 스티커를 두지 않는다.
// 새 출처는 이 표와 서버의 출처 판정(`trades.py`)에만 더한다. 필터는 "전체"와 이 표의 출처 순서다.
export const TRADE_SOURCE = { llm: "LLM 매수", manual: "일반 매수" };
export function tradesView(page, index) {
  const WEEK = "일월화수목금토", clock = (runAt) => runAt.slice(11, 16), due = (runAt) => Date.parse(`${runAt}:00+09:00`);
  const side = (value) => (value === "BUY" ? '<span class="side up">매수</span>' : '<span class="side down">매도</span>');
  let last = null, timer = null, filter = "all";
  const gap = (v) => `${assetSign(v)}${Math.abs(v).toFixed(3)}배`;
  const render = (data) => {
    last = data;
    clearTimeout(timer);
    const trades = data.trades, request = trades?.request, now = Date.now();
    const asked = request && (request.sectors?.[index]?.order_count || 0) > 0 && now < due(request.run_at) ? request : null;
    const decided = data.decisions?.date === request?.date ? data.decisions.sectors?.[index]?.decision : null;
    const blocks = trades?.sectors?.[index] || [];
    const open = asked && blocks.find((block) => block.date === asked.date && block.source !== "manual");
    const block = (b, live) => {
      const state = live ? ({ approve: "approved", cancel: "rejected" }[decided] || asked.sectors[index].status) : b.state;
      const rows = b.executions?.length
        ? b.executions.map((e) => assetRow(`${e.symbol}${side(e.side)}`, e.quantity != null ? assetShares(e.quantity) : "", e.amount != null ? `$${figure(e.amount)}` : "",
          e.at.slice(11, 16)).replace('"asset-item"', e.filled ? '"asset-item"' : '"asset-item miss"'))
        : (b.orders || []).map((o) => assetRow(`${o.symbol}${side(o.side)}`, o.shares != null ? `약 ${assetShares(o.shares)}` : "", assetMoney(o.krw, "KRW"),
          o.usd != null ? `약 $${figure(o.usd)}` : ""));
      const act = live ? `<p class="note">${{ approved: `${clock(asked.run_at)}에 집행한다. 그 전까지 취소할 수 있다.`,
        rejected: `이 지수는 집행하지 않는다. ${clock(asked.run_at)} 전까지 다시 승인할 수 있다.` }[state] || `${clock(asked.run_at)}까지 취소하지 않으면 그대로 집행한다.`}</p>`
        + `<div class="act"><button type="button" data-decision="cancel"${state === "rejected" ? ' class="on" disabled' : ""}>${state === "rejected" ? "취소함" : "취소"}</button>`
        + `<button type="button" data-decision="approve" class="go${state === "approved" ? ' on" disabled' : '"'}>${state === "approved" ? "승인함" : "승인"}</button></div>` : "";
      return `<div class="trade" data-date="${b.date}"><div class="top"><b>${assetDay(b.date)} (${WEEK[new Date(`${b.date}T12:00:00Z`).getUTCDay()]})</b>`
        + (TRADE_SOURCE[b.source] ? `<span class="badge ${b.source}">${TRADE_SOURCE[b.source]}</span>` : "") + "</div>"
        + (b.target != null && b.after != null ? `<div class="lev">목표 배율 갭 ${gap(b.target - b.after)}</div>` : "")
        + (b.reason ? `<p class="why">${assetText(b.reason)}</p>` : "") + (rows.length ? `<div class="rows">${rows.join("")}</div>` : "") + act + "</div>";
    };
    const past = blocks.filter((b) => b !== open && (filter === "all" || b.source === filter));
    // 기간 투자액은 체결한 행만 센다. 체결하지 못한 주문은 금액이 있어도 돈이 나가지 않았다.
    const invested = past.reduce((sum, b) => sum + (b.executions || []).reduce((inner, e) => inner + (e.filled && e.amount != null ? (e.side === "BUY" ? e.amount : -e.amount) : 0), 0), 0);
    page.innerHTML = (open ? `<h2>집행 요청</h2>${block(open, true)}` : "")
      + `<h2 class="trade-head">거래 내역<div class="seg">`
      + [["all", "전체"], ...Object.entries(TRADE_SOURCE)].map(([name, label]) => `<button type="button" data-filter="${name}"${name === filter ? ' class="on"' : ""}>${label}</button>`).join("")
      + `</div></h2><div class="asset-sum trade-sum"><b>${assetSign(invested)}${assetMoney(invested, "USD")}</b>기간 투자액</div>`
      + (past.length ? past.map((b) => block(b)).join("") : '<p class="status">거래 내역이 없다.</p>');
    if (open) timer = setTimeout(() => render(last), due(asked.run_at) - now + 1000);
  };
  page.addEventListener("click", async (event) => {
    const pick = event.target.closest(".seg button[data-filter]");
    if (pick) {
      if (pick.dataset.filter === filter) return;
      feelSlide();
      filter = pick.dataset.filter;
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
  return { render, stop: () => clearTimeout(timer) };
}
