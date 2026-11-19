// @ts-nocheck
import { assetDay, assetMoney, assetRow, assetShares, assetText } from "./asset-view";
import { ASSET_FLAG, ASSET_URL, account, assetSaved } from "../shared/account";
import { INDEX_NAME } from "../shared/chrome";
import { figure } from "../shared/format";
import { report } from "../shared/route";
import { feelPress, tg } from "../shared/telegram";
// 거래 내역 화면(`?trades={지수}`)은 내 자산 페이지의 거래 내역 단추와 초록 신호등 카드, 집행 알림의 단추가 여는 화면이다. 계좌 요약과 함께 받은 거래 내역(`trades`)에서
// 그 지수의 블록을 맨 위가 최신이 되게 쌓는다. 그날 승인 요청(`trades.request`)이 그 지수에 주문을 두었고 집행 시각(`run_at`, KST) 전이면,
// 그날 블록을 거래 내역 절 위 집행 요청 절로 옮기고 취소·승인 단추를 단다. 단추는 Worker의 `/decide`에 결정을 적고, Worker가 돌려준 결정으로 블록을 다시 그린다.
// 결정은 지수마다 따로이고, 아무것도 누르지 않은 지수는 집행 시각에 그대로 집행한다. 집행 시각이 지나면 그 블록을 거래 내역 절로 내려 단추를 끈다.
// 받아 둔 계좌 요약이 있으면 그 값부터 그리고, 화면을 열 때와 미니 앱으로 돌아올 때마다 새로 받는다.
export const TRADE_STATE = {
  pending: ["결정 대기", "wait"], approved: ["승인", "wait"], rejected: ["취소", "off"], auto_approved: ["무응답 승인", "done"],
  executed: [], unfilled: ["미체결", "off"], not_required: ["주문 없음", "off"],
};
export function tradesPage(index) {
  const title = `${INDEX_NAME[index]} 거래 내역`;
  document.title = title;
  document.getElementById("issue-bar").textContent = title;
  const page = Object.assign(document.createElement("div"), { className: "trades-page" });
  report.replaceChildren(page);
  const WEEK = "일월화수목금토", clock = (runAt) => runAt.slice(11, 16), due = (runAt) => Date.parse(`${runAt}:00+09:00`);
  const side = (value) => (value === "BUY" ? '<span class="side up">매수</span>' : '<span class="side down">매도</span>');
  let last = null, timer = null;
  const render = (data) => {
    last = data;
    clearTimeout(timer);
    const trades = data.trades, request = trades?.request, now = Date.now();
    const asked = request && (request.sectors?.[index]?.order_count || 0) > 0 && now < due(request.run_at) ? request : null;
    const decided = data.decisions?.date === request?.date ? data.decisions.sectors?.[index]?.decision : null;
    const blocks = trades?.sectors?.[index] || [];
    const open = asked && blocks.find((block) => block.date === asked.date);
    const block = (b, live) => {
      const state = live ? ({ approve: "approved", cancel: "rejected" }[decided] || asked.sectors[index].status) : b.state;
      const running = !live && b.run_at && ["pending", "approved"].includes(state) && now >= due(b.run_at);
      const [label, kind] = running ? ["집행 중", "wait"] : TRADE_STATE[state] || [state, "off"];
      const rows = b.executions?.length
        ? b.executions.map((e) => assetRow(`${e.symbol}${side(e.side)}`, e.quantity != null ? assetShares(e.quantity) : "", e.amount != null ? `$${figure(e.amount)}` : "",
          `${e.at.slice(11, 16)} ${e.filled ? "체결" : "미체결"}`).replace('"asset-item"', e.filled ? '"asset-item"' : '"asset-item miss"'))
        : (b.orders || []).map((o) => assetRow(`${o.symbol}${side(o.side)}`, o.shares != null ? `약 ${assetShares(o.shares)}` : "", assetMoney(o.krw, "KRW"),
          o.usd != null ? `약 $${figure(o.usd)}` : ""));
      const act = live ? `<p class="note">${{ approved: `${clock(asked.run_at)}에 집행한다. 그 전까지 취소할 수 있다.`,
        rejected: `이 지수는 집행하지 않는다. ${clock(asked.run_at)} 전까지 다시 승인할 수 있다.` }[state] || `${clock(asked.run_at)}까지 취소하지 않으면 그대로 집행한다.`}</p>`
        + `<div class="act"><button type="button" data-decision="cancel"${state === "rejected" ? ' class="on" disabled' : ""}>${state === "rejected" ? "취소함" : "취소"}</button>`
        + `<button type="button" data-decision="approve" class="go${state === "approved" ? ' on" disabled' : '"'}>${state === "approved" ? "승인함" : "승인"}</button></div>` : "";
      return `<div class="trade" data-date="${b.date}"><div class="top"><b>${assetDay(b.date)} (${WEEK[new Date(`${b.date}T12:00:00Z`).getUTCDay()]})</b>`
        + (label ? `<span class="badge ${kind}">${label}</span>` : "") + "</div>"
        + (b.current != null && b.target != null ? `<div class="lev">현재 ${b.current.toFixed(3)}배 → 목표 ${b.target.toFixed(3)}배</div>` : "")
        + (b.reason ? `<p class="why">${assetText(b.reason)}</p>` : "") + (rows.length ? `<div class="rows">${rows.join("")}</div>` : "") + act + "</div>";
    };
    const past = blocks.filter((b) => b !== open);
    page.innerHTML = (open ? `<h2>집행 요청</h2>${block(open, true)}` : "")
      + `<h2>거래 내역</h2>` + (past.length ? past.map((b) => block(b)).join("") : '<p class="status">거래 내역이 없다.</p>');
    if (open) timer = setTimeout(() => render(last), due(asked.run_at) - now + 1000);
  };
  const status = (text) => { if (!last) page.innerHTML = `<h2>거래 내역</h2><p class="status">${text}</p>`; };
  page.addEventListener("click", async (event) => {
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
  const saved = assetSaved();
  if (saved) render(saved); else status("거래 내역을 불러오는 중이다.");
  const load = () => account().then((data) => {
    if (!data) { last = null; return status("본인 계정에서만 볼 수 있다."); }
    try { sessionStorage.setItem(ASSET_FLAG, JSON.stringify(data)); } catch {}
    render(data);
  }, () => status("거래 내역을 불러오지 못했다. 미니 앱을 다시 열면 새로 받는다."));
  load();
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") load(); });
}
