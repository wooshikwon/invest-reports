// @ts-nocheck
import { reportText } from "./data";
import { keep } from "./keep";
import { motion } from "./motion";
import { depth, key, life, reshow, visit } from "./route";
import { feelPress, tg } from "./telegram";
// 머리 상자가 화면 위에 붙어 있으면 `stuck`을 달고, 위쪽 높이의 유리(`#top-glass`)에 `off`를 달아 감춘다. 문서 맨 위에서는 달지 않는다.
// 붙었는지는 머리 상자 바로 위의 빈 띠(`#berth`)의 아래 끝이 머리 상자가 붙는 높이보다 위로 올라갔는지로 정한다. iOS는 코드가 화면을 옮긴 직후 붙는 상자의 위치를 옮기기 전 화면 기준으로 알려 주므로 머리 상자의 위치로 정하지 않는다.
export const masthead = document.getElementById("masthead");
export const ticker = document.getElementById("ticker");
// 머리 상자 왼쪽 끝의 페이지 이름. 바로가기 알약에서 연 페이지의 이름(자산, 지수, 이슈, 시장)을 쓴다.
export const pageName = document.getElementById("page-name");
export const berth = document.getElementById("berth");
export const topGlass = document.getElementById("top-glass");
export const stick = () => topGlass.classList.toggle("off", masthead.classList.toggle("stuck", scrollY > 0 && berth.getBoundingClientRect().bottom <= parseFloat(getComputedStyle(masthead).top) + .5));
// 붙어 있는 머리 상자에서 지수 단추와 지수 메뉴 밖을 누르면 문서 맨 위로 올라간다.
const onMast = (event) => {
  if (!masthead.classList.contains("stuck") || event.target.closest(".index-pick, .index-menu")) return;
  feelPress();
  scrollTo({ top: 0, behavior: motion.matches ? "instant" : "smooth" });
};
// 본문의 단어표 용어(build.py가 `button.term`으로 감싼 자리)를 누르면 용어 아래에 대표 표기와 설명을 담은 말풍선을 띄운다. 아래 자리가 모자라면 위에 띄운다.
// 히스토리로 바꿔 넣은 이슈 문단의 용어도 같은 말풍선을 쓰도록 문서 전체에서 누르기를 받는다. 요약 소제목 안의 용어를 눌러도 접기 상자는 그대로 둔다. 같은 용어를 다시 누르거나, 말풍선 밖을 누르거나, 화면을 밀면 닫는다.
// 말풍선 밖을 누른 손길은 말풍선만 닫고 그 아래 접힌 본문·링크에는 클릭을 넘기지 않는다.
export let gloss = null;
export const unglos = () => { gloss?.term.classList.remove("on"); gloss?.remove(); gloss = null; };
const onTerm = (event) => {
  const term = event.target.closest("button.term");
  if (!term) return;
  event.stopPropagation();
  event.preventDefault();
  const again = gloss?.term === term;
  unglos();
  if (again) return;
  feelPress();
  gloss = Object.assign(document.createElement("div"), { className: "bubble gloss below" });
  gloss.term = term;
  gloss.append(Object.assign(document.createElement("b"), { textContent: term.dataset.term }),
               Object.assign(document.createElement("p"), { textContent: term.dataset.desc }));
  document.body.append(gloss);
  term.classList.add("on");
  // 용어가 두 줄에 걸치면 누른 줄의 상자를 기준으로 삼는다. 화면 양 끝에서 12px 안쪽에 두고, 꼬리는 용어 가운데를 가리킨다.
  const at = [...term.getClientRects()].find((r) => event.clientY >= r.top && event.clientY <= r.bottom) || term.getBoundingClientRect();
  const size = { width: gloss.offsetWidth, height: gloss.offsetHeight };
  const left = Math.min(innerWidth - 12 - size.width, Math.max(12, at.left + at.width / 2 - size.width / 2));
  const below = at.bottom + 10 + size.height <= innerHeight - 12 || at.top - size.height - 10 < masthead.getBoundingClientRect().bottom;
  gloss.classList.toggle("below", below);
  gloss.style.left = `${left + scrollX}px`;
  gloss.style.top = `${(below ? at.bottom + 10 : at.top - size.height - 10) + scrollY}px`;
  gloss.style.setProperty("--tail", `${Math.min(size.width - 18, Math.max(18, at.left + at.width / 2 - left))}px`);
};
export let hush = false;
export function initChrome() {
  addEventListener("scroll", stick, { passive: true });
  masthead.addEventListener("click", onMast);
  document.addEventListener("click", onTerm, true);
  addEventListener("pointerdown", (event) => {
    hush = !!gloss && !gloss.contains(event.target) && !event.target.closest("button.term");
    if (hush) unglos();
  }, { capture: true, passive: true });
  addEventListener("click", (event) => { if (!hush) return; hush = false; event.stopPropagation(); event.preventDefault(); }, true);
  addEventListener("scroll", () => { if (gloss) unglos(); }, { passive: true });
}
// 소제목 위 말머리와 이벤트 시각은 지수마다 리포트 그림의 판단 색 계열에서 채도를 낮춘 색으로 쓴다(conviction_chart.py JUDGMENT_COLORS).
// 두 번째 색은 그라데이션이 끝나는 색으로, 지수색에서 색상환을 따라 보라 쪽으로 조금 옮긴 색이다.
export const INDEX = { nasdaq: ["#8FBCE6", "#AFA6EC"], biotech: ["#AE9CE6", "#E09DCB"] };
// 그림 카드가 없는 지수와 예측 절 설명의 첫 항목, 머리 상자 기준 가격, 시장 페이지의 한 눈에 보기 절 제목에 쓰는 리포트 지수의 이름이다.
// build.py card_scale이 카드 가격을 지수 눈금으로 늘려 적으므로 머리 상자 가격은 시장 탭의 같은 이름 지수 값과 같다.
export const INDEX_NAME = { nasdaq: "나스닥", biotech: "바이오" };
// 주가 카드의 이름 줄에 쓰는 지수 이름이다.
export const INDEX_TITLE = { nasdaq: "나스닥 100", biotech: "나스닥 바이오테크" };
export const paint = () => {
  const tint = INDEX[key.split("-")[1]];
  if (!tint) return;
  document.documentElement.style.setProperty("--index", tint[0]);
  document.documentElement.style.setProperty("--index-to", tint[1]);
};
// `listing`은 `r/index.json`이다. `index` 지수의 리포트 가운데 날짜가 가장 늦은 리포트의 키를 돌려주고, 그 지수의 리포트가 없으면 빈 글자를 돌려준다.
export const latest = (listing, index) => Object.keys(listing).filter((name) => listing[name].index === index)
  .sort((a, b) => listing[b].date.localeCompare(listing[a].date))[0] || "";
// 머리 상자 오른쪽 끝에 지수 단추를 단다. `listing`은 `r/index.json`이다. 단추는 보고 있는 리포트 지수의 지수색 점, 지수 이름, 아래 꺾쇠를 담은 알약이고,
// 누르면 단추 아래에 지수 메뉴를 펼친다. 메뉴는 리포트가 있는 지수마다 지수색 점, 지수 이름, 지수 전체 이름을 한 줄에 쓰고, 보고 있는 지수 줄에 체크를 단다.
// 다른 지수 줄을 누르면 고른 지수를 기기의 `index`에 남기고(`keep.ts`) 그 지수의 가장 늦은 리포트를 보던 페이지로 연다. 기록을 하나 더해 그 기록에 다음 깊이와
// 보던 페이지를 적고 그 자리에서 다시 그린다. 보고 있는 지수 줄이나 메뉴 밖을 누르면 메뉴를 닫는다. 다른 지수의 리포트 본문은 단추를 단 1.5초 뒤 미리 받아 둔다.
// 리포트가 있는 지수가 하나뿐이면 단추를 달지 않는다.
const CHEVRON = '<svg width="10" height="6" viewBox="0 0 10 6" aria-hidden="true"><path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const CHECK = '<svg class="check" width="14" height="11" viewBox="0 0 14 11" aria-hidden="true"><path d="M1.5 5.5l4 4 7-8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const dot = (name) => Object.assign(document.createElement("span"), { className: "dot", style: `background: linear-gradient(135deg, ${INDEX[name][0]}, ${INDEX[name][1]})` });
export function indexPick(listing) {
  const index = key.split("-")[1];
  const order = Object.keys(INDEX).filter((name) => latest(listing, name));
  if (order.length !== 2 || !order.includes(index)) return;
  const other = order.find((name) => name !== index);
  const pick = masthead.appendChild(Object.assign(document.createElement("button"), { type: "button", className: "index-pick" }));
  pick.append(dot(index), Object.assign(document.createElement("span"), { textContent: INDEX_NAME[index] }));
  pick.insertAdjacentHTML("beforeend", CHEVRON);
  pick.setAttribute("aria-haspopup", "menu");
  pick.setAttribute("aria-expanded", "false");
  pick.setAttribute("aria-label", `지수 고르기, 지금 ${INDEX_NAME[index]}`);
  const menu = masthead.appendChild(Object.assign(document.createElement("div"), { className: "index-menu", hidden: true }));
  menu.setAttribute("role", "menu");
  const { signal } = life, target = latest(listing, other);
  const close = () => { menu.hidden = true; pick.setAttribute("aria-expanded", "false"); };
  for (const name of order) {
    const item = menu.appendChild(Object.assign(document.createElement("button"), { type: "button", className: name === index ? "item on" : "item" }));
    item.setAttribute("role", "menuitem");
    item.append(dot(name), Object.assign(document.createElement("span"), { className: "name", textContent: INDEX_NAME[name] }),
                Object.assign(document.createElement("span"), { className: "sub", textContent: INDEX_TITLE[name] }));
    if (name === index) item.insertAdjacentHTML("beforeend", CHECK);
    item.addEventListener("click", () => {
      feelPress();
      if (name === index) return close();
      if (pick.disabled) return;
      pick.disabled = true;
      keep("index", other);
      close();
      reportText(target).catch(() => {}).then(() => {
        if (signal.aborted) return;
        history.replaceState({ ...history.state, y: scrollY }, "");
        const params = new URLSearchParams(location.search);
        params.set("r", target);
        history.pushState({ depth: depth + 1, from: key, page: history.state?.page }, "", `?${params}`);
        reshow(false);
      });
    });
  }
  pick.addEventListener("click", () => {
    if (pick.disabled) return;
    feelPress();
    menu.hidden = !menu.hidden;
    pick.setAttribute("aria-expanded", String(!menu.hidden));
  });
  document.addEventListener("pointerdown", (event) => { if (!menu.hidden && !event.target.closest(".index-pick, .index-menu")) close(); }, { capture: true, signal });
  addEventListener("scroll", () => menu.hidden || close(), { passive: true, signal });
  setTimeout(() => signal.aborted || reportText(target).catch(() => {}), 1500);
}
// 텔레그램 앱 안에서 연 리포트 화면은 머리 상자 오른쪽 끝, 지수 단추 오른쪽에 알림 단추를 단다. 누르면 알림 설정 화면(`?alerts=1`, `pages/alerts.ts`)을 연다.
// 알림은 사람마다 봇 대화창으로 오므로 브라우저로 연 화면에는 단추를 달지 않는다.
export function alertBell() {
  if (!(tg && tg.initData)) return;
  const bell = masthead.appendChild(Object.assign(document.createElement("button"), { type: "button", className: "alert-bell",
    innerHTML: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2.6a5 5 0 0 0-5 5v3.2L3.6 13.6h12.8L15 10.8V7.6a5 5 0 0 0-5-5Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8 16.2a2.1 2.1 0 0 0 4 0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>' }));
  bell.setAttribute("aria-label", "알림 설정");
  masthead.classList.add("belled");
  bell.addEventListener("click", () => {
    feelPress();
    visit(key, { alerts: "1" });
  });
}
