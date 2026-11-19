// @ts-nocheck
import { assetCards, assetMoney, assetRow, assetShares, assetSign, assetSignal, assetText } from "./asset-view";
import { ASSET, ASSET_FLAG, account, assetSaved } from "../shared/account";
import { INDEX_NAME } from "../shared/chrome";
import { tone } from "../shared/format";
import { slider } from "../shared/motion";
import { dial, rewindFrames, rewindOffset } from "../shared/rewind";
import { key, life, report, visit } from "../shared/route";
import { feelPress, feelSlide } from "../shared/telegram";
// 리포트 화면의 페이지(`pages`, 이름은 `names`)를 `place`로 묶고 `name` 페이지를 연다. 본인 계정이면 내 자산 페이지를 맨 앞에 더한다.
// Worker가 계좌 요약을 건네면 기기의 `localStorage`에 표시(`ASSET_FLAG`)를 적는다. 표시가 있는 기기는 리포트 화면을 열자마자 내 자산 페이지를 맨 앞에 두고,
// 열 페이지가 정해지지 않았으면 예측 페이지를 연다. 받은 계좌 요약은 `sessionStorage`에 두어 같은 세션에서 다시 연 리포트 화면은 받은 값부터 그리고,
// 리포트 화면을 열 때와 미니 앱으로 돌아올 때마다 새로 받는다. 본인 계정이 아니거나 Worker가 403을 답하면 표시와 받아 둔 값을 지우고 내 자산 페이지를 뺀다.
export function assets(pages, names, place, name) {
  const store = (area, value) => { try { if (value == null) area.removeItem(ASSET_FLAG); else area.setItem(ASSET_FLAG, value); } catch {} };
  const flagged = (() => { try { return localStorage.getItem(ASSET_FLAG) === "1"; } catch { return false; } })();
  const page = Object.assign(document.createElement("div"), { className: "page" });
  let shown = false;
  // 이미 연 화면(`still`)에 페이지를 넣거나 뺄 때는 보던 페이지와 화면 위치를 그대로 둔다. 내 자산 페이지를 보다가 빼면 첫 페이지를 맨 위부터 연다.
  const show = (on, still) => {
    shown = on;
    const y = scrollY, at = history.state?.page;
    if (on) report.prepend(page); else page.remove();
    place(on ? [page, ...pages] : pages, on ? [ASSET, ...names] : names, still ? (at === ASSET && !on ? null : at) : name || names[0], still);
    if (still && (on || at !== ASSET)) scrollTo(0, y);
  };
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
    if (!data || data.error) {
      if (!data || !page.querySelector(".asset-sum")) page.innerHTML = `<h2>내 투자</h2><p class="status">${data ? "계좌를 불러오지 못했다. 미니 앱을 다시 열면 새로 받는다." : "계좌를 불러오는 중이다."}</p>`;
      return;
    }
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
  fill(assetSaved());
  if (flagged) show(true, false);
  else place(pages, names, name, false);
  const { signal } = life;
  const load = () => account().then((data) => {
    if (signal.aborted) return;
    store(localStorage, data && "1");
    store(sessionStorage, data && JSON.stringify(data));
    if (data) fill(data);
    if (!!data !== shown) show(!!data, true);
  }, () => signal.aborted || fill({ error: true }));
  load();
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && shown) load(); }, { signal });
}
