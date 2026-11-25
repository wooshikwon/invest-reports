// @ts-nocheck
import { backward } from "../shared/back";
import { issueChart } from "../shared/gauge";
import { EASE, GLIDE, atEdge, glide, homing, motion, slider } from "../shared/motion";
import { key, life, query, report, returned, visit } from "../shared/route";
import { feelPress, feelSlide } from "../shared/telegram";
import { gallery, viewer } from "../shared/viewer";
import { NEWS_HELP, question } from "../shared/help";
import { marketed } from "../shared/data";
import { linkStocks, stockNames } from "../shared/stocklink";
// 종목 뉴스를 그린다. 기사는 종목 뉴스 배치가 뉴스 Worker(`NEWS_URL`, `worker/news.js`)에 올린 것이고, 앱은 공개 읽기 세 경로만 쓴다.
// `GET /list?index={지수}`와 `GET /list?ticker={티커}&limit={편수}`는 기사마다 ID, 회차 시작 시각(`time`), 종목, 제목, 머리 줄(요약), 첫 그림 주소(`image`), 첫 종목의 회차 구간 변동률(`move`)을 주고,
// `GET /articles/{ID}`는 기사 한 편의 소제목 세 줄(`subheads`), 본문 HTML(`html`), 그림 주소와 사진 설명(`images`)을 더 준다. 목록의 머리 줄은 기사의 요약이고, 요약 없이 올린 기사는 첫 소제목이다. 본문 HTML은 build.py `issue_articles`가 만든 이슈 본문과 같은 조각이라
// 본문 소제목(`h5`), 이슈 그래프 카드(`figure.issue-chart`), 단어표 용어 단추(`button.term`)가 들어 있다.
// 리포트 화면의 상세 이슈 해설 절은 "주요 이슈 해설"과 "종목별 뉴스" 두 탭을 두고(`newsTab`), 종목 상세는 공시 상세 위에 주요 뉴스 절을 둔다(`headlines`).
// 기사를 누르면 주소의 `news`에 기사 ID를 적어 뉴스 상세를 연다. 종목 상세에서 열면 `ticker`에 그 티커도 적는다.
// 뉴스 상세 본문은 종목마다 처음 나오는 이름을 종목 상세로 가는 단추로 감싼다(`shared/stocklink.ts`). 이름은 `r/market.json` 지도 종목의 부르는 이름과 별칭이다.
// Worker가 답하지 않으면 종목 뉴스 탭과 주요 뉴스 절에 빈 상태 문구를 쓰고, 상세 이슈 해설 탭은 그대로 둔다.
export const NEWS_URL = "https://invest-news.wonwooshik.workers.dev";
// 다른 장으로 넘긴 뒤 목록 머리를 둘 화면 위쪽 여백(px). 머리 상자에 가리지 않는 높이다.
const TOP = 120;
// 종목 상세 주요 뉴스 절이 받는 기사 수, 한 장에 담는 기사 수, 번호 줄에 한 번에 보이는 번호 수.
const STOCK_NEWS = 50, PAGE = 5, NUMBERS = 5;
// Worker를 기다리는 시간. 넘기면 답하지 않은 것으로 본다.
const WAIT = 8e3;
// 같은 주소는 한 문서에서 한 번만 받는다. 받지 못한 주소는 지워 다음에 다시 받는다.
const asked = {};
const ask = (path) => (asked[path] ||= fetch(`${NEWS_URL}${path}`, { signal: AbortSignal.timeout?.(WAIT) })
  .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .catch((error) => { delete asked[path]; throw error; }));
export const newsList = (query) => ask(`/list?${query}`).then((value) => value.articles);
// 지수 목록의 한 장은 최신 회차의 이름·시작 시각(`round`·`time`), 등록한 회차의 기사 수(`total`), 한 장의 기사 수(`size`), 그 장의 기사(`articles`)다.
// 기사는 늦은 회차부터, 같은 회차 안에서는 첫 종목의 회차 구간 변동률(`move`)이 큰 기사부터 온다.
export const newsPage = (index, page = 1) => ask(`/list?index=${index}&page=${page}`);
export const newsArticle = (id) => ask(`/articles/${encodeURIComponent(id)}`);
// 회차 시작 시각 "2026-11-19T18:00:00+09:00"을 "11/19 18:00"으로 쓴다. 시각은 서울 시각 그대로다.
const clock = (time) => `${+time.slice(5, 7)}/${+time.slice(8, 10)} ${time.slice(11, 16)}`;
const empty = (text) => Object.assign(document.createElement("p"), { className: "empty", textContent: text });

// 장 번호 줄. 가운데에 장 번호를 보고 있는 장을 가운데에 두어 `NUMBERS`개까지, 양옆에 앞 장과 다음 장으로 가는 꺾쇠를 둔다.
// 번호나 꺾쇠를 누르면 진동을 내고 그 장 번호(0부터)로 `go`를 부른다. 돌려준 줄의 `draw(at)`는 `at`번 장을 고른 모양으로 다시 그린다.
function pager(count, go) {
  const arrow = (side, path) => {
    const button = Object.assign(document.createElement("button"), { type: "button", className: side });
    button.setAttribute("aria-label", side === "prev" ? "앞 장" : "다음 장");
    button.innerHTML = `<svg width="8" height="12" viewBox="0 0 8 12" aria-hidden="true"><path d="${path}" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    return button;
  };
  const prev = arrow("prev", "M6 1L1.5 6 6 11"), next = arrow("next", "M2 1l4.5 5L2 11");
  const numbers = Object.assign(document.createElement("span"), { className: "numbers" });
  const nav = Object.assign(document.createElement("nav"), { className: "pager" });
  nav.append(prev, numbers, next);
  let at = 0;
  const pick = (page) => { if (page === at || page < 0 || page >= count) return; feelPress(); go(page); };
  prev.addEventListener("click", () => pick(at - 1));
  next.addEventListener("click", () => pick(at + 1));
  nav.draw = (page) => {
    at = page;
    const first = Math.min(Math.max(0, at - Math.floor(NUMBERS / 2)), Math.max(0, count - NUMBERS));
    numbers.replaceChildren(...Array.from({ length: Math.min(NUMBERS, count) }, (_, k) => {
      const number = Object.assign(document.createElement("button"), { type: "button", className: first + k === at ? "on" : "", textContent: String(first + k + 1) });
      number.addEventListener("click", () => pick(first + k));
      return number;
    }));
    prev.disabled = at === 0;
    next.disabled = at === count - 1;
  };
  return nav;
}

// 종목 뉴스 목록 블록. 종목별 뉴스 목록(`full`)은 제목, 머리 줄(요약), 회차 시각을 위에서 아래로 쓰고, 회차 시각 오른쪽에 기사가 다룬 종목마다 티커 스티커를 붙이며,
// 같은 줄 오른쪽 끝에 첫 종목의 회차 구간 변동률을 "변동률 지수 : N%"로 회색 글씨로 쓴다. 변동률이 없는 기사는 변동률을 쓰지 않는다.
// 종목 상세 주요 뉴스 절은 제목과 회차 시각만 쓴다. 블록을 누르면 진동을 내고 `open`을 부른다.
function newsBlock(item, open, full) {
  const node = Object.assign(document.createElement("div"), { className: "pick" });
  const lead = node.appendChild(Object.assign(document.createElement("div"), { className: "lead" }));
  const text = lead.appendChild(Object.assign(document.createElement("div"), { className: "text" }));
  const age = Object.assign(document.createElement("div"), { className: "age" });
  age.append(clock(item.time));
  text.append(Object.assign(document.createElement("h3"), { textContent: item.title }));
  if (full) {
    age.append(...(item.tickers || []).map((ticker) => Object.assign(document.createElement("span"), { className: "ticker", textContent: ticker })));
    if (item.move !== null && item.move !== undefined) age.append(Object.assign(document.createElement("span"), { className: "move", textContent: `변동률 지수 : ${item.move.toFixed(2)}%` }));
    text.append(Object.assign(document.createElement("p"), { textContent: item.headline }));
  }
  text.append(age);
  node.addEventListener("click", () => {
    feelPress();
    open();
  });
  return node;
}

// 리포트 화면의 상세 이슈 해설 절 제목을 "주요 이슈 해설 | 종목별 뉴스" 탭 줄로 바꾼다. 탭 줄 아래 줄에는 왼쪽에 "마지막 업데이트 MM/DD HH:MM KST"를,
// 상세 이슈 해설 탭이면 오른쪽에 절 제목의 물음표 단추를 둔다. 상세 이슈 해설 탭은 분석 완료 시각과 이슈 목록을, 종목 뉴스 탭은 보고 있는 리포트 지수(`index`)의 종목 기사 목록을 보인다. 고른 탭 아래 막대는 다른 탭을 고르면 그 탭 아래로 옮겨 간다.
// 기사 목록은 종목 뉴스 탭을 처음 고를 때 지금까지 올라온 지수 기사의 첫 장을 받아 보인다. 한 장은 Worker가 정한 열 편이고, 장이 둘 이상이면 아래에 장 번호 줄을 둔다.
// 기사는 Worker가 준 순서(늦은 회차부터, 같은 회차 안에서는 첫 종목의 회차 구간 변동률이 큰 순서)로 놓는다. 이 절에서 좌우로 밀면 탭을 넘기므로 장은 번호 줄로만 넘긴다.
// 날짜 슬라이드로 지난 리포트를 열어도 지금 기준 기사를 보인다.
// 절 제목부터 다음 절 제목 앞까지(마지막 절이면 문서 끝까지)에서 가로로 40px 넘게, 세로 이동의 1.5배 넘게 밀고 손을 떼면 민 방향의 탭으로 넘긴다.
// 왼쪽으로 밀면 종목 뉴스, 오른쪽으로 밀면 상세 이슈 해설이다. 화면 좌우 끝 띠(`atEdge`)에서 시작한 밀기, 넘기기 묶음과 그림 화면, 설명 상자 안에서 민 것,
// 절이 가린 페이지에 있을 때는 넘기지 않는다.
// 처음 탭(`first`)은 상세 이슈 해설이다. 가장 늦은 리포트는 기사 목록을 바로 받아, 최신 회차에 그 지수 기사가 있고 그 회차의 시작 시각이 리포트의 분석 완료 시각(`written`, "2026-11-20 11:43" 같은 서울 시각)보다 늦으면
// 처음 탭을 종목 뉴스로 바꾸고 그 탭으로 넘긴다. 목록을 받기 전에 탭을 누르면 넘기지 않는다. 지난 리포트는 상세 이슈 해설 탭으로 연다.
// 고른 탭은 `history.state`의 `tab`에 적어, 이슈 화면이나 뉴스 상세에서 뒤로 돌아오면 떠나기 전 탭으로 연다. 처음 항목으로 돌릴 때(`motion.ts` `homing`)는 처음 탭으로 돌아간다.
// 다른 화면을 열면 문서가 숨겨지면서 처음 항목으로 돌리므로, 숨겨진 동안 돌린 탭은 적지 않고 화면이 다시 보일 때 적는다.
// 종목 뉴스 탭의 마지막 업데이트 시각은 최신 회차의 시작 시각이다. 목록은 상세 이슈 해설 목록과 같은 모양이되 그림을 싣지 않고, 기사마다 제목, 머리 줄(요약),
// 회차 시각을 위에서 아래로 쓴다. 회차 시각 오른쪽에는 기사가 다룬 종목마다 티커 스티커를 붙이고, 같은 줄 오른쪽 끝에 목록 순서를 정한 첫 종목의 회차 구간 변동률을
// "변동률 지수 : N%"로 회색 글씨로 쓴다. 변동률이 없는 기사는 쓰지 않는다.
export function newsTab(index, written) {
  const { signal } = life;
  const head = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === "상세 이슈 해설");
  if (!head) return;
  const own = [];
  for (let node = head.nextElementSibling; node && node.tagName !== "H2"; node = node.nextElementSibling) own.push(node);
  const box = Object.assign(document.createElement("div"), { className: "news-box", hidden: true });
  // 종목 뉴스 탭의 첫 줄. 왼쪽에 마지막 업데이트 시각을, 오른쪽에 설명 물음표 단추를 둔다.
  const stamp = document.createElement("span");
  const meta = Object.assign(document.createElement("p"), { className: "issue-asof meta" });
  meta.append(stamp, question("종목별 뉴스", () => {
    const list = document.createElement("ul");
    NEWS_HELP(index).forEach(([name, text]) => {
      const li = list.appendChild(document.createElement("li"));
      li.append(Object.assign(document.createElement("b"), { textContent: name }), text);
    });
    return [list];
  }));
  const body = document.createElement("div");
  box.append(meta, body);
  (own.at(-1) || head).after(box);
  const tip = head.querySelector(":scope > .help");
  const line = Object.assign(document.createElement("span"), { className: "tabline" });
  const tabs = ["주요 이슈 해설", "종목별 뉴스"].map((name, i) => {
    const tab = Object.assign(document.createElement("button"), { type: "button", textContent: name });
    tab.addEventListener("click", () => { touched = true; if (i !== shown) { feelPress(); pick(i, true); } });
    return tab;
  });
  const bar = Object.assign(document.createElement("i"), { className: "bar" });
  line.append(tabs[0], tabs[1], bar);
  // 상세 이슈 해설 탭의 아래 줄. `section`이 만든 분석 완료 시각 줄에 물음표 단추를 오른쪽에 붙인다.
  let asof = own.find((node) => node.classList?.contains("issue-asof"));
  if (!asof && tip) {
    asof = Object.assign(document.createElement("p"), { className: "issue-asof" });
    head.after(asof);
    own.unshift(asof);
  }
  if (asof) {
    asof.classList.add("meta");
    if (tip) asof.append(tip);
  }
  head.replaceChildren(line);
  head.classList.add("tabbed");
  const kept = returned ? history.state?.tab : undefined;
  let shown = -1, first = 0, filled = false, touched = kept === 0 || kept === 1;
  const keep = () => history.replaceState({ ...history.state, tab: shown }, "");
  const pick = (i, move) => {
    shown = i;
    if (!document.hidden) keep();
    tabs.forEach((tab, j) => tab.classList.toggle("on", i === j));
    if (!move) bar.style.transition = "none";
    bar.style.width = `${tabs[i].offsetWidth}px`;
    bar.style.transform = `translateX(${tabs[i].offsetLeft}px)`;
    bar.offsetWidth;
    bar.style.transition = "";
    own.forEach((node) => { node.hidden = i === 1; });
    box.hidden = i === 0;
    if (i && !filled) fill();
  };
  // `page`번 장(1부터)을 받아 기사 목록과 장 번호 줄을 그린다. 고른 장은 `history.state`의 `newsPage`에 적어, 뉴스 상세에서 뒤로 돌아와도 그 장을 연다.
  // 다른 장으로 넘기면 목록 머리가 화면 위에 가려져 있을 때 목록 머리까지 화면을 올린다.
  const fill = (page = history.state?.newsPage || 1, move = false) => {
    filled = true;
    if (!body.childElementCount) body.replaceChildren(Object.assign(document.createElement("p"), { className: "status", textContent: "종목 뉴스를 불러오는 중이다." }));
    newsPage(index, page).then(({ time, total, size, articles }) => {
      if (signal.aborted) return;
      if (time) stamp.textContent = `마지막 업데이트 ${clock(time)} KST`;
      if (!total) return body.replaceChildren(empty("올라온 종목 뉴스가 없다."));
      if (!articles.length) return fill(1);
      history.replaceState({ ...history.state, newsPage: page }, "");
      const list = Object.assign(document.createElement("div"), { className: "issue-list" });
      list.append(...articles.map((item) => newsBlock(item, () => visit(key, { news: item.id, page }), true)));
      const count = Math.ceil(total / size);
      if (count < 2) return body.replaceChildren(list);
      const nav = pager(count, (next) => fill(next + 1, true));
      nav.draw(page - 1);
      body.replaceChildren(list, nav);
      const top = box.getBoundingClientRect().top;
      if (move && top < TOP) scrollBy(0, top - TOP);
    }, () => {
      if (signal.aborted) return;
      filled = false;
      body.replaceChildren(empty("종목 뉴스를 불러오지 못했다."));
    });
  };
  let begin = null;
  document.addEventListener("touchstart", (event) => {
    begin = null;
    const { target, touches } = event;
    if (touches.length !== 1 || atEdge(touches[0].clientX) || head.closest(".page.off") || target.closest(".carousel, .viewer, .help-card, .back-edge, input")) return;
    let next = box.nextElementSibling;
    while (next && next.tagName !== "H2") next = next.nextElementSibling;
    const y = touches[0].clientY;
    if (y < head.getBoundingClientRect().top || (next && y >= next.getBoundingClientRect().top)) return;
    begin = { x: touches[0].clientX, y };
  }, { passive: true, signal });
  document.addEventListener("touchend", (event) => {
    if (!begin) return;
    const touch = event.changedTouches[0], dx = touch.clientX - begin.x, dy = touch.clientY - begin.y, to = dx < 0 ? 1 : 0;
    begin = null;
    if (Math.abs(dx) <= 40 || Math.abs(dx) <= 1.5 * Math.abs(dy) || to === shown) return;
    touched = true;
    feelSlide();
    pick(to, true);
  }, { passive: true, signal });
  pick(touched ? kept : first, false);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) keep(); }, { signal });
  homing(head, () => { touched = false; if (shown !== first) pick(first, false); });
  if (document.documentElement.classList.contains("past")) return;
  newsPage(index).then(({ round, time, articles }) => {
    if (signal.aborted || articles[0]?.round !== round || Date.parse(time) <= (written ? Date.parse(`${written.replace(" ", "T")}:00+09:00`) : 0)) return;
    first = 1;
    if (!touched) pick(1, false);
  }, () => {});
}

// 종목 상세에서 `after` 바로 뒤에 주요 뉴스 절을 두고, 절의 마지막 노드를 돌려준다. 절은 `symbol` 종목을 단 최신 기사 `STOCK_NEWS`편까지 받아
// 종목별 뉴스 목록과 같은 모양의 블록에 제목과 회차 시각만 쓰고, `PAGE`편씩 한 장에 담아 좌우로 밀어 넘긴다. 묶음 높이는 가장 높은 장에 맞춰 두어,
// 기사가 적은 마지막 장으로 넘겨도 줄지 않는다. 장이 둘 이상이면 아래에 번호 줄을 두고,
// 번호는 보고 있는 장을 가운데에 두어 `NUMBERS`개까지 보이며, 양옆 꺾쇠는 앞 장과 다음 장으로 넘긴다. 블록을 누르면 그 기사의 뉴스 상세를 연다.
export function headlines(after, symbol) {
  const { signal } = life;
  const head = Object.assign(document.createElement("h2"), { className: "issues inside", textContent: "주요 뉴스" });
  const box = Object.assign(document.createElement("div"), { className: "headlines" });
  after.after(head, box);
  newsList(`ticker=${encodeURIComponent(symbol)}&limit=${STOCK_NEWS}`).then((items) => {
    if (signal.aborted) return;
    if (!items.length) return box.replaceChildren(empty("최근 올라온 기사가 없다."));
    const pages = [];
    for (let i = 0; i < items.length; i += PAGE) {
      const list = Object.assign(document.createElement("div"), { className: "issue-list" });
      list.append(...items.slice(i, i + PAGE).map((item) => newsBlock(item, () => visit(key, { news: item.id, ticker: symbol }), false)));
      pages.push([list]);
    }
    if (pages.length === 1) return box.replaceChildren(pages[0][0]);
    const mark = document.createElement("span");
    box.replaceChildren(mark);
    const nav = pager(pages.length, (page) => carousel.go(page));
    const carousel = slider(pages, mark, { name: "headline-pages", change: (page) => nav.draw(page) });
    mark.remove();
    box.append(nav);
    nav.draw(0);
  }, () => {
    if (!signal.aborted) box.replaceChildren(empty("주요 뉴스를 불러오지 못했다."));
  });
  return box;
}

// 뉴스 상세를 이슈 화면과 같은 틀에 그린다. `data`는 `GET /articles/{ID}`의 기사이고, `ticker`가 있으면 종목 상세에서 연 기사다.
// 절 제목은 "종목별 뉴스"이고, 위쪽 한 줄 띠에는 기사 제목을 쓴다. 기사는 이슈 문단처럼 제목, 소제목 줄, 그림 묶음, 이슈 해설 말머리, 회차 시각, 본문을 차례로 쓴다.
// 소제목 줄은 제목 아래에 굵지 않은 동그라미 목록으로 쓰고, 소제목 줄 없이 올린 기사는 목록을 두지 않는다.
// 본문의 이슈 그래프 카드와 그림은 이슈 화면의 그리기 함수로 그린다.
// 기사 끝에는 들어온 목록의 앞 기사와 다음 기사로 가는 칸을 이슈 문단 끝의 칸과 같은 모양으로 둔다. 목록은 종목 상세에서 열었으면 그 종목의 최신 기사 `STOCK_NEWS`편이고,
// 아니면 그 기사가 있던 종목별 뉴스 목록의 장(주소의 `page`)이다. 칸을 누르면 진동을 내고 그 기사를 받아, 이슈를 넘길 때처럼 옆으로 옮겨 보이고 주소의 기사 ID를 바꾼다.
export const mount = (root, { data, ticker }) => newsDetail(data, ticker);
export const unmount = () => {};
function newsDetail(data, ticker) {
  const { signal } = life;
  const head = Object.assign(document.createElement("h2"), { className: "issues inside" });
  head.append(Object.assign(document.createElement("span"), { textContent: "종목별 뉴스" }));
  const box = Object.assign(document.createElement("div"), { className: "issue-box inside" });
  report.replaceChildren(head, box);
  backward(["news", "ticker"], "이슈");
  const bar = document.getElementById("issue-bar");
  const rename = (title) => {
    if (bar.textContent === title) return;
    bar.textContent = title;
    bar.animate([{ opacity: 0 }, { opacity: 1 }], { duration: motion.matches ? 0 : GLIDE });
  };
  let items = [], busy = false, current = null;
  const page = (article) => {
    const node = Object.assign(document.createElement("div"), { className: "issue-page" });
    node.append(Object.assign(document.createElement("h3"), { textContent: article.title }));
    if (article.subheads?.length) {
      const list = node.appendChild(Object.assign(document.createElement("ul"), { className: "subheads" }));
      list.append(...article.subheads.map((line) => Object.assign(document.createElement("li"), { textContent: line })));
    }
    // 뉴스 상세에는 본문 그림(첫 그림) 한 장만 싣는다.
    const shown = article.images.slice(0, 1);
    if (shown.length) {
      const figure = node.appendChild(Object.assign(document.createElement("figure"), { className: "issue-image" }));
      for (const { url, caption } of shown) {
        const photo = figure.appendChild(Object.assign(document.createElement("figure"), { className: "photo" }));
        const frame = photo.appendChild(Object.assign(document.createElement("div"), { className: "frame" }));
        frame.append(Object.assign(document.createElement("img"), { src: url, alt: "" }),
                     Object.assign(document.createElement("span"), { className: "ai", textContent: "AI 생성 이미지" }));
        if (caption) photo.append(Object.assign(document.createElement("figcaption"), { textContent: caption }));
      }
    }
    const lead = node.appendChild(document.createElement("h4"));
    lead.append(Object.assign(document.createElement("mark"), { textContent: "이슈 해설" }));
    node.append(Object.assign(document.createElement("p"), { className: "written", textContent: `${article.time.slice(0, 10).replaceAll("-", ".")} ${article.time.slice(11, 16)}` }));
    const mark = node.children.length;
    node.insertAdjacentHTML("beforeend", article.html);
    const body = [...node.children].slice(mark);
    marketed?.then((market) => { if (!signal.aborted) linkStocks(body, stockNames(market, article.tickers || [])); });
    node.addEventListener("click", (event) => {
      const stock = event.target.closest("button.stock");
      if (!stock) return;
      feelPress();
      visit(key, { stock: stock.dataset.stock });
    });
    node.querySelectorAll("figure.issue-chart[data-card]").forEach(issueChart);
    node.querySelectorAll("figure.issue-image").forEach(gallery);
    node.querySelectorAll("img").forEach((img) => img.addEventListener("click", () => viewer(img)));
    return node;
  };
  // 목록의 `at`번째 기사를 보이는 문단 끝에 앞 기사와 다음 기사로 가는 칸을 붙인다. 칸에는 그 기사의 첫 그림과 제목을 쓰고, 목록에 그림이 하나도 없으면 꼬리표와 제목만 쓴다.
  const neighbors = (node, at) => {
    if (at < 0) return;
    const framed = items.some((item) => item.image);
    const cell = (k, side) => {
      if (k < 0 || k >= items.length) return document.createElement("span");
      const button = Object.assign(document.createElement("button"), { type: "button", className: side });
      const tag = Object.assign(document.createElement("span"), { className: "tag", textContent: side === "prev" ? "‹ 이전" : "다음 ›" });
      if (framed) {
        const shot = button.appendChild(Object.assign(document.createElement("div"), { className: "shot" }));
        if (items[k].image) shot.append(Object.assign(document.createElement("img"), { className: "thumb", src: items[k].image, alt: "", loading: "lazy" }));
        shot.append(tag);
      } else {
        button.append(tag);
      }
      button.append(Object.assign(document.createElement("span"), { className: "title", textContent: items[k].title }));
      button.addEventListener("click", () => {
        if (busy) return;
        feelPress();
        step(at, k);
      });
      return button;
    };
    const nav = node.appendChild(Object.assign(document.createElement("nav"), { className: "step" }));
    nav.append(cell(at - 1, "prev"), cell(at + 1, "next"));
  };
  // 보고 있는 `i`번째 기사에서 `k`번째 기사로 넘긴다. 다음 기사는 오른쪽에서, 앞 기사는 왼쪽에서 들어오고, 동시에 화면을 맨 위로 옮긴다.
  const step = (i, k) => {
    busy = true;
    newsArticle(items[k].id).then((article) => {
      if (signal.aborted) return;
      const dir = k > i ? 1 : -1, out = current, shown = page(article);
      neighbors(shown, k);
      const params = new URLSearchParams(location.search);
      params.set("news", article.id);
      history.replaceState(history.state, "", `?${params}`);
      box.style.minHeight = `${box.offsetHeight}px`;
      box.classList.add("moving");
      out.classList.add("leaving");
      shown.classList.add("on");
      box.append(shown);
      current = shown;
      rename(article.title);
      const options = { duration: motion.matches ? 0 : GLIDE, easing: EASE };
      out.animate([{ transform: "none" }, { transform: `translateX(calc(${-dir} * (100vw + 10px)))` }], options);
      shown.animate([{ transform: `translateX(calc(${dir} * (100vw + 10px)))` }, { transform: "none" }], options);
      const cancel = () => { stop(); removeEventListener("touchstart", cancel); removeEventListener("wheel", cancel); };
      const stop = glide(scrollY, 0, (top) => scrollTo(0, top));
      addEventListener("touchstart", cancel, { passive: true });
      addEventListener("wheel", cancel, { passive: true });
      setTimeout(() => {
        out.remove();
        box.classList.remove("moving");
        box.style.minHeight = "";
        removeEventListener("touchstart", cancel);
        removeEventListener("wheel", cancel);
        busy = false;
      }, options.duration);
    }, () => { busy = false; });
  };
  current = page(data);
  current.classList.add("on");
  box.append(current);
  rename(data.title);
  (ticker ? newsList(`ticker=${encodeURIComponent(ticker)}&limit=${STOCK_NEWS}`) : newsPage(key.split("-")[1], Number(query.get("page")) || 1).then((value) => value.articles)).then((found) => {
    if (signal.aborted) return;
    items = found;
    neighbors(current, items.findIndex((item) => item.id === data.id));
  }, () => {});
}
