// @ts-nocheck
import { slider } from "./motion";
// 이슈 그림 묶음에 그림이 두 장 이상이면 그림과 사진 설명을 넘기기 묶음에 싣고, 묶음 아래에 장마다 점을 찍는다.
export function gallery(figure) {
  const photos = [...figure.querySelectorAll(":scope > figure.photo")];
  if (photos.length < 2) return;
  const dots = document.createElement("div");
  dots.className = "dots";
  photos.forEach((_, k) => dots.appendChild(document.createElement("i")).addEventListener("click", () => box.go(k)));
  const mark = figure.insertBefore(document.createElement("span"), photos[0]);
  const box = slider(photos.map((photo) => [photo]), mark, { feel: true, change: (i) => [...dots.children].forEach((dot, k) => dot.classList.toggle("on", k === i)) });
  mark.remove();
  box.after(dots);
}

export function viewer(img) {
  const box = document.createElement("div");
  box.className = "viewer";
  // 되감기 슬라이더가 원래 그림을 숨기고 canvas를 보이므로, 크게 보는 그림은 숨김을 풀어 띄운다.
  const large = img.cloneNode();
  large.style.display = "";
  box.append(large);
  document.body.append(box);
  const carousel = img.closest(".carousel");
  const group = carousel ? [...carousel.querySelectorAll("img")] : [img];
  let index = group.indexOf(img), swipe = null;
  let scale = 1, x = 0, y = 0, start = null, moved = false;
  const place = () => {
    const fit = (offset, size, room, at) => size * scale <= room ? (size - size * scale) / 2
      : Math.min(-at, Math.max(room - at - size * scale, offset));
    x = fit(x, large.offsetWidth, box.clientWidth, large.offsetLeft);
    y = fit(y, large.offsetHeight, box.clientHeight, large.offsetTop);
    large.style.transform = `translate(${x + (swipe ? swipe.dx : 0)}px, ${y}px) scale(${scale})`;
  };
  // 묶음의 i번 그림으로 바꾸고, 닫았을 때 그 그림이 보이도록 뒤의 묶음도 함께 넘긴다.
  const show = (i) => {
    index = i;
    large.src = group[i].src;
    scale = 1; x = 0; y = 0;
    large.style.transform = "";
    carousel.go([...carousel.querySelector(".track").children].indexOf(group[i].closest(".slide")));
  };
  const touches = (event) => {
    const [a, b = a] = event.touches;
    return { mid: [(a.clientX + b.clientX) / 2 - large.offsetLeft, (a.clientY + b.clientY) / 2 - large.offsetTop],
             gap: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), count: event.touches.length };
  };
  box.addEventListener("touchstart", (event) => {
    if (event.touches.length === 1) moved = false;
    start = { ...touches(event), scale, x, y };
    swipe = event.touches.length === 1 && scale === 1 && group.length > 1 ? { dx: 0, dy: 0 } : null;
  }, { passive: true });
  box.addEventListener("touchmove", (event) => {
    event.preventDefault();
    const now = touches(event);
    if (now.count !== start.count) { start = { ...now, scale, x, y }; swipe = null; }
    if (swipe) {
      swipe = { dx: now.mid[0] - start.mid[0], dy: now.mid[1] - start.mid[1] };
      if (Math.hypot(swipe.dx, swipe.dy) > 8) moved = true;
      place();
      return;
    }
    if (now.count === 2) scale = Math.min(5, Math.max(1, start.scale * now.gap / start.gap));
    const ratio = scale / start.scale;
    x = now.mid[0] - (start.mid[0] - start.x) * ratio;
    y = now.mid[1] - (start.mid[1] - start.y) * ratio;
    if (now.count === 2 || Math.hypot(now.mid[0] - start.mid[0], now.mid[1] - start.mid[1]) > 8) moved = true;
    place();
  }, { passive: false });
  box.addEventListener("touchend", (event) => {
    if (event.touches.length) { start = { ...touches(event), scale, x, y }; swipe = null; return; }
    if (!swipe) return;
    const next = index + (swipe.dx < 0 ? 1 : -1);
    const turn = Math.abs(swipe.dx) > 50 && Math.abs(swipe.dx) > Math.abs(swipe.dy) && group[next];
    swipe = null;
    if (turn) show(next); else place();
  });
  box.addEventListener("click", () => { if (!moved) box.remove(); });
}
