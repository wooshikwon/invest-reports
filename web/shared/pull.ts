// @ts-nocheck
import { key, query } from "./route";
import { feelPress, haptic } from "./telegram";
// 문서 맨 위에서 시작해 아래로 끌면 본문이 손가락을 따라 내려온다. 본문은 처음에 끈 거리의 85%만큼 내려오고, 더 끌수록 따라오는 비율이 조금씩 줄어 손가락보다 덜 내려온다.
// 끈 거리 `d`에 본문은 1020 × (√(1 + d/600) − 1)px 내려오므로 비율은 줄어도 끄는 거리에 한계는 없다.
// 새로고침 표시는 벌어진 틈의 가운데에 두고, 본문이 176px에 닿을 때까지 호를 그만큼 늘린다. 176px에 닿으면 호가 돌기 시작하고, 손을 떼기 전에 미니 앱 문서와 `r/index.json`, `r/market.json`, 리포트나 종목 값을 서버에서 새로 받는다.
// 리포트는 `report.html`과 `r/index.json`의 `parts`에 적힌 `history.json`·`cards.json`을 새로 받는다.
// 새로 받기가 손을 떼기 전에 끝나도 호는 계속 돈다. 손을 떼면 본문과 표시가 96px 아래 자리로 올라가 멈춘다. 그 자리에 닿고 새로 받기도 끝나면 미니 앱을 다시 연다.
// 다시 연 문서는 `sessionStorage`의 `pulled`를 읽어 표시를 96px 아래에 두고, 앞 문서에서 돌던 각도부터 호를 이어 돌린다. 과거 리포트 띠도 앞 문서처럼 먼저 세운다.
// 리포트는 앞 문서가 막 새로 받은 사본을 서버에 다시 묻지 않고 쓰고, 다 그릴 때까지 본문을 감춘다. 리포트를 다 그리면(`landed`) 본문이 96px 아래 자리에서 나타나고
// 새로고침 완료 동작을 보인 뒤 본문과 표시를 0.45초에 걸쳐 고른 속도로 제자리로 올린다(`slow`).
// 176px에 닿기 전에 떼거나 옆으로 밀면 새로 받지 않고 제자리로 돌아간다. 새로 받기에 실패하면 다시 열지 않고 제자리로 돌아간다.
// 판단 배치의 단계가 바뀌면 `r/index.json`과 리포트가 바뀌므로, 다시 열면 그날 리포트의 새 단계를 받는다.
// 이슈 화면과 종목 상세도 같은 몸짓으로 새로 받는다. 종목 상세는 리포트 대신 `r/stocks/{티커}.json`을 새로 받는다.
export let landed = () => {};
export let pulled = null;
// 리포트 목록과 리포트, 시세는 서버에 바뀌었는지 물어 받는다. 당겨 새로고침으로 다시 연 문서는 앞 문서가 받아 둔 사본을 그대로 쓴다.
export let cache = "no-cache";
export function initPull() {
  pulled = JSON.parse(sessionStorage.getItem("pulled") || "null");
  sessionStorage.removeItem("pulled");
  cache = pulled ? "force-cache" : "no-cache";
  const pull = document.getElementById("pull"), arc = pull.querySelector("circle"), main = document.querySelector("main"), FULL = 176, HOLD = 96;
  const head = document.getElementById("masthead");
  let from = null, fetching = null, spun = 0;
  // 본문을 `y`px 아래로 옮긴다. 화면 위에 붙은 머리 상자는 `-y`px 옮겨 화면에서 제자리에 둔다. 문서 맨 위에서는 머리 상자가 붙지 않으므로 본문과 함께 옮긴다.
  // `offset`은 지금 그려진 본문의 옮긴 거리다.
  const shift = (y) => {
    main.style.transform = y ? `translate3d(0, ${y}px, 0)` : "";
    head.style.transform = y && scrollY > 0 && head.classList.contains("stuck") ? `translate3d(0, ${-y}px, 0)` : "";
  };
  const offset = () => new DOMMatrixReadOnly(getComputedStyle(main).transform).m42;
  const place = (y, grown = fetching ? 1 : Math.min(1, y / FULL)) => {
    shift(y);
    pull.style.transform = `translateY(${y / 2}px) scale(${.7 + .3 * grown})`;
    pull.style.opacity = Math.min(1, y / 48);
    if (!pull.classList.contains("done")) arc.setAttribute("stroke-dasharray", `${grown * 75} 100`);
    pull.classList.toggle("ready", grown === 1);
  };
  const settle = (y, grown, slow = false) => {
    [main, pull].forEach((el) => el.classList.toggle("slow", slow));
    main.classList.add("pulling");
    pull.classList.add("back");
    place(y, grown);
  };
  const refresh = () => {
    feelPress();
    pull.classList.add("spin");
    spun = Date.now();
    const stock = query.get("stock");
    const named = !stock && /^\d{8}-[a-z]+$/.test(key);
    const urls = [location.href.split("#")[0], "r/market.json", ...(stock ? [`r/stocks/${stock}.json`] : named ? [`r/${key}/report.html`] : [])];
    const reload = (url) => fetch(url, { cache: "reload" }).then((r) => { if (!r.ok) throw new Error(r.status); return r; });
    // 리포트의 이슈 과거 맥락과 요약 카드 값은 새로 받은 `r/index.json`의 `parts`에 적힌 것만 새로 받는다.
    const listed = reload("r/index.json").then((r) => r.json())
      .then((listing) => Promise.all((named ? listing[key]?.parts ?? [] : []).map((part) => reload(`r/${key}/${part}.json`))));
    fetching = Promise.all([...urls.map(reload), listed]).then(() => true, () => false);
  };
  const release = () => {
    from = null;
    if (!fetching) return settle(0);
    settle(HOLD);
    Promise.all([fetching, new Promise((done) => setTimeout(done, 250))]).then(([ok]) => {
      if (ok) {
        sessionStorage.setItem("pulled", JSON.stringify({ spun, past: document.documentElement.classList.contains("past") }));
        return location.reload();
      }
      fetching = null;
      pull.classList.remove("spin");
      settle(0);
    });
  };
  // 문서 끝의 튕김(`bounce`)은 손을 떼고 미끄러지던 화면이 문서 끝에 닿을 때 본문만 문서 끝 바깥으로 밀었다가 되돌린다. 본문은 문서 끝에 닿은 시각
  // `since`에 닿는 순간의 속도 `v`(px/ms, 아래로 밀려나면 양수)로 출발하는 감쇠 용수철 하나를 따라 움직인다. 용수철은 본문의 속도를 점점 줄여 멈추고,
  // 반대 방향으로 점점 빨라지다가 다시 느려지며 본문을 제자리에 둔다. 출발 속도가 화면의 속도와 같으므로 본문은 문서 끝에서 속도가 끊기지 않고 이어 간다.
  // 용수철의 고유 진동수는 초당 8라디안(`W`), 감쇠비는 1.02(`Z`)이다. 감쇠비가 1보다 조금 커서 본문은 제자리를 지나치지 않고, 밀려난 거리는 닿은 뒤 `t`ms에
  // v/(R1 − R2) × (e^(R1·t) − e^(R2·t))px다. 본문은 0.12초 뒤 닿는 속도의 45배(px)까지 밀려나고 1.2초 남짓 지나 제자리에 닿는다.
  // 닿는 속도는 3.5px/ms에서 자르므로 본문은 160px 넘게 밀려나지 않는다. 닿는 속도가 느릴수록 밀려나는 거리가 짧아질 뿐, 느리게 닿아도 튕긴다.
  const W = .008, Z = 1.02, R1 = -W * (Z - Math.sqrt(Z * Z - 1)), R2 = -W * (Z + Math.sqrt(Z * Z - 1));
  let bouncing = 0;
  const halt = () => { cancelAnimationFrame(bouncing); bouncing = 0; };
  const bounce = (v, since) => {
    halt();
    main.classList.remove("pulling");
    v = Math.max(-3.5, Math.min(3.5, v));
    const step = () => {
      const t = Math.max(0, performance.now() - since), y = v / (R1 - R2) * (Math.exp(R1 * t) - Math.exp(R2 * t));
      shift(y);
      bouncing = t < 200 || Math.abs(y) > .3 ? requestAnimationFrame(step) : (shift(0), 0);
    };
    step();
  };
  const bottom = () => scrollY >= document.documentElement.scrollHeight - innerHeight - 1;
  // 문서 맨 아래의 튕김은 웹뷰가 스스로 그린다. 스크립트는 스크롤 이벤트를 화면이 문서 끝에 닿은 뒤 한두 프레임 늦게 받으므로, 스크립트가 그린 튕김은 문서 끝에서 미세하게 끊긴다.
  // 화면이 문서 맨 위에서 한 화면 높이와 스크롤 범위의 절반 가운데 짧은 거리보다 아래에 있으면 문서에 `native-end`를 달아 웹뷰의 세로 튕김을 켠다(`native`).
  // 그보다 위에서는 웹뷰의 튕김을 끄므로, 문서 맨 위의 튕김과 당겨 새로고침은 스크립트가 그린다. 스크롤 범위가 없는 짧은 문서는 양 끝의 튕김을 모두 스크립트가 그린다.
  const root = document.documentElement;
  const native = () => {
    const max = root.scrollHeight - innerHeight;
    return root.classList.toggle("native-end", max > 0 && scrollY > Math.min(innerHeight, max / 2));
  };
  native();
  addEventListener("resize", native, { passive: true });
  // 손을 뗀 뒤 4초 안의 스크롤만 미끄러짐으로 본다. 문서 끝에 닿는 마지막 스크롤은 문서 끝에서 잘려 짧으므로 속도에서 뺀다. 속도(px/ms)는 그 앞의
  // 마지막 스크롤 기록(`prior`)까지 0.05초 안의 기록에서 처음 기록과 마지막 기록 사이의 거리를 시간으로 나눈 값이고, 그 안의 기록이 하나뿐이면 마지막 두 기록으로 잰다.
  // 화면은 스크롤 이벤트가 오기 전에 문서 끝에 닿아 멈춰 있으므로, 닿은 시각은 `prior`의 자리에서 그 속도로 문서 끝까지 가는 시각으로 셈한다.
  // 튕김은 그 시각부터 흐른 시간의 자리를 스크롤 이벤트 안에서 바로 그리므로, 이벤트가 늦게 와도 본문은 문서 끝에서 멈칫하지 않는다.
  let touching = false, lifted = -Infinity, marks = [];
  addEventListener("scroll", () => {
    const now = performance.now(), y = scrollY, own = !native(), edge = y <= 0 || bottom() && own;
    marks = marks.filter(([t]) => now - t < 100);
    const prior = marks.at(-1), near = marks.filter(([t]) => t >= prior?.[0] - 50), span = near.length > 1 ? near : marks.slice(-2);
    marks.push([now, y]);
    if (!edge || span.length < 2 || touching || now - lifted > 4000) return;
    const v = (prior[1] - span[0][1]) / Math.max(1, prior[0] - span[0][0]);
    if (Math.abs(v) < .03 || !(y <= 0 ? prior[1] > 0 && v < 0 : y > prior[1] && v > 0)) return;
    bounce(-v, Math.min(now, prior[0] + (y - prior[1]) / v));
  }, { passive: true });
  // 문서 끝에서 화면 밖으로 끌면 본문이 같은 비율로 줄어드는 거리만큼 따라오고, 손을 떼면 0.65초에 걸쳐 서서히 제자리로 돌아간다.
  // 문서 맨 위에서 아래로 끌 때만 새로고침 표시를 띄운다. 웹뷰가 튕김을 그리지 않는 짧은 문서는 맨 아래에서 위로 끌면 본문만 올라간다.
  // 튕기거나 제자리로 돌아가는 본문에 손가락이 닿으면 본문은 그 자리에 멈춘다(`base`). 이어서 문서 끝 밖으로 끌면 멈춘 자리부터 따라오고,
  // 끌지 않고 떼거나 문서 안쪽으로 밀면 멈춘 자리에서 0.65초에 걸쳐 제자리로 돌아간다.
  const rest = () => {
    main.classList.add("pulling");
    shift(0);
  };
  addEventListener("touchstart", (event) => {
    touching = true;
    halt();
    if (pull.matches(".spin, .done")) return;
    const base = offset();
    main.classList.remove("pulling");
    shift(base);
    const edge = event.touches.length !== 1 ? "" : scrollY <= 0 ? (bottom() ? "both" : "top") : bottom() && !native() ? "bottom" : "";
    from = edge ? { x: event.touches[0].clientX, y: event.touches[0].clientY, edge, down: false, base } : null;
    if (!from && base) rest();
    pull.classList.remove("back");
  }, { passive: true });
  addEventListener("touchmove", (event) => {
    if (!from) return;
    const dx = event.touches[0].clientX - from.x, dy = event.touches[0].clientY - from.y;
    if (!from.down) {
      if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
      const up = from.edge !== "top" && from.base <= 0 && dy < 0 && Math.abs(dx) < -dy && bottom();
      const down = from.edge !== "bottom" && from.base >= 0 && dy > 0 && Math.abs(dx) <= dy && scrollY <= 0;
      if (!up && !down) {
        if (from.base) rest();
        from = null;
        return;
      }
      from.down = up ? "up" : "down";
    }
    const pulled = Math.max(0, 1020 * (Math.sqrt(1 + Math.abs(dy) / 600) - 1));
    if (from.down === "up") {
      shift(from.base - (dy < 0 ? pulled : 0));
      return;
    }
    const y = from.base + (dy > 0 ? pulled : 0);
    if (y >= FULL && !fetching) refresh();
    place(y);
  }, { passive: true });
  const lift = () => {
    touching = false;
    lifted = performance.now();
    if (!from) return;
    if (from.down === "up") {
      from = null;
      rest();
      return;
    }
    release();
  };
  addEventListener("touchend", lift, { passive: true });
  addEventListener("touchcancel", lift, { passive: true });
  // 새로고침 완료 동작은 호를 온전한 원으로 닫고 원 둘레에서 흰 고리를 한 번 퍼뜨리는 것이다. 고리가 거의 퍼진 뒤 본문과 표시를 올린다.
  if (pulled) {
    fetching = Promise.resolve(true);
    if (pulled.past) document.documentElement.classList.add("past");
    pull.querySelector("svg").style.animationDelay = `${-((Date.now() - pulled.spun) % 800)}ms`;
    pull.classList.add("spin");
    main.classList.add("veil");
    place(HOLD);
    landed = () => {
      landed = () => {};
      main.classList.replace("veil", "unveil");
      pull.classList.remove("spin");
      pull.classList.add("done");
      arc.setAttribute("stroke-dasharray", "100 100");
      haptic?.notificationOccurred("success");
      setTimeout(() => {
        fetching = null;
        settle(0, 1, true);
        setTimeout(() => { pull.classList.remove("done"); main.classList.remove("unveil"); }, 450);
      }, 550);
    };
  }
}
