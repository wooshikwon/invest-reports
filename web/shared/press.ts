// @ts-nocheck
// 누를 수 있는 요소를 누르고 있는 동안 `pressed`를 달아 3% 줄인다. 손을 떼거나, 누른 채 화면을 밀어 누름이 취소되거나, 손가락이 요소 밖으로 나가면 뗀다.
// 누를 수 없게 막은 단추와 본문 속 단어표 용어는 줄이지 않는다.
export const PRESSABLE = "button:not(:disabled):not(.term):not(.stock), summary, .issue-list .pick, .gauge .evbox .t.go";
export let pressed = null;
export const unpress = () => { pressed?.classList.remove("pressed"); pressed = null; };
export function initPress() {
  addEventListener("pointerdown", (event) => {
    unpress();
    pressed = event.target.closest?.(PRESSABLE) || null;
    pressed?.classList.add("pressed");
  }, { capture: true, passive: true });
  ["pointerup", "pointercancel"].forEach((type) => addEventListener(type, unpress, { capture: true, passive: true }));
  addEventListener("pointerout", (event) => { if (pressed && !pressed.contains(event.relatedTarget)) unpress(); }, { capture: true, passive: true });
}
