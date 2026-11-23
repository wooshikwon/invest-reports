// @ts-nocheck
import { ASSET_FLAG, account, assetSaved } from "../shared/account";
import { INDEX_NAME } from "../shared/chrome";
import { rolled } from "../shared/roll";
// 거래 내역 화면(`?trades={지수}`)은 내 자산 페이지의 거래 내역 단추와 알림 카드가 여는 화면이다. 계좌 요약과 함께 받은 거래 내역(`trades`)에서
// 그 지수의 블록을 맨 위가 최신이 되게 쌓는다. 거래 내역 절 위 주문 요청 절은 맨 위에 그 지수의 집행 신호등 카드를 신호등 색과 관계없이 둔다.
// 그날 승인 요청(`trades.request`)이 그 지수에 주문을 두었고 집행 시각(`run_at`, KST) 전이면, 그날 블록을 주문 요청 절로 옮기고 취소·승인 단추를 단다. 단추는 Worker의 `/decide`에 결정을 적고, Worker가 돌려준 결정으로 블록을 다시 그린다.
// 결정은 지수마다 따로이고, 아무것도 누르지 않은 지수는 집행 시각에 그대로 집행한다. 집행 시각이 지나면 그 블록을 거래 내역 절로 내려 단추를 끈다.
// 사용자가 SGOV 투입을 지시한 날은 그 수기 요청(`trades.instructed`)을 지수 블록 아래 별도 블록으로 두고, 지수의 리밸런싱과 따로 취소·승인을 받는다.
// 받아 둔 계좌 요약이 있으면 그 값부터 그리고, 화면을 열 때와 미니 앱으로 돌아올 때마다 새로 받아 바뀐 기간 투자액 숫자를 굴린다.
// 거래 내역을 그리는 글씨와 단추는 내 자산 조각(`asset-view.ts`)의 `tradesView`에 있고, Worker가 계좌 요약을 건넨 뒤에야 조각을 불러온다.
let view = null;
export function mount(root, { index, signal }) {
  const title = `${INDEX_NAME[index]} 거래 내역`;
  document.title = title;
  document.getElementById("issue-bar").textContent = title;
  const page = Object.assign(document.createElement("div"), { className: "trades-page" });
  root.replaceChildren(page);
  let last = null, made = null;
  const render = (data, roll = false) => {
    last = data;
    (made ||= import("./asset-view").then((chunk) => chunk.tradesView(page, index))).then((drawn) => {
      if (signal.aborted) return;
      view = drawn;
      if (last) roll ? rolled(() => drawn.render(last)) : drawn.render(last);
    });
  };
  const status = (text) => { if (!last) page.innerHTML = `<h2>거래 내역</h2><p class="status">${text}</p>`; };
  const saved = assetSaved();
  if (saved) render(saved); else status("거래 내역을 불러오는 중이다.");
  const load = () => account().then((data) => {
    if (signal.aborted) return;
    if (!data) { last = null; view?.stop(); return status("본인 계정에서만 볼 수 있다."); }
    try { sessionStorage.setItem(ASSET_FLAG, JSON.stringify(data)); } catch {}
    render(data, true);
  }, () => signal.aborted || status("거래 내역을 불러오지 못했다. 미니 앱을 다시 열면 새로 받는다."));
  load();
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") load(); }, { signal });
}
// 거래 내역 화면을 걷으면 집행 시각에 블록을 내리려고 걸어 둔 회차를 푼다.
export function unmount() {
  view?.stop();
  view = null;
}
