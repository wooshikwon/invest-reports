// @ts-nocheck
import { INDEX } from "./chrome";
import { roll } from "./roll";
import { key } from "./route";
import { shape } from "./svg";
// 폭 `W`인 그림 카드의 지수색 그라데이션 칠을 돌려준다. 그라데이션은 `--index-ink`와 같이 지수 옆 색상에서 지수색으로 100도 방향으로 넘어가고,
// 카드 폭의 −25%와 85%에 두 색을 둔다. 카드마다 다시 그릴 때 그림을 비우므로 그라데이션은 문서에 한 번 둔다.
export function indexInk(W) {
  if (!document.getElementById("index-ink")) {
    const [hue, hueTo] = INDEX[key.split("-")[1]] || INDEX.nasdaq;
    const defs = document.body.appendChild(shape("svg", { width: 0, height: 0, "aria-hidden": "true", style: "position: absolute" }));
    const rise = Math.tan(10 * Math.PI / 180) * W;
    const ramp = defs.appendChild(shape("linearGradient", { id: "index-ink", gradientUnits: "userSpaceOnUse", x1: -0.25 * W, y1: -0.25 * rise, x2: 0.85 * W, y2: 0.85 * rise }));
    ramp.append(shape("stop", { offset: 0, "stop-color": hueTo }), shape("stop", { offset: 1, "stop-color": hue }));
  }
  return "url(#index-ink)";
}
// 그림 카드 틀. 위 줄 맥락 글씨, 가운데 줄 값과 상태, 폭 `W`·높이 `H`의 그림 칸, 그림 아래 줄을 둔다.
// 맥락 글씨와 값은 글씨나 노드 목록으로 받고, 상태 글씨가 없으면 상태 칸을 숨긴다.
// 맥락 글씨를 따로 받으면 카드를 만들 때의 맥락 글씨 대신 쓴다. 값은 `roll`로 굴리고, 다시 그릴 때마다 카드를 새로 만드는 곳은 자리 이름(`slot`)을 준다.
export function gaugeCard(ctx, W, H, slot) {
  const box = Object.assign(document.createElement("div"), { className: "gauge summary" });
  box.innerHTML = '<div class="top"><span class="ctx"></span></div><div class="val"><b class="ink"></b><span class="state"><i></i><span></span></span></div><div class="fig"></div><div class="foot"></div>';
  const [label, value, state] = [box.querySelector(".ctx"), box.querySelector(".val b"), box.querySelector(".state")];
  const svg = box.querySelector(".fig").appendChild(shape("svg", { viewBox: `0 0 ${W} ${H}` }));
  const head = (text, big, context = ctx) => {
    label.replaceChildren(...[context].flat());
    value.replaceChildren(...[big].flat());
    roll(value, slot);
    state.querySelector("span").textContent = text;
    state.hidden = !text;
  };
  return { box, svg, head, value, foot: box.querySelector(".foot") };
}
