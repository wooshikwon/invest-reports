// @ts-nocheck
import { ASSET, ASSET_FLAG, account, assetSaved } from "../shared/account";
import { stale } from "../shared/session";
import { beat } from "../shared/live";
import { rolled } from "../shared/roll";
import { life, report } from "../shared/route";
// 리포트 화면의 페이지(`pages`, 이름은 `names`)를 `place`로 묶고 `name` 페이지를 연다. 본인 계정이면 내 자산 페이지를 맨 앞에 더한다.
// Worker가 계좌 요약을 건네면 기기의 `localStorage`에 표시(`ASSET_FLAG`)를 적는다. 표시가 있는 기기는 리포트 화면을 열자마자 내 자산 페이지를 맨 앞에 두고,
// 열 페이지가 정해지지 않았으면 내 자산 페이지를 연다. 표시가 없는 기기는 열 페이지가 정해지지 않았으면 첫 페이지인 지수 페이지를 연다. 받은 계좌 요약은 `sessionStorage`에 두어 같은 세션에서 다시 연 리포트 화면은 받은 값부터 그리고,
// 리포트 화면을 열 때와 미니 앱으로 돌아올 때, 내 자산 페이지가 보이는 동안 1분마다 새로 받는다. 본인 계정이 아니거나 Worker가 403을 답하면 표시와 받아 둔 값을 지우고 내 자산 페이지를 뺀다.
export function assets(pages, names, place, name) {
  const store = (area, value) => { try { if (value == null) area.removeItem(ASSET_FLAG); else area.setItem(ASSET_FLAG, value); } catch {} };
  const flagged = (() => { try { return localStorage.getItem(ASSET_FLAG) === "1"; } catch { return false; } })();
  const page = Object.assign(document.createElement("div"), { className: "page" });
  let shown = false, arm = () => {};
  // 이미 연 화면(`still`)에 페이지를 넣거나 뺄 때는 보던 페이지와 화면 위치를 그대로 둔다. 내 자산 페이지를 보다가 빼면 첫 페이지를 맨 위부터 연다.
  const show = (on, still) => {
    shown = on;
    const y = scrollY, at = history.state?.page;
    if (on) report.prepend(page); else page.remove();
    place(on ? [page, ...pages] : pages, on ? [ASSET, ...names] : names, still ? (at === ASSET && !on ? null : at) : name || (on ? ASSET : names[0]), still);
    if (still && (on || at !== ASSET)) scrollTo(0, y);
    arm();
  };
  // 계좌 요약을 받기 전과 받지 못했을 때는 안내 한 줄만 쓴다. 한 번 그린 페이지는 받지 못한 회차에도 그대로 둔다.
  // 계좌 요약을 그리는 글씨와 그림은 내 자산 조각(`asset-view.ts`)에 있고, Worker가 계좌 요약을 건넨 뒤에야 조각을 불러온다.
  const { signal } = life;
  let drawn = false, seen = null, paint = null;
  const fill = (data, roll = false) => {
    if (!data || data.error) {
      if (!data || !drawn) page.innerHTML = `<h2>내 투자</h2><p class="status">${data ? "계좌를 불러오지 못했다. 미니 앱을 다시 열면 새로 받는다." : "계좌를 불러오는 중이다."}</p>`;
      return;
    }
    drawn = true;
    seen = JSON.stringify(data);
    (paint ||= import("./asset-view").then((chunk) => chunk.assetPage(page))).then((draw) => signal.aborted || (roll ? rolled(() => draw(data)) : draw(data)));
  };
  fill(assetSaved());
  if (flagged) show(true, false);
  else place(pages, names, name, false);
  // 받은 계좌 요약이 앞에 그린 값과 같으면 다시 그리지 않고, 다르면 바뀐 큰 글씨 숫자를 굴려 다시 그린다. 값이 같아도 휴장이면 기준 시각의 지금 시각을 바꾸려고 다시 그린다.
  const load = () => account().then((data) => {
    if (signal.aborted) return;
    store(localStorage, data && "1");
    store(sessionStorage, data && JSON.stringify(data));
    if (data && JSON.stringify(data) !== seen) fill(data, true);
    else if (data && stale(data.live?.time || data.time)) fill(data);
    if (!!data !== shown) show(!!data, true);
  }, () => signal.aborted || fill({ error: true }));
  load();
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && shown) load(); }, { signal });
  // 내 자산 페이지가 보이는 동안에는 1분마다 정시 3초 뒤에 새로 받는다. 다른 페이지로 넘기거나 화면이 숨으면 멈추고, 다시 보이면 주기로 돌아간다.
  arm = beat(1, load, () => shown && page.isConnected && !page.classList.contains("off"), signal);
  const watch = new MutationObserver(arm);
  watch.observe(page, { attributes: true, attributeFilter: ["class"] });
  signal.addEventListener("abort", () => watch.disconnect(), { once: true });
  arm();
}
