// @ts-nocheck
import { depth, from, key, life } from "./route";
import { feelPress, feelSlide } from "./telegram";
// 이슈 화면과 종목 상세, 뉴스 상세의 왼쪽 아래에 뒤로가기 단추를 띄운다.
// 주소로 바로 연 화면의 단추는 주소에서 `names`를 지우고 리포트 화면의 `page` 페이지를 맨 위부터 연다.
export function backward(names, page) {
  const { signal } = life;
  const back = document.body.appendChild(document.createElement("button"));
  back.className = "back";
  signal.addEventListener("abort", () => back.remove(), { once: true });
  back.innerHTML = '<svg width="12" height="20" viewBox="0 0 12 20" aria-hidden="true"><path d="M10 2 2 10l8 8" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  // 단추 이름은 어디서 열었든 "뒤로가기"이고, 돌아가는 곳은 이 화면을 연 곳이다. 이슈 화면 안에서 다른 이슈로 넘겨도 돌아가는 곳은 바뀌지 않는다.
  back.setAttribute("aria-label", "뒤로가기");
  // 리포트 화면(이슈 목록이나 종목 뉴스 목록, 이벤트 캘린더, 지수 지도 말풍선의 "자세히 보기")에서 연 화면의 단추는 뒤로 가서, 떠날 때의 리포트 화면(페이지와 캘린더 날짜, 화면 위치)으로 돌아간다.
  // 종목 상세의 주요뉴스에서 연 뉴스 상세의 단추도 뒤로 가서 그 종목 상세로 돌아간다.
  // 주소로 바로 연 이슈 화면의 단추는 이슈 화면 기록을 이 이슈를 담은 리포트 화면으로 바꾸며 이슈 페이지를 맨 위부터 연다(`land`). 종목 상세는 시장 페이지를, 뉴스 상세는 이슈 페이지를 연다. 깊이는 그대로 넘긴다.
  back.addEventListener("click", () => {
    feelPress();
    if (depth > 0 && from) return history.back();
    sessionStorage.setItem("land", `${key} ${page}`);
    if (depth > 0) sessionStorage.setItem("depth", depth);
    const params = new URLSearchParams(location.search);
    names.forEach((name) => params.delete(name));
    location.replace(`?${params}`);
  });
  // 화면 어디서든 오른쪽으로 60px 넘게, 세로 이동의 1.5배 넘게 밀고 손을 떼면 뒤로가기 단추를 누른 것과 같다.
  // 그림을 크게 본 화면과 설명 상자, 넘기기 묶음 안에서 민 것은 세지 않는다.
  let swipe = null;
  document.addEventListener("touchstart", (event) => {
    const { target, touches } = event;
    swipe = touches.length === 1 && !target.closest(".viewer, .help-card, .carousel") ? { x: touches[0].clientX, y: touches[0].clientY } : null;
  }, { passive: true, signal });
  document.addEventListener("touchend", (event) => {
    if (!swipe) return;
    const touch = event.changedTouches[0], dx = touch.clientX - swipe.x, dy = touch.clientY - swipe.y;
    swipe = null;
    if (dx > 60 && dx > 1.5 * Math.abs(dy)) back.click();
  }, { passive: true, signal });
  // 화면이 내용의 아래쪽으로 8px 넘게 내려가면 단추를 감추고, 위쪽으로 8px 넘게 올라가면 다시 띄운다.
  // 올라간 거리는 마지막으로 올라간 뒤 가장 깊이 내려간 위치부터, 내려간 거리는 마지막으로 내려간 뒤 가장 얕게 올라간 위치부터 잰다. 문서 양 끝을 넘어 튕긴 위치는 문서 끝으로 센다.
  let deepest = scrollY, shallowest = scrollY;
  addEventListener("scroll", () => {
    const y = Math.max(0, Math.min(scrollY, document.documentElement.scrollHeight - innerHeight));
    deepest = Math.max(deepest, y);
    shallowest = Math.min(shallowest, y);
    if (y < deepest - 8) {
      deepest = y;
      back.classList.remove("hide");
    }
    if (y > shallowest + 8) {
      shallowest = y;
      back.classList.add("hide");
    }
  }, { passive: true, signal });
}

// 미니 앱 안에서 다른 리포트로 옮겨 온 리포트 화면(`depth`가 0보다 크면)은 화면 왼쪽 끝 18px 띠에서 오른쪽으로 밀어 앞 화면으로 돌아간다.
// 이슈 화면과 종목 상세, 거래 내역 화면, 뉴스 상세는 이 띠를 두지 않고, 화면 어디서든 오른쪽으로 밀면 뒤로가기 단추를 누른 것과 같다.
// 띠는 손가락이 처음 6px 움직인 방향으로 할 일을 정한다. 가로로 움직인 거리가 세로의 0.6배 이상이면 뒤로 가기로 받고 페이지 스크롤을 막는다.
// 막지 않으면 스크롤할 여지가 있는 본문 가운데에서 손가락이 조금만 비스듬히 움직여도 브라우저가 스크롤을 시작해 밀기를 끊는다.
// 그보다 세로로 움직이면 스크롤을 브라우저에 맡기고 그 손짓은 더 보지 않는다. 띠를 누르고 있는 동안은 뿌리에 `edging`을 달아 띠 아래 스크롤 상자의 스크롤을 멈춘다. 미는 동안 손가락 높이에 뒤로 가기 원이 따라 나오고, 80px을 넘기면 원이 밝아지며
// 선택 변경 진동을 낸다. 80px을 넘긴 채 손을 떼면 앞 페이지로 돌아가고, 못 넘기면 원을 거둔다. 움직이지 않고 누른 곳은 띠 아래 요소를 누른 것으로 넘긴다.
export function backEdge() {
  const edge = Object.assign(document.createElement("div"), { className: "back-edge" });
  const ring = Object.assign(document.createElement("div"), { className: "back-ring" });
  ring.innerHTML = '<svg width="10" height="16" viewBox="0 0 10 16" aria-hidden="true"><path d="M8 2L2 8l6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  document.body.append(edge, ring);
  const REACH = 80;
  let start = null, ready = false;
  const place = (dx, y) => {
    const pull = Math.min(dx, REACH * 1.6);
    ring.style.transform = `translate(${pull * 0.6 - 44}px, ${y - 22}px)`;
    ring.style.opacity = Math.min(1, dx / 40);
  };
  edge.addEventListener("touchstart", (event) => {
    const touch = event.touches[0];
    start = { x: touch.clientX, y: touch.clientY, moved: false, back: null };
    ready = false;
    document.documentElement.classList.add("edging");
    ring.classList.remove("ready", "rest");
  }, { passive: true });
  edge.addEventListener("touchmove", (event) => {
    if (!start) return;
    const touch = event.touches[0], dx = touch.clientX - start.x, dy = touch.clientY - start.y;
    if (Math.hypot(dx, dy) > 8) start.moved = true;
    if (start.back === null) {
      if (Math.hypot(dx, dy) < 6) return;
      start.back = dx >= Math.abs(dy) * 0.6;
    }
    if (!start.back) return;
    if (event.cancelable) event.preventDefault();
    place(Math.max(0, dx), touch.clientY);
    if (ready !== dx > REACH) {
      ready = dx > REACH;
      ring.classList.toggle("ready", ready);
      if (ready) feelSlide();
    }
  }, { passive: false });
  const end = (event) => {
    if (!start) return;
    const { moved } = start, touch = event.changedTouches[0];
    start = null;
    document.documentElement.classList.remove("edging");
    ring.classList.add("rest");
    if (ready) return history.back();
    ring.style.opacity = 0;
    ring.style.transform = `translate(-44px, ${touch.clientY - 22}px)`;
    if (moved || event.type === "touchcancel") return;
    event.preventDefault();
    edge.hidden = true;
    const under = document.elementFromPoint(touch.clientX, touch.clientY);
    edge.hidden = false;
    under?.click();
  };
  edge.addEventListener("touchend", end);
  edge.addEventListener("touchcancel", end);
  // 뒤로 가기로 떠난 페이지가 브라우저 캐시에서 그대로 돌아오면 원을 거둔 상태로 되돌린다.
  addEventListener("pageshow", () => { ring.classList.remove("ready"); ring.style.opacity = 0; }, { signal: life.signal });
}
