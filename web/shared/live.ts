// @ts-nocheck
import { listed } from "./data";
import { key, life } from "./route";
// 실시간 값 `premarket`·`afterhours`·`progress`는 claude-svr의 build.py가 Cloudflare KV에 쓰고 invest-live Worker(`LIVE_URL`)가 `GET /{이름}`으로 돌려주는 값이다.
// Worker가 답하지 않으면 빈 값으로 보고, 화면은 리포트에 적힌 값으로 그린다.
// `premarket`은 build.py `premarket`이 뉴욕 프리장부터 정규장 마감까지 10분마다 지수마다 적는 그날 프리장이나 정규장의 마지막 체결가이고, `afterhours`는
// build.py `afterhours`가 사전 리포트를 올린 뒤 애프터장이 끝날 때까지 10분마다 지수마다 적는 그날 애프터장의 마지막 체결가다. 머리 상자, 지도, 주가와 예측 카드,
// 종목 상세의 주가 카드가 쓴다. `onLive(hook)`은 두 값을 `{ early, after, regular }`로 묶어 `hook`을 부르고, 가장 늦은 리포트를 보는 동안 화면이 보이면 5분마다,
// 화면이 다시 보일 때마다 새로 받아 다시 부른다.
// 정규장 값은 그 세션이 열릴 때 만든 다음날 사전 리포트(목록 항목의 `live`가 그 세션 날짜인 리포트)만 그린다. 그 리포트는 `early`에서 그 값을
// 리포트 날짜 키로 받고, 다른 리포트는 정규장 값 대신 그날 프리장의 마지막 값(`pre`)을 받는다. `regular`는 지수마다 뉴욕 날짜별 정규장 값이다.
export const LIVE_URL = "https://invest-live.wonwooshik.workers.dev";
export const liveValue = (name) => fetch(`${LIVE_URL}/${name}`, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
export const hooks = [];
export let lived = null;
export const forget = () => { hooks.length = 0; lived = null; };
export const live = () => (lived = Promise.all([...["premarket", "afterhours"].map(liveValue), listed]).then(([found, after, listing]) => {
  const own = listing[key], early = {}, regular = {};
  Object.entries(found).forEach(([index, days]) => {
    early[index] = {};
    regular[index] = {};
    Object.entries(days).forEach(([day, value]) => {
      if (value.phase !== "regular") return (early[index][day] = value);
      regular[index][day] = value;
      early[index][day] = value.pre ? { ...value.pre, session: value.session, phase: "pre" } : null;
    });
    if (own?.live && own.index === index) early[index][own.date] = days[own.live] ?? null;
  });
  return { early, after, regular };
}));
export const onLive = (hook) => {
  const { signal } = life;
  hooks.push(hook);
  (lived || live()).then((found) => signal.aborted || hook(found));
};
export const refresh = () => {
  if (!hooks.length || document.visibilityState !== "visible" || document.documentElement.classList.contains("past")) return;
  live().then((found) => hooks.forEach((hook) => hook(found)));
};
export function initLive() {
  setInterval(refresh, 5 * 60e3);
  document.addEventListener("visibilitychange", refresh);
}
