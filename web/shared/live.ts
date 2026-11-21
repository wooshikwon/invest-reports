import { life } from "./route";
// 실시간 값 `premarket`·`afterhours`·`progress`·`index`는 claude-svr가 invest-live Worker(`LIVE_URL`)에 쓰고, Worker가 `GET /` 한 번에 `{ premarket, afterhours, progress, index }`로 돌려주는 값이다.
// 값이 없는 이름은 키가 없다. 처음 받을 때 Worker가 답하지 않으면 빈 값으로 보고, 화면은 리포트에 적힌 값으로 그린다. 그 뒤로 답하지 않은 회차는 받아 둔 값을 그대로 둔다.
// `premarket`은 뉴욕 프리장부터 정규장 마감까지 지수마다 적는 그날 프리장이나 정규장의 마지막 체결가이고, `afterhours`는 정규장 마감 값을 고정한 뒤
// 애프터장이 끝날 때까지 지수마다 적는 그날 애프터장의 마지막 체결가다. 선물 시간대에는 나스닥 선물 등락으로 바꾼 나스닥 애프터장 값이다.
// 머리 상자, 지도, 주가 카드, 종목 상세의 주가 카드가 쓴다. `index`는 유가 카드의 로드 줄이 쓴다.
// `progress`는 판단 배치 동안 지수마다 적는 단계와 그 단계에 닿은 시각이다. 판단 없는 날짜 지점의 단계 표시가 쓴다.
// 지도와 종목 상세는 세션 날짜별 값(`early`·`after`)을 쓴다. 리포트 화면의 머리 상자와 주가 카드는 날짜 지점별 값(`points`)을 쓴다.
export const LIVE_URL = "https://invest-live.wonwooshik.workers.dev";
// 실시간 값을 받는 간격(분)이다. Worker 요청 수가 하루 한도에 다가가면 이 값 하나를 3이나 5로 올린다.
export const LIVE_EVERY = 1;
// 서버는 매 분 0초에 값을 새로 쓰므로, 앱은 간격의 정시에서 3초 뒤에 받는다.
const LATE = 3e3;

// `points`는 지수마다 날짜 지점(`point`)별로 묶은 값 `{ pre, regular, after }`이다. 지점 N의 `after`는 N 앞 세션의 애프터장(선물 시간대 포함) 값이고,
// `pre`는 N의 프리장 값, `regular`는 N의 정규장 값(`ohlc` 포함)이다. `index`는 지수와 WTI의 1분 값 `{ price, time, loaded }`이다.
export type Live = { early: Record<string, any>; after: Record<string, any>; progress: Record<string, any>; points: Record<string, any>; index: Record<string, any> };
type Hook = (found: Live) => void;

// 지금부터 다음 `every`분 간격 정시 3초 뒤까지 남은 밀리초다. 간격은 1970년 1월 1일 0시부터 세므로 1·3·5분 간격의 정시는 매시 정각에서 시작한다.
export const nextBeat = (every: number, now = Date.now()) => {
  const period = every * 60e3;
  return (Math.floor((now - LATE) / period) + 1) * period + LATE - now;
};

// `every`분 간격 정시 3초 뒤마다 `run`을 부른다. 화면이 숨거나 `active`가 거짓이면 다음 회차를 걸지 않고, `signal`이 끊기면 걸어 둔 회차를 푼다.
// 돌려주는 `arm`은 다음 회차를 다시 건다. 조건이 바뀐 곳(구독, 화면이 다시 보임, 페이지 전환)에서 부른다.
export function beat(every: number, run: () => void, active: () => boolean, signal: AbortSignal) {
  let timer = 0;
  const stop = () => { clearTimeout(timer); timer = 0; };
  const arm = () => {
    stop();
    if (signal.aborted || document.visibilityState !== "visible" || !active()) return;
    timer = setTimeout(() => {
      timer = 0;
      if (document.visibilityState !== "visible" || !active()) return;
      run();
      arm();
    }, nextBeat(every));
  };
  signal.addEventListener("abort", stop, { once: true });
  document.addEventListener("visibilitychange", () => (document.visibilityState === "visible" ? arm() : stop()), { signal });
  return arm;
}

const hooks: { hook: Hook; each: boolean; signal: AbortSignal }[] = [];
let text: string | null = null, found: Live | null = null, asking: Promise<boolean> | null = null, arm = () => {};

const shape = (value: any): Live => {
  const early = {};
  Object.entries(value.premarket || {}).forEach(([index, days]: [string, any]) => {
    early[index] = {};
    Object.entries(days).forEach(([day, value]: [string, any]) => {
      if (value.phase !== "regular") return (early[index][day] = value);
      early[index][day] = value.pre ? { ...value.pre, session: value.session, phase: "pre" } : null;
    });
  });
  const points = {};
  const at = (index, point) => ((points[index] ??= {})[point] ??= {});
  Object.entries(value.premarket || {}).forEach(([index, days]: [string, any]) => Object.values(days).forEach((v: any) => {
    if (!v?.point) return;
    if (v.phase === "regular") {
      at(index, v.point).regular = v;
      if (v.pre) at(index, v.point).pre = { ...v.pre, session: v.session, phase: "pre", point: v.point };
    } else at(index, v.point).pre = v;
  }));
  Object.entries(value.afterhours || {}).forEach(([index, days]: [string, any]) => Object.values(days).forEach((v: any) => { if (v?.point) at(index, v.point).after = v; }));
  return { early, after: value.afterhours || {}, progress: value.progress || {}, points, index: value.index || {} };
};

// `GET /`을 한 번 부른다. 받은 본문이 앞 회차와 같거나(304를 받은 브라우저는 저장해 둔 같은 본문을 건넨다) Worker가 답하지 않았으면 거짓을 돌려준다.
const ask = () => (asking ||= fetch(`${LIVE_URL}/`, { cache: "no-cache" })
  .then((r) => (r.ok ? r.text() : null)).catch(() => null)
  .then((body) => {
    asking = null;
    if (body == null) {
      if (found) return false;
      body = "{}";
    }
    if (body === text && found) return false;
    let value = {};
    try { value = JSON.parse(body) || {}; } catch {}
    text = body;
    found = shape(value);
    return true;
  }));

// 실시간 값을 쓰는 리포트(가장 늦은 리포트)를 보는 동안에만 정시마다 받는다. 지난 리포트(`past`)는 연 때 한 번만 받는다.
const live = () => hooks.length > 0 && !document.documentElement.classList.contains("past");
const tick = () => ask().then((changed) => hooks.forEach(({ hook, each, signal }) => signal.aborted || (changed || each) && hook(found)));

// 화면은 `subscribe(hook)`으로만 실시간 값을 받는다. 받아 둔 값이 있으면 그 값으로, 없으면 받은 뒤 `hook`을 부르고, 그 뒤로는 값이 바뀐 회차에만 다시 부른다.
// `each`가 참이면 값이 같아도 회차마다 부른다. 구독은 그 화면의 수명(`life`)에 묶인다.
export const subscribe = (hook: Hook, each = false) => {
  const { signal } = life;
  hooks.push({ hook, each, signal });
  (found ? Promise.resolve(true) : ask()).then(() => signal.aborted || hook(found));
  arm();
};

// 화면을 바꾸면 구독과 받아 둔 값을 비운다. 다음 화면은 처음 구독할 때 새로 받는다.
export const forget = () => {
  hooks.length = 0;
  text = found = null;
  arm();
};

// 화면이 다시 보이면 바로 한 번 받은 뒤 정시 주기로 돌아간다. 숨은 동안에는 회차를 걸지 않는다.
export function initLive() {
  arm = beat(LIVE_EVERY, tick, live, new AbortController().signal);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && live()) tick(); });
}
