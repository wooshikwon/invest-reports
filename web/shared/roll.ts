// @ts-nocheck
import { EASE, motion } from "./motion";
// 큰 글씨 숫자 굴림. 1분 값이나 새 계좌 요약으로 큰 글씨 숫자가 바뀌면 바뀐 숫자 자리마다 이전 숫자에서 새 숫자까지 0~9를 차례로 굴린다.
// 값이 커졌으면 숫자가 위로, 작아졌으면 아래로 지나간다. 날짜 슬라이드·단추처럼 사용자가 고른 변경은 굴리지 않고 바로 바꾼다.
// `rolled(fn)`은 `fn`이 그리는 동안 바뀐 큰 글씨를 굴리게 한다. 받은 값으로 다시 그리는 곳(실시간 값, 계좌 요약)만 `rolled`로 감싼다.
// `roll(el, slot)`은 다 그린 큰 글씨 `el`을 앞에 그린 글씨와 견줘 굴린다. 다시 그릴 때 새 요소를 만드는 곳은 같은 자리에 같은 이름(`slot`)을 주어 앞 글씨를 이어 받는다.
// 굴림을 줄이도록 설정한 기기와 지수색 그라데이션 글씨(`.ink`)는 굴리지 않는다.
const ROLL = 700, named = new Map(), held = new WeakMap();
let rolling = false;
export const rolled = (fn) => {
  rolling = true;
  try { return fn(); } finally { rolling = false; }
};
// 글씨 마디의 모양(글씨를 뺀 HTML)과 글씨 마디 목록을 읽는다. 모양이 같은 두 글씨만 마디끼리 견준다.
const read = (el) => {
  const texts = [], walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  while (walk.nextNode()) texts.push(walk.currentNode);
  const words = texts.map((node) => node.data);
  texts.forEach((node) => (node.data = ""));
  const form = el.innerHTML;
  texts.forEach((node, i) => (node.data = words[i]));
  return { form, words, texts };
};
const number = (word) => {
  const found = word.replace(/,/g, "").replace("−", "-").match(/-?\d+(\.\d+)?/);
  return found ? +found[0] : NaN;
};
// 숫자 자리 하나. 새 숫자(`.d`)가 자리 폭과 높이를 잡고 숨어 있는 동안, 그 위에 이전 숫자부터 새 숫자까지 쌓은 띠(`.strip`)를 한 줄씩 옮긴다.
const digit = (from, to, up) => {
  const box = Object.assign(document.createElement("span"), { className: "roll" });
  const steps = [];
  for (let d = +from; ; d = (d + (up ? 1 : 9)) % 10) { steps.push(d); if (d === +to) break; }
  if (!up) steps.reverse();
  box.append(Object.assign(document.createElement("span"), { className: "d", textContent: to }));
  const strip = box.appendChild(Object.assign(document.createElement("span"), { className: "strip" }));
  steps.forEach((d) => strip.append(Object.assign(document.createElement("span"), { textContent: d })));
  const far = `translateY(${-(steps.length - 1) * 100}%)`;
  strip.animate([{ transform: up ? "none" : far }, { transform: up ? far : "none" }], { duration: ROLL, easing: EASE, fill: "forwards" })
    .finished.then(() => box.isConnected && box.replaceWith(to), () => {});
  return box;
};
// 글씨 마디 하나를 오른쪽 끝부터 견줘, 두 글씨 모두 숫자이고 다른 자리만 굴린다. 자리 수가 달라 새로 생긴 자리와 부호·기호는 바로 바꾼다.
const word = (node, before) => {
  const after = node.data, up = !(number(after) < number(before)), out = document.createDocumentFragment();
  let plain = "";
  [...after].forEach((ch, i) => {
    const old = before[before.length - after.length + i];
    if (/\d/.test(ch) && /\d/.test(old ?? "") && old !== ch) {
      if (plain) out.append(plain);
      plain = "";
      out.append(digit(old, ch, up));
    } else plain += ch;
  });
  if (plain) out.append(plain);
  node.replaceWith(out);
};
export const roll = (el, slot = el) => {
  const seen = typeof slot === "string" ? named : held, now = read(el), last = seen.get(slot);
  seen.set(slot, { form: now.form, words: now.words });
  if (!rolling || motion.matches || !last || last.form !== now.form || el.matches(".ink")) return;
  now.texts.forEach((node, i) => { if (node.data !== last.words[i]) word(node, last.words[i]); });
};
