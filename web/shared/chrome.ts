// @ts-nocheck
import { reportText } from "./data";
import { keep } from "./keep";
import { motion } from "./motion";
import { depth, key, life, reshow } from "./route";
import { feelPress } from "./telegram";
// 머리 상자가 화면 위에 붙어 있으면 `stuck`을 달고, 위쪽 높이의 유리(`#top-glass`)에 `off`를 달아 감춘다. 문서 맨 위에서는 달지 않는다.
// 붙었는지는 머리 상자 바로 위의 빈 띠(`#berth`)의 아래 끝이 머리 상자가 붙는 높이보다 위로 올라갔는지로 정한다. iOS는 코드가 화면을 옮긴 직후 붙는 상자의 위치를 옮기기 전 화면 기준으로 알려 주므로 머리 상자의 위치로 정하지 않는다.
export const masthead = document.getElementById("masthead");
export const ticker = document.getElementById("ticker");
export const berth = document.getElementById("berth");
export const topGlass = document.getElementById("top-glass");
export const stick = () => topGlass.classList.toggle("off", masthead.classList.toggle("stuck", scrollY > 0 && berth.getBoundingClientRect().bottom <= parseFloat(getComputedStyle(masthead).top) + .5));
// 붙어 있는 머리 상자에서 지수 단추 밖을 누르면 문서 맨 위로 올라간다.
const onMast = (event) => {
  if (!masthead.classList.contains("stuck") || event.target.closest(".index-pick")) return;
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
export const INDEX_TITLE = { nasdaq: "나스닥 100", biotech: "나스닥 바이오" };
export const paint = () => {
  const tint = INDEX[key.split("-")[1]];
  if (!tint) return;
  document.documentElement.style.setProperty("--index", tint[0]);
  document.documentElement.style.setProperty("--index-to", tint[1]);
};
// `listing`은 `r/index.json`이다. `index` 지수의 리포트 가운데 날짜가 가장 늦은 리포트의 키를 돌려주고, 그 지수의 리포트가 없으면 빈 글자를 돌려준다.
export const latest = (listing, index) => Object.keys(listing).filter((name) => listing[name].index === index)
  .sort((a, b) => listing[b].date.localeCompare(listing[a].date))[0] || "";
// 머리 상자 오른쪽 끝에 지수 단추를 단다. `listing`은 `r/index.json`이다. 단추를 누르면 고른 지수를 기기의 `index`에 남기고(`keep.ts`), 세로선을 반대쪽 끝으로 옮긴 뒤 다른 지수의 가장 늦은 리포트를
// 보던 페이지로 연다. 기록을 하나 더해 그 기록에 다음 깊이와 보던 페이지를 적고 그 자리에서 다시 그린다. 다른 지수의 리포트 본문은 단추를 단 1.5초 뒤 미리 받아 둔다.
// 리포트가 있는 지수가 하나뿐이면 단추를 달지 않는다.
export function indexPick(listing) {
  const index = key.split("-")[1];
  const order = Object.keys(INDEX).filter((name) => latest(listing, name));
  if (order.length !== 2 || !order.includes(index)) return;
  const other = order.find((name) => name !== index);
  const pick = masthead.appendChild(Object.assign(document.createElement("button"), {
    type: "button", className: `index-pick${index === order[1] ? " right" : ""}`, innerHTML: '<i class="fill"></i><i class="bar"></i>' }));
  pick.setAttribute("aria-label", `${INDEX_NAME[other]} 리포트 보기`);
  pick.style.cssText = `--left: ${INDEX[order[0]][0]}; --left-to: ${INDEX[order[0]][1]}; --right: ${INDEX[order[1]][0]}; --right-to: ${INDEX[order[1]][1]}`;
  const { signal } = life, target = latest(listing, other);
  pick.addEventListener("click", () => {
    if (pick.disabled) return;
    pick.disabled = true;
    feelPress();
    keep("index", other);
    pick.classList.toggle("right", other === order[1]);
    Promise.all([reportText(target).catch(() => {}), new Promise((done) => setTimeout(done, motion.matches ? 0 : 280))]).then(() => {
      if (signal.aborted) return;
      history.replaceState({ ...history.state, y: scrollY }, "");
      const params = new URLSearchParams(location.search);
      params.set("r", target);
      history.pushState({ depth: depth + 1, from: key, page: history.state?.page }, "", `?${params}`);
      reshow(false);
    });
  });
  setTimeout(() => signal.aborted || reportText(target).catch(() => {}), 1500);
}
