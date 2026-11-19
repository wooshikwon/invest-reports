// @ts-nocheck
import { tg } from "./telegram";
// 내 자산 페이지는 본인 텔레그램 계정으로 연 리포트 화면의 맨 앞 페이지다. 계좌 요약은 invest-account Worker가 텔레그램 서명과 사용자 ID를 검증한 뒤에만 건넨다.
// 텔레그램 앱 안에서 연 화면은 initData를 Worker에 보내고, 본인 계정인지는 Worker만 판정한다. Worker가 403을 답하면 `sessionStorage`에 거절 표시(`ASSET_DENIED`)를 적어
// 같은 세션에서는 다시 묻지 않는다. Worker는 서명한 지 하루가 지난 initData를 거절하므로, 하루 넘게 열어 둔 화면은 요청하지 않고 받아 둔 값을 그대로 둔다.
export const ASSET = "자산", ASSET_FLAG = "asset", ASSET_DENIED = "asset-denied";
export const ASSET_URL = "https://invest-account.wonwooshik.workers.dev";
export async function account() {
  if (!(tg && tg.initData && tg.initDataUnsafe?.user)) return null;
  try { if (sessionStorage.getItem(ASSET_DENIED)) return null; } catch {}
  if (Date.now() / 1000 - tg.initDataUnsafe.auth_date > 86000) throw new Error("stale");
  const response = await fetch(ASSET_URL, { method: "POST", body: tg.initData, cache: "no-store" });
  if (response.status === 403) {
    try { sessionStorage.setItem(ASSET_DENIED, "1"); } catch {}
    return null;
  }
  if (!response.ok) throw new Error(response.status);
  return response.json();
}
export const assetSaved = () => { try { return JSON.parse(sessionStorage.getItem(ASSET_FLAG)); } catch { return null; } };
