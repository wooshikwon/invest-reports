// @ts-nocheck
import { masthead } from "./chrome";
import { motion } from "./motion";
import { report } from "./route";
import { feelPress } from "./telegram";
// 이슈 제목의 방향 표식을 가려내 칠하고, 나머지 표식인 이벤트 중요도는 지운다. 중요도는 `build.py`가 소제목에 단 `data-level`로 그린다.
export const TONES = { "상승 요인": "tone-up", "하락 요인": "tone-down", "양방향": "tone-both" };
export function toneTags(scope) {
  scope.querySelectorAll("h3 code").forEach((tag) => {
    const tone = TONES[tag.textContent.trim()];
    if (tone) tag.classList.add(tone);
    else tag.remove();
  });
}
// 소제목의 방향 표식은 제목 끝으로 옮긴다.
export function trail(h3) {
  const codes = [...h3.querySelectorAll("code")];
  if (codes.length) {
    const tags = document.createElement("span");
    tags.className = "tags";
    tags.append(...codes);
    h3.append(Object.assign(document.createElement("span"), { className: "gap", textContent: " " }), tags);
  }
  h3.normalize();
  h3.childNodes.forEach((node) => { if (node.nodeType === 3) node.textContent = node.textContent.replace(/\s+$/, ""); });
}

// 말머리만 단 요약 소제목 바로 아래의 목록은 그 소제목의 결론이므로, 접기 전에 목록을 소제목 안으로 옮긴다. `first`는 훑기 시작할 노드다.
export function lift(first) {
  for (let node = first; node && node.tagName !== "H2"; node = node.nextElementSibling) {
    const list = node.nextElementSibling;
    if (node.tagName === "H3" && node.textContent.trim() === node.querySelector("mark")?.textContent.trim() && list?.tagName === "UL") {
      list.className = "heads";
      node.append(list);
    }
  }
}
export function heads(title) {
  lift([...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === title)?.nextElementSibling);
}
// `anchor` 바로 뒤에 `outlook.json`의 설명 절(현재 상태·주요 분기와 예측·종합 시나리오)을 접기 상자로 붙인다.
// `set(html, point)`은 절을 통째로 바꾼다. 절에는 설명 날짜를 `data-point`로 단다.
export function notes(anchor) {
  let nodes = [];
  return {
    set(html, point = "") {
      nodes.forEach((node) => node.remove());
      const temp = document.createElement("div");
      temp.innerHTML = html;
      toneTags(temp);
      lift(temp.firstElementChild);
      wrap([...temp.children].filter((node) => level(node) === 3), 3);
      temp.querySelectorAll("h3").forEach(trail);
      nodes = [...temp.children];
      nodes.forEach((node) => { node.dataset.point = point; });
      anchor.after(...nodes);
    },
  };
}
// 절 안의 `###`(depth 3)이나 `####`(depth 4) 소제목마다 접기 상자를 만든다. 말머리가 `keep`에 든 소제목은 접지 않는다.
export const level = (node) => (/^H\d$/.test(node.tagName) ? +node.tagName[1] : 9);
export function fold(title, depth = 3, keep = []) {
  const head = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === title);
  if (!head) return;
  const heads = [];
  for (let node = head.nextElementSibling; node && node.tagName !== "H2"; node = node.nextElementSibling) {
    if (level(node) === depth && !keep.includes(node.querySelector("mark")?.textContent.trim())) heads.push(node);
  }
  wrap(heads, depth);
}
// 소제목마다 소제목만 보이는 접기 상자를 만들고, 같은 깊이나 더 얕은 다음 소제목 앞까지의 노드를 그 안에 넣는다.
export function wrap(heads, depth) {
  heads.forEach((h3) => {
    const box = document.createElement("details");
    box.className = "fold";
    const summary = document.createElement("summary");
    h3.before(box);
    let node = h3.nextElementSibling;
    summary.appendChild(h3);
    const body = Object.assign(document.createElement("div"), { className: "body" });
    box.append(summary, body);
    while (node && level(node) > depth) {
      const next = node.nextElementSibling;
      body.appendChild(node);
      node = next;
    }
    summary.addEventListener("click", (event) => {
      event.preventDefault();
      setFold(box, !(box.want ?? box.open));
    });
    // 펼친 내용을 누르면 접는다. 그림과 링크를 누른 경우, 누른 채 10px 넘게 움직인 경우, 글자를 고른 경우는 접지 않는다.
    // 소제목이 머리 상자 띠 밑으로 지나가 있으면 접기 전에 소제목을 띠 바로 아래로 옮긴다.
    let down = null;
    body.addEventListener("pointerdown", (event) => { down = [event.clientX, event.clientY]; }, { passive: true });
    body.addEventListener("click", (event) => {
      const moved = down && Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 10;
      down = null;
      if (moved || event.target.closest("img, a, button") || String(getSelection()).trim()) return;
      const cover = masthead.getBoundingClientRect().bottom + 9, above = summary.getBoundingClientRect().top - cover;
      if (above < 0) scrollBy({ top: above, behavior: motion.matches ? "instant" : "smooth" });
      setFold(box, false);
    });
  });
}
// 접기 상자의 내용 높이와 투명도를 지금 값에서 목표 값까지 이어서 바꾼다. 움직이는 중에 다시 누르면 그 자리에서 방향을 바꾸고,
// 다 닫힌 뒤에야 상자를 닫는다. 넘기는 묶음 안에서는 움직이는 동안 묶음 높이가 매 프레임 내용 높이를 따라가게 한다.
export function setFold(box, open) {
  if ((box.want ?? box.open) === open) return;
  if (open) feelPress();
  box.want = open;
  const body = box.lastElementChild, carousel = box.closest(".carousel.fit");
  const start = box.open ? body.getBoundingClientRect().height : 0;
  box.anim?.cancel();
  box.open = true;
  const full = body.scrollHeight, end = open ? full : 0;
  body.style.overflow = "hidden";
  carousel?.classList.add("folding");
  const anim = (box.anim = body.animate(
    [{ height: `${start}px`, opacity: full ? start / full : 1 }, { height: `${end}px`, opacity: open ? 1 : 0 }],
    { duration: motion.matches ? 0 : 280, easing: "cubic-bezier(.25, .8, .25, 1)" },
  ));
  anim.onfinish = () => {
    box.anim = null;
    body.style.overflow = "";
    if (!open) box.open = false;
    carousel?.classList.remove("folding");
  };
}
