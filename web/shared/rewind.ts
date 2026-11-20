// @ts-nocheck
import { key } from "./route";
import { feelPress, feelSlide } from "./telegram";
// 되감기 슬라이더가 보여 주는 날짜 수와, 리포트 날짜 `date`에서 그 앞 90일의 첫날을 0으로 센 `day`의 자리.
// "기준 날짜 이동" 단추의 아이콘이다. 시계 둘레의 화살이 10시에서 반시계 방향으로 나아간다.
// 꺾쇠의 두 날개는 90°로 벌어지고, 두 날개 끝이 시계 둘레에서 같은 거리만큼 안팎으로 떨어지도록 꺾쇠를 돌려 둔다.
export const REWIND_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.07 8A8 8 0 1 1 4.48 14.74"/><path d="M8.44 7.64L5.07 8L4.71 4.63"/>'
  + '<path d="M12 8v4.2l2.8 1.8"/></svg>';
export const REWIND_SPAN = 90, rewindOffset = (day, date) => Math.round((Date.parse(day) - Date.parse(date)) / 864e5) + REWIND_SPAN;

// `box` 끝에 지난 판단 날짜를 고르는 슬라이더를 둔다. `days`는 고를 수 있는 날짜(오름차순)이고 `start`번 날짜에서 시작한다.
// 슬라이더는 리포트 날짜와 그 앞 90일을 늘 같은 폭으로 보여 주고, 레버는 `days`의 날짜에만 선다. 레버가 선 날짜가 정해질 때마다 그 번호로 `pick`을 부른다.
// 슬라이더는 "기준 날짜 이동" 단추를 누르면 열리고, 레버 밖의 막대를 누르면 닫힌다. 날짜는 레버를 잡고 옮길 때만 바뀌고, 닫아도 고른 날짜는 그대로 둔다.
export function dial(box, date, days, start, pick) {
  const offset = (day) => rewindOffset(day, date);
  const control = document.createElement("div");
  control.className = "rewind shut";
  control.innerHTML = `<input type="range" min="0" max="${REWIND_SPAN}" step="1" value="${REWIND_SPAN}" tabindex="-1"><span></span><i class="bar"></i><i class="grip"></i>`
    + `<button type="button" class="open">${REWIND_ICON}기준 날짜 이동</button>`;
  const [range, shown, bar, grip, open] = control.children;
  const toggle = (shut) => () => { feelPress(); control.classList.toggle("shut", shut); };
  open.addEventListener("click", toggle(false));
  bar.addEventListener("click", toggle(true));
  const first = offset(days[0]);
  range.style.setProperty("--from", first / REWIND_SPAN);
  let wanted = start;
  // 레버를 잡고 있는 동안 레버 위에 날짜 말풍선을 띄운다. 레버 폭 18px를 빼고 남은 폭에서 레버 중심을 찾고,
  // 말풍선은 슬라이더 폭 안에 두되 꼬리는 레버 중심을 가리킨다.
  const show = (i) => {
    wanted = i;
    range.value = offset(days[i]);
    shown.textContent = `${days[i].slice(5, 7)}/${days[i].slice(8, 10)}`;
    const half = shown.offsetWidth / 2, at = 9 + offset(days[i]) / REWIND_SPAN * (range.clientWidth - 18);
    shown.style.left = `${Math.min(range.clientWidth - half, Math.max(half, at))}px`;
    shown.style.setProperty("--tail", `${at - Math.min(range.clientWidth - half, Math.max(half, at))}px`);
    grip.style.left = `${at}px`;
    pick(i);
  };
  // 레버를 첫 날짜보다 왼쪽으로 옮기면 첫 날짜에 세우고, 그 밖에는 가장 가까운 날짜로 붙인다. 붙는 날짜가 바뀔 때마다 진동을 낸다.
  const nearest = () => {
    const at = Math.max(first, +range.value);
    return days.reduce((best, day, i) => (Math.abs(offset(day) - at) <= Math.abs(offset(days[best]) - at) ? i : best), 0);
  };
  range.addEventListener("input", () => {
    const i = nearest();
    if (i !== wanted) feelSlide();
    show(i);
  });
  const hold = (on) => () => { control.classList.toggle("held", on); if (on) show(nearest()); };
  // 레버 칸을 누르면 누른 자리와 레버 중심의 거리(`grab`)를 기억하고, 손가락이 움직인 만큼 레버를 옮긴다.
  let grab = 0;
  const lever = () => 9 + range.value / REWIND_SPAN * (range.clientWidth - 18);
  grip.addEventListener("pointerdown", (event) => {
    grip.setPointerCapture(event.pointerId);
    grab = event.clientX - range.getBoundingClientRect().left - lever();
    hold(true)();
  });
  grip.addEventListener("pointermove", (event) => {
    if (!grip.hasPointerCapture(event.pointerId)) return;
    const x = event.clientX - range.getBoundingClientRect().left - grab;
    range.value = Math.round(Math.min(1, Math.max(0, (x - 9) / (range.clientWidth - 18))) * REWIND_SPAN);
    range.dispatchEvent(new Event("input"));
  });
  ["pointerup", "pointercancel"].forEach((type) => grip.addEventListener(type, () => { hold(false)(); }));
  box.appendChild(control);
  show(start);
}

// 지수의 되감기 카드 자료(build.py `r/rewind-{지수}/cards.json`)의 판단 목록이다. 리포트 그림 카드와 내 자산 그림 카드가 함께 쓰므로 받은 목록은 화면을 닫을 때까지 두고,
// 받지 못하면 다음에 다시 받는다.
export const rewinds = {};
export const rewindFrames = (index) => (rewinds[index] ??= fetch(`r/rewind-${index}/cards.json`, { cache: "no-cache" })
  .then((r) => (r.ok ? r.json() : Promise.reject())).then((data) => data.frames).catch(() => { delete rewinds[index]; return null; }));
// 그림 카드 묶음 아래에 지난 판단 날짜로 되감는 슬라이더를 둔다(build.py `r/rewind-{지수}/cards.json`). 리포트 날짜와 그 앞 날짜만
// 고를 수 있고, 리포트 날짜가 되감기 범위에 없으면 슬라이더를 두지 않는다. 날짜를 고르면 그날 판단으로 카드를 다시 그린다.
// `view.pending()`이 날짜 지점을 주면 그 지점의 판단이 아직 없으므로, 슬라이더 끝에 판단 없는 날짜(`pending: true`인 프레임, 가장 늦은 판단의 값에 날짜 지점 `point`만 바꾼 값이다)를 하나 더 두고 그 날짜에서 시작한다.
// 사용자가 레버를 옮기기 전에는 `update()`가 늘 끝 날짜(판단 없는 날짜가 있으면 그 날짜)에 선다. 돌려준 `update()`는 `view.pending()`이 바뀐 뒤 슬라이더를 다시 짓는다. 고른 날짜는 그대로 둔다.
export function cardRewind(box, date, set, view) {
  const at = (frame) => (frame.pending ? frame.point : frame.day);
  let frames = null, touched = false, drawn = 0, raf = 0, latest = null, wait = null;
  const draw = () => {
    raf = 0;
    set.show(frames[drawn]);
    if (frames[drawn].pending) box.go(0);
  };
  const build = (keep) => {
    box.querySelector(".rewind")?.remove();
    wait = view.pending();
    const top = wait ?? date;
    const list = all.filter((frame) => frame.day <= date && rewindOffset(frame.day, top) >= 0);
    frames = wait ? [...list, { ...latest, point: wait, pending: true }] : list;
    const found = frames.findIndex((frame) => at(frame) === keep);
    drawn = found < 0 ? frames.length - 1 : found;
    set.show(frames[drawn]);
    dial(box, top, frames.map(at), drawn, (i) => {
      if (i === drawn) return;
      touched = true;
      drawn = i;
      if (!raf) raf = requestAnimationFrame(draw);
    });
  };
  let all = null;
  rewindFrames(key.split("-")[1]).then((got) => {
    if (!got) return;
    all = got;
    latest = all.find((frame) => frame.day === date);
    if (latest) build(null);
  }).catch(() => {});
  return { update() { if (frames && view.pending() !== wait) build(touched ? at(frames[drawn]) : null); } };
}
