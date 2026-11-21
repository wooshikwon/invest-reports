// @ts-nocheck
import { life } from "./route";
import { feelSlide } from "./telegram";
// 좌우로 넘기는 동작은 모두 `--glide`와 같은 0.3초, 같은 감속 곡선(cubic-bezier(.33, 1, .68, 1))으로 움직인다.
// `glide`는 값을 `from`에서 `to`까지 그 곡선으로 바꾸며 매 프레임 `set`을 부르고, 다 바꾸면 `done`을 부른다. 멈추는 함수를 돌려준다.
export const motion = matchMedia("(prefers-reduced-motion: reduce)");
// 화면 좌우 끝 24px 띠. 이 띠에서 시작한 가로 밀기는 바로가기 탭을 넘기므로(`jump`), 절 안의 넘기기는 받지 않는다.
export const atEdge = (x) => x < 24 || x > innerWidth - 24;
export const GLIDE = 300, EASE = "cubic-bezier(.33, 1, .68, 1)";
export const glide = (from, to, set, done) => {
  const begin = performance.now(), span = motion.matches ? 0 : GLIDE;
  let frame;
  const tick = (now) => {
    const t = span ? Math.min(1, Math.max(0, (now - begin) / span)) : 1;
    set(from + (to - from) * (1 - (1 - t) ** 3));
    if (t < 1) frame = requestAnimationFrame(tick);
    else done?.();
  };
  frame = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(frame);
};

// 슬라이드마다 노드 목록을 받아 좌우로 넘기는 묶음을 만들고 `after` 뒤에 둔다. 묶음 상자를 돌려준다.
// `fit`이면 넘기기가 멈춘 뒤와 슬라이드 높이가 바뀐 뒤 묶음 높이를 보고 있는 슬라이드에 맞춘다. `change`가 있으면 보고 있는
// 슬라이드가 바뀔 때마다 그 번호로 `change`를 부른다. `start`번 슬라이드부터 보여 준다.
// `feel`이면 보고 있는 슬라이드가 바뀔 때마다 선택 변경 진동을 낸다. 상자의 `go(i)`는 i번 슬라이드로 넘기고, `go(i, true)`는 넘기는 움직임 없이 바로 옮긴다.
// `lock(i)`이 알림 문구를 돌려주면 i번 슬라이드로 옮기지 못한다. 밀어서 넘기면 손을 뗀 뒤 보던 슬라이드로 튕겨 돌아오고, `go(i)`는 움직이지 않으며, 두 경우 모두 그 문구로 짧은 알림(`toast`)을 띄운다.
export function slider(slides, after, { fit = false, start = 0, change = null, name = "", area = null, feel = false, lock = null } = {}) {
  const box = document.createElement("div");
  box.className = ["carousel", fit && "fit", name].filter(Boolean).join(" ");
  box.innerHTML = '<div class="track"></div>';
  const track = box.querySelector(".track");
  slides.forEach((nodes) => {
    const slide = document.createElement("div");
    slide.className = "slide";
    nodes.forEach((node) => slide.appendChild(node));
    track.appendChild(slide);
  });
  after.after(box);
  const step = () => (slides.length > 1 ? track.children[1].offsetLeft - track.children[0].offsetLeft : 1);
  const current = () => Math.min(slides.length - 1, Math.max(0, Math.round(track.scrollLeft / step())));
  const fitHeight = () => { if (fit) track.style.height = `${track.children[current()].offsetHeight}px`; };
  // 손가락을 뗀 뒤 넘기기가 멈추면, 손을 댄 장에서 민 방향으로 지나간 장의 폭 1/5을 넘긴 만큼 장을 넘기고, 1/5을 넘기지 못하면
  // 손을 댄 장으로 맞춘다. 맞추는 동안 손을 다시 대면 맞추기를 그 위치에서 멈추고 새로 민 거리로 다시 정한다.
  let timer, shown = start, felt = start, from = null, touching = false, aligning = null, rest = start;
  // 장을 옮기는 동안에는 한 장씩 멈추기를 끄고 `glide`로 옮긴다. 켜 두면 브라우저가 매 프레임 가까운 장으로 끌어당긴다.
  const stop = () => { aligning?.(); aligning = null; track.style.scrollSnapType = ""; };
  const slide = (i) => {
    stop();
    track.style.scrollSnapType = "none";
    aligning = glide(track.scrollLeft, i * step(), (left) => (track.scrollLeft = left), () => { aligning = null; track.style.scrollSnapType = ""; });
  };
  track.addEventListener("touchstart", () => {
    touching = true;
    stop();
    from = current();
  }, { passive: true });
  const settle = () => {
    if (touching) return;
    let goal = target();
    const why = goal !== rest && lock?.(goal);
    if (why) {
      toast(why);
      goal = rest;
    } else rest = goal;
    if (Math.abs(track.scrollLeft - goal * step()) > 1) {
      from = goal;
      if (!aligning) slide(goal);
      return;
    }
    from = null;
    fitHeight();
  };
  const wait = () => { clearTimeout(timer); timer = setTimeout(settle, 150); };
  const release = () => { touching = false; wait(); };
  track.addEventListener("touchend", release, { passive: true });
  track.addEventListener("touchcancel", release, { passive: true });
  const target = () => {
    const at = track.scrollLeft / step(), base = from ?? current();
    if (Math.abs(at - base) < 0.2) return base;
    const goal = at > base ? Math.ceil(at - 0.2) : Math.floor(at + 0.2);
    return Math.min(slides.length - 1, Math.max(0, goal));
  };
  // `fit`이면 넘기는 동안 화면에 걸친 두 장 가운데 더 높은 장만큼 묶음 높이를 바로 늘려, 들어오는 장의 아래가 잘리지 않게 한다.
  // 줄이는 것은 넘기기가 멈춘 뒤에 한다.
  const reveal = () => {
    const at = track.scrollLeft / step(), last = slides.length - 1;
    const need = Math.max(...[Math.floor(at), Math.ceil(at)].map((i) => track.children[Math.min(last, Math.max(0, i))].offsetHeight));
    if (need <= track.offsetHeight) return;
    track.style.transition = "none";
    track.style.height = `${need}px`;
    track.offsetHeight;
    track.style.transition = "";
  };
  // 손을 뗀 뒤 브라우저의 장 맞추기가 장 위치 1.5px 안까지 오면 그 장 위치로 바로 옮겨 남은 미세한 움직임을 끝낸다.
  // iOS는 넘기기 묶음이 움직이는 동안 새 손가락을 묶음의 넘기기로 받으므로, 움직임이 남아 있으면 날짜 슬라이더 레버를 눌러도 레버가 잡히지 않는다.
  track.addEventListener("scroll", () => {
    if (!touching && !aligning) {
      const exact = current() * step(), gap = Math.abs(track.scrollLeft - exact);
      if (gap > 0 && gap <= 1.5) track.scrollLeft = exact;
    }
    if (fit) reveal();
    const now = current();
    if (feel && now !== felt) { felt = now; feelSlide(); }
    if (change && now !== shown) change((shown = now));
    wait();
  }, { passive: true });
  // 화면 폭이 바뀌거나 슬라이드 안의 표식·그림이 나중에 자리를 잡아 슬라이드 높이가 바뀌어도 묶음 높이를 다시 맞춘다.
  if (fit) {
    const watch = new ResizeObserver(fitHeight);
    [...track.children].forEach((slide) => watch.observe(slide));
    life.signal.addEventListener("abort", () => watch.disconnect());
  }
  box.go = (i, now = false) => {
    const goal = Math.min(slides.length - 1, Math.max(0, i));
    const why = goal !== rest && lock?.(goal);
    if (why) return toast(why);
    rest = goal;
    if (!now) return slide(goal);
    stop();
    track.scrollLeft = goal * step();
  };
  // 절 제목 `area`를 받으면 그 제목부터 다음 절 제목 앞까지(마지막 절이면 문서 끝까지)를 넘기기 영역으로 쓴다. 넘기기 묶음과 날짜 띠 밖에서
  // 가로로 40px 넘게, 세로 이동의 1.5배 넘게 밀고 손을 떼면 민 방향의 다음 장으로 넘긴다. 절이 가린 페이지에 있으면 넘기지 않는다.
  if (area) {
    let begin = null;
    document.addEventListener("touchstart", (event) => {
      begin = null;
      const { target, touches } = event;
      if (touches.length !== 1 || atEdge(touches[0].clientX) || area.closest(".page.off") || track.contains(target) || target.closest(".viewer, .help-card, .days, .back-edge, .frozen, input")) return;
      let next = area.nextElementSibling;
      while (next && next.tagName !== "H2") next = next.nextElementSibling;
      const y = touches[0].clientY;
      if (y < area.getBoundingClientRect().top || (next && y >= next.getBoundingClientRect().top)) return;
      begin = { x: touches[0].clientX, y };
    }, { passive: true, signal: life.signal });
    document.addEventListener("touchend", (event) => {
      if (!begin) return;
      const touch = event.changedTouches[0], dx = touch.clientX - begin.x, dy = touch.clientY - begin.y;
      begin = null;
      if (Math.abs(dx) > 40 && Math.abs(dx) > 1.5 * Math.abs(dy)) box.go(current() - Math.sign(dx));
    }, { passive: true, signal: life.signal });
  }
  // 리포트를 짓는 동안(`settling`)에는 첫 위치와 높이를 바로 재지 않고 다 지은 뒤 `settle`이 한 번에 잰다.
  // 짓는 도중에 재면 새로 넣은 노드를 그때마다 처음부터 배치해야 한다.
  const init = () => { if (start) track.scrollLeft = start * step(); return fit ? track.children[current()].offsetHeight : null; };
  const size = (height) => { if (height != null) track.style.height = `${height}px`; };
  if (settling) settling.sizes.push([init, size]);
  else size(init());
  if (change) later(() => change(start));
  return box;
}
// 화면 아래에 짧은 알림을 2.4초 동안 띄운다. 알림이 떠 있는 동안 다시 띄우면 문구만 바꾸고 시간을 새로 센다.
let note = null, noted = 0;
export const toast = (text) => {
  if (!note?.isConnected) {
    note = Object.assign(document.createElement("div"), { className: "toast" });
    note.setAttribute("role", "status");
    document.body.append(note);
  }
  note.textContent = text;
  clearTimeout(noted);
  noted = setTimeout(() => { note.remove(); note = null; }, 2400);
};
// `later(fn)`은 리포트를 짓는 동안이면 `fn`을 `settle` 때까지 미루고, 아니면 바로 부른다. 화면 위치를 재는 첫 표시에 쓴다.
export let settling = null;
export const settleStart = () => { settling = { sizes: [], after: [] }; };
export const later = (fn) => (settling ? settling.after.push(fn) : fn());
// 넘기기 묶음의 첫 위치를 모두 옮긴 뒤 높이를 모두 재고, 잰 높이를 모두 쓴 다음 미룬 첫 표시를 부른다. 읽기와 쓰기를 섞지 않으므로 배치는 몇 번만 한다.
export const settle = () => {
  if (!settling) return;
  const { sizes, after } = settling;
  settling = null;
  sizes.map(([init]) => init()).forEach((height, k) => sizes[k][1](height));
  after.forEach((fn) => fn());
};
