// @ts-nocheck
import { key, query } from "./route";
import { feelPress, haptic } from "./telegram";
// 문서 맨 위에서 아래로 끌면 웹뷰가 스스로 튕기며 본문을 내리고, 웹뷰가 문서 맨 위 밖으로 내린 거리는 음수의 `scrollY`로 알려진다.
// 새로고침 표시는 벌어진 틈에서 본문과 함께 내려오고, 내린 거리가 110px에 닿을 때까지 호를 그만큼 늘린다. 손가락이 닿은 채 110px에 닿으면 호가 돌기 시작하고,
// 손을 떼기 전에 미니 앱 문서와 `r/index.json`, `r/market.json`, 리포트나 종목 값을 서버에서 새로 받는다.
// 리포트는 `report.html`과 `r/index.json`의 `parts`에 적힌 `history.json`·`cards.json`을 새로 받는다.
// 새로 받기가 손을 떼기 전에 끝나도 호는 계속 돈다. 손을 떼면 본문은 웹뷰의 튕김으로 제자리로 돌아가고, 표시는 위쪽 높이 바로 아래로 옮겨 붙어 돈다(`hold`).
// 새로 받기가 끝나면 미니 앱을 다시 연다.
// 다시 연 문서는 `sessionStorage`의 `pulled`를 읽어 표시를 같은 자리에 두고, 앞 문서에서 돌던 각도부터 호를 이어 돌린다. 과거 리포트 띠도 앞 문서처럼 먼저 세운다.
// 리포트는 앞 문서가 막 새로 받은 사본을 서버에 다시 묻지 않고 쓰고, 다 그릴 때까지 본문을 감춘다. 리포트를 다 그리면(`landed`) 본문이 나타나고
// 새로고침 완료 동작을 보인 뒤 표시가 0.45초에 걸쳐 작아지며 사라진다(`slow`).
// 110px에 닿기 전에 떼면 새로 받지 않고, 표시는 본문과 함께 올라가며 흐려진다. 새로 받기에 실패하면 다시 열지 않고 표시를 감춘다.
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
  const pull = document.getElementById("pull"), arc = pull.querySelector("circle"), main = document.querySelector("main"), FULL = 110;
  let fetching = null, spun = 0, touching = false;
  // 웹뷰가 문서 맨 위 밖으로 내린 거리 `over`에 맞춰 표시를 드러내고 호를 늘린다. 위쪽 높이 아래에 붙은 표시는 그대로 둔다.
  const place = (over) => {
    if (pull.classList.contains("hold")) return;
    const grown = fetching ? 1 : Math.min(1, over / FULL);
    pull.style.transform = `scale(${.7 + .3 * grown})`;
    pull.style.opacity = Math.min(1, over / 48);
    arc.setAttribute("stroke-dasharray", `${grown * 75} 100`);
    pull.classList.toggle("ready", grown === 1);
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
  // 표시를 지금 보이는 자리에서 위쪽 높이 바로 아래 자리로 0.65초에 걸쳐 옮겨 붙인다.
  const hold = () => {
    const from = pull.getBoundingClientRect().top;
    pull.classList.add("hold");
    pull.style.transform = `translateY(${from - pull.getBoundingClientRect().top}px)`;
    pull.getBoundingClientRect();
    pull.classList.add("back");
    pull.style.transform = "";
  };
  // 붙어 있던 표시를 작아지며 흐려지게 한 뒤 문서 맨 위 위의 자리로 되돌린다.
  const close = (slow = false) => {
    pull.classList.toggle("slow", slow);
    pull.classList.add("back");
    pull.style.opacity = 0;
    pull.style.transform = "scale(.7)";
    setTimeout(() => {
      pull.classList.remove("hold", "back", "slow", "done", "ready");
      place(Math.max(0, -scrollY));
    }, slow ? 450 : 650);
  };
  const release = () => {
    touching = false;
    if (!fetching || pull.classList.contains("hold")) return;
    hold();
    Promise.all([fetching, new Promise((done) => setTimeout(done, 250))]).then(([ok]) => {
      if (ok) {
        sessionStorage.setItem("pulled", JSON.stringify({ spun, past: document.documentElement.classList.contains("past") }));
        return location.reload();
      }
      fetching = null;
      pull.classList.remove("spin");
      close();
    });
  };
  addEventListener("scroll", () => {
    const over = Math.max(0, -scrollY);
    place(over);
    if (touching && over >= FULL && !fetching) refresh();
  }, { passive: true });
  addEventListener("touchstart", (event) => { touching = event.touches.length === 1; }, { passive: true });
  addEventListener("touchend", release, { passive: true });
  addEventListener("touchcancel", release, { passive: true });
  // 새로고침 완료 동작은 호를 온전한 원으로 닫고 원 둘레에서 흰 고리를 한 번 퍼뜨리는 것이다. 고리가 거의 퍼진 뒤 표시를 닫는다.
  if (pulled) {
    fetching = Promise.resolve(true);
    if (pulled.past) document.documentElement.classList.add("past");
    pull.querySelector("svg").style.animationDelay = `${-((Date.now() - pulled.spun) % 800)}ms`;
    pull.classList.add("spin", "hold", "ready");
    pull.style.opacity = 1;
    arc.setAttribute("stroke-dasharray", "75 100");
    main.classList.add("veil");
    landed = () => {
      landed = () => {};
      main.classList.replace("veil", "unveil");
      pull.classList.remove("spin");
      pull.classList.add("done");
      arc.setAttribute("stroke-dasharray", "100 100");
      haptic?.notificationOccurred("success");
      setTimeout(() => {
        fetching = null;
        close(true);
        setTimeout(() => main.classList.remove("unveil"), 450);
      }, 550);
    };
  }
}
