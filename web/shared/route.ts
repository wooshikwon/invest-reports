// @ts-nocheck
import * as reportScreen from "../pages/report";
import * as stockScreen from "../pages/stock";
import * as tradesScreen from "../pages/trades";
import { ASSET } from "./account";
import { backEdge, backward } from "./back";
import { latest, masthead, paint, ticker, unglos } from "./chrome";
import { listed, parts, reportPart, reportText, texts } from "./data";
import { forget } from "./live";
import { unpress } from "./press";
import { cache, landed } from "./pull";
import { tg } from "./telegram";
export let query = new URLSearchParams(location.search);
// 지수 단추로 고른 리포트는 주소의 `r`로 다시 연다. 텔레그램은 다시 연 뒤에도 처음 받은 `start_param`을 그대로 주므로 `r`을 먼저 읽는다.
// 홈 화면 바로가기는 `start_param` 없이 미니 앱을 열므로, 키가 없으면 리포트를 받기 전에 `r/index.json`에서 키를 정한다.
// 주소에 `issue`가 있으면 리포트 대신 그 번호의 이슈 하나를 보이는 이슈 화면을 그리고, `at`이 있으면 히스토리에서 그 날짜 항목을 고른다.
// 주소에 `stock`이 있으면 이슈 화면과 같은 틀에 그 티커의 종목 상세를 그린다.
// 주소에 `trades`가 있거나 집행 알림의 단추가 `start_param`으로 `trades-{지수}`를 주면 같은 틀에 그 지수의 거래 내역 화면을 그린다.
// 알림 단추로 연 화면은 그 지수의 최신 리포트 키를 `r`에, 지수를 `trades`에 적은 주소로 기록을 바꾼다.
export const opened = (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) || query.get("tgWebAppStartParam") || "";
export const trades = ["nasdaq", "biotech"].find((index) => query.get("trades") === index || (!query.get("r") && opened === `trades-${index}`)) || "";
export let key = query.get("r") || (trades ? "" : opened);
export const report = document.getElementById("report");
// 미니 앱 안에서 다른 리포트로 옮기면 주소의 `r`을 바꿔 페이지를 다시 열므로 브라우저 기록이 하나씩 쌓인다. 기록마다 처음 연 리포트에서
// 몇 번 옮겨 왔는지(`depth`)를 `history.state`에 적는다. 옮기기 직전에 다음 깊이를 `sessionStorage`에 두고, 새 페이지가 그 값을 읽어 자기 기록에 적는다.
// 뒤로 가기로 돌아온 페이지는 자기 기록에 적힌 깊이를 그대로 쓴다. 지수 단추는 페이지를 다시 열지 않고 기록을 하나 더해 그 기록에 다음 깊이를 적는다.
// 리포트 화면에서 옮겨 온 페이지는 앞 화면의 리포트 키(`from`)도 같은 방법으로 자기 기록에 적는다. 이슈 화면과 종목 상세에서 옮겨 왔으면 빈 글자를 적는다.
export let depth = 0;
export let from = "";
export function initHistory() {
  depth = history.state?.depth ?? (+sessionStorage.getItem("depth") || 0);
  from = history.state?.from ?? (sessionStorage.getItem("from") || "");
  sessionStorage.removeItem("depth");
  sessionStorage.removeItem("from");
  history.replaceState({ ...history.state, depth, from }, "");
// 옮기기 직전의 화면 위치(`y`)도 자기 기록에 적는다. 브라우저는 리포트를 받아 그리기 전에 화면 위치를 되돌리려다 실패하므로, 되돌리기는 페이지가 맡는다.
  history.scrollRestoration = "manual";
}
// 이슈 화면(`issue`, `at`)과 종목 상세(`stock`, `session`), 거래 내역 화면(`trades`)은 `more`로 줄 때만 주소에 적고, 다른 리포트로 옮길 때는 지운다.
export const visit = (target, more = {}) => {
  history.replaceState({ ...history.state, y: scrollY }, "");
  sessionStorage.setItem("depth", depth + 1);
  sessionStorage.setItem("from", query.get("issue") || query.get("stock") || trades ? "" : key);
  const params = new URLSearchParams(location.search);
  params.delete("issue");
  params.delete("at");
  params.delete("stock");
  params.delete("session");
  params.delete("trades");
  params.set("r", target);
  Object.entries(more).forEach(([name, value]) => params.set(name, value));
  location.search = params.toString();
};
export const fail = (message) => { report.innerHTML = `<p class="status">${message}</p>`; };
// 종목 상세는 리포트 대신 `r/stocks/{티커}.json`을 받아 그린다(`pages/stock.ts`). 거래 내역 화면은 리포트를 받지 않고 계좌 요약으로 그린다(`pages/trades.ts`).
export const symbol = query.get("stock");
// 한 화면이 받는 값과 거는 손길은 그 화면의 수명(`life`)에 묶는다. 화면을 바꾸면 수명을 끊어 앞 화면의 손길을 떼고, 늦게 받은 값으로 앞 화면을 그리지 않는다.
export let life = new AbortController();
// 뒤로 가기로 돌아온 화면이면 `returned`가 참이다. 처음 연 문서는 브라우저가 알려 주는 이동 종류로, 그 자리에서 다시 그린 화면은 기록 이동(`popstate`)인지로 정한다.
export let returned = performance.getEntriesByType("navigation")[0]?.type === "back_forward";
// 지수 단추와 뒤로 가기는 문서를 다시 열지 않고 그 자리에서 화면을 다시 그린다(`reshow`). 리포트 키와 깊이는 바뀐 기록에서 다시 읽는다.
// 앞 화면은 새 화면을 그리기 직전에 걷는다(`leave`). 날짜 줄과 지수 단추, 과거 리포트 띠, 시세 줄, 바로가기 알약, 뒤로 가기 띠, 말풍선, 그림 카드의 지수색 칠을 지우고,
// 실시간 값을 받는 곳을 비운 뒤 화면을 맨 위로 옮긴다.
export const leave = () => {
  forget();
  unglos();
  unpress();
  document.querySelectorAll(".index-pick, .back-edge, .back-ring, nav.jump, body > .bubble").forEach((node) => node.remove());
  document.getElementById("index-ink")?.ownerSVGElement.remove();
  document.documentElement.classList.remove("past", "edging");
  masthead.classList.remove("stuck");
  report.classList.remove("flow");
  document.getElementById("day").textContent = "";
  document.getElementById("past").textContent = "";
  ticker.textContent = "";
  scrollTo(0, 0);
};
export const reshow = (back) => {
  life.abort();
  life = new AbortController();
  returned = back;
  query = new URLSearchParams(location.search);
  key = query.get("r") || opened;
  ({ depth = 0, from = "" } = history.state || {});
  present();
};
// 화면은 저마다 `mount(root, ctx)`로 본문 상자(`report`)에 그리고 `unmount()`로 걷는다. `ctx.signal`은 그 화면의 수명이다.
// 새 화면을 그리기 직전에 앞 화면을 걷고(`unmount`), 화면마다 같은 머리 상자와 바로가기를 걷은 뒤(`leave`) 새 화면을 그린다.
let screen = null;
const mount = (next, ctx) => {
  screen = next;
  return next.mount(report, { signal: life.signal, ...ctx });
};
export function present() {
  const { signal } = life;
  const arrive = () => {
    screen?.unmount();
    screen = null;
    leave();
    paint();
    if (depth > 0 && !query.get("issue") && !symbol && !trades) backEdge();
  };
  (/^\d{8}-[a-z]+$/.test(key) ? Promise.resolve(key) : listed.then((listing) => latest(listing, trades || "nasdaq"))).then((found) => {
    if (!found) throw new Error("no report");
    key = found;
    if (trades) {
      arrive();
      if (!query.get("trades")) history.replaceState(history.state, "", `?r=${key}&trades=${trades}`);
      backward(["trades"], ASSET);
      return mount(tradesScreen, { index: trades });
    }
    if (symbol) {
      arrive();
      if (!/^[A-Z][A-Z.-]{0,9}$/.test(symbol)) throw new Error("bad symbol");
      return fetch(`r/stocks/${symbol}.json`, { cache }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then((data) => mount(stockScreen, { data }));
    }
    // 리포트 화면은 요약 카드 값을 받은 뒤 그리고, 이슈 과거 맥락은 그린 뒤 받아 붙인다. 이슈 화면은 이슈 과거 맥락을 받은 뒤 그리고 요약 카드 값은 받지 않는다.
    const text = reportText(key), issue = !!query.get("issue");
    return listed.then((listing) => {
      const history = reportPart(key, "history", listing).catch(() => null);
      return Promise.all([text, issue ? null : reportPart(key, "cards", listing), issue ? history : null]).then(([body, cards, past]) => {
        delete texts[found];
        delete parts[`${found}/history`];
        delete parts[`${found}/cards`];
        if (signal.aborted) return;
        arrive();
        mount(reportScreen, { body, listing, cards, history: issue ? past : history });
      });
    });
  }).catch(() => {
    if (signal.aborted) return;
    arrive();
    fail(symbol ? "종목을 찾지 못했다." : "리포트를 찾지 못했다.");
  }).finally(() => landed());
}
export function initRoute() {
  if (query.get("issue") || query.get("stock") || trades) document.documentElement.classList.add("issue");
}
export function initPopstate() {
  addEventListener("popstate", () => reshow(true));
}
