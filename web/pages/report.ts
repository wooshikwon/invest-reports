// @ts-nocheck
import { assets } from "./asset";
import { events, freeze } from "./calendar";
import { issueCharts, section } from "./issue";
import { indicators } from "./macro";
import { indexMap } from "./market";
import { newsTab } from "./news";
import { figures } from "./outlook";
import { alertBell, indexPick, latest, pageName } from "../shared/chrome";
import { marketed, relist } from "../shared/data";
import { help } from "../shared/help";
import { keep, kept } from "../shared/keep";
import { subscribe } from "../shared/live";
import { atEdge, home, motion, settle, settleStart } from "../shared/motion";
import { key, life, query, report, reshow, returned } from "../shared/route";
import { fold, notes, toneTags, trail } from "../shared/sections";
import { feelPress, feelSlide } from "../shared/telegram";
import { viewer } from "../shared/viewer";
// 리포트 화면과 이슈 화면을 그린다. `body`는 `r/{키}/report.html`이고, `listing`은 `r/index.json`이다.
// 리포트 화면과 이슈 화면은 `mount`로 그리고 `unmount`로 걷는다. 화면이 거는 손길과 받는 값은 수명(`life`)에 묶여 있고, `unmount`는 페이지를 여는 함수를 비운다.
export const mount = (root, { body, listing, cards, history, outlook }) => reportPage(body, listing, cards, history, outlook);
export const unmount = () => unturn();
// 판단이 올라와 화면을 그 자리에서 다시 그릴 때(`arrive`) 보던 페이지와 화면 위치를 다음 화면에 넘긴다.
let carry = null;
const OUTLOOK = ["현재 상태", "주요 분기와 예측", "종합 시나리오"];
const NOTE_OF = { "주가": "현재 상태", "예측과 일정": "주요 분기와 예측", "권장 배율": "종합 시나리오" };
function reportPage(body, listing, cards, history, given) {
  const { signal } = life;
  const carried = carry;
  carry = null;
  settleStart();
  const index = key.split("-")[1], entry = listing[key], isLatest = key === latest(listing, index);
  // `due`는 가장 늦은 리포트의 판단 날짜 지점(`entry.point`)의 정규장이 시작했거나 그보다 늦은 날짜 지점의 실시간 값이 들어왔는지다.
  // 그때부터 다음 판단이 올라올 때까지 화면의 예측은 업데이트를 기다리는 값이다.
  // 설명 세 절(`noted`)은 화면을 그릴 때 받은 가장 늦은 판단의 `outlook.json`(`given`)으로 채우고, 예측 단추(`aimed`)의 상태를 받지 않는다.
// 예측 단추의 상태는 기기의 `aim`에 남겨 다른 리포트와 다음에 열 때도 쓴다(`keep.ts`).
  // 설명 절은 그 절에 맞는 그림 카드와 한 장에 넣어 카드와 함께 넘긴다(`NOTE_OF`). 주가 카드는 현재 상태, 예측과 일정 카드는 주요 분기와 예측, 권장 배율 카드는 종합 시나리오다.
  // `due`인 동안(판단 배치가 도는 동안 포함)에는 설명 절의 제목과 내용을 회색으로 흐리게 보인다.
  let due = false, cardSet = null, noted = null, aimed = kept("aim") === true;
  // 예측 단추의 글자는 판단 배치의 단계(`stage`)로 정하고, 단계 판정은 여기서 하며 `outlook.ts`는 받은 글자와 상태만 그린다.
  // 단계는 가장 늦은 리포트를 보는 동안만 정한다. 실시간 값의 `progress`가 보는 리포트의 날짜(`entry.date`)보다 늦은 날짜에 이 지수의 단계를 적었으면 판단 배치가 도는 중이라 "예측 중 N%"(`running`)이고,
  // 그렇지 않은데 `due`이면 배치가 시작하기 전이라 "예측 업데이트 전"(`pre`)이다. 그 밖에는 "예측"(`done`)이다.
  // 진척률은 지금 단계의 누적 분에 그 단계에 머문 분을 다음 단계의 몫까지만 더해 마지막 누적 분으로 나눈 값이고, 줄지 않으며 99%에서 멈춘다.
  let stage = { state: "done", text: "예측" }, shown = 0, shownFor = null;
  const view = { aim: aimed, stage: () => stage, watch: (on) => { aimed = on; keep("aim", on); } };
  if (entry) {
    document.title = `${entry.title} ${entry.day}`;
    const judge = (found) => {
      const progressed = found?.progress, own = isLatest && progressed?.date > entry.date && progressed.indexes?.[index], plan = progressed?.plan || [];
      if (own && plan.length >= 2 && plan.at(-1)) {
        const step = Math.min(own.step, plan.length - 2);
        const inside = Math.min(Math.max((Date.now() - Date.parse(own.since)) / 60e3, 0), plan[step + 1] - plan[step]);
        if (shownFor !== progressed.date) { shownFor = progressed.date; shown = 0; }
        shown = Math.max(shown, Math.min(99, Math.floor((plan[step] + inside) / plan.at(-1) * 100)));
        return [{ state: "running", text: `예측 중 ${shown}%` }, true];
      }
      return [due ? { state: "pre", text: "예측 업데이트 전" } : { state: "done", text: "예측" }, due];
    };
    // 판단이 올라왔는지는 판단 배치가 돌거나 `due`인 동안 실시간 값을 받는 회차마다 `r/index.json`을 다시 받아 본다.
    // 이 지수의 목록 항목 가운데 날짜가 보는 리포트보다 늦은 것이 생기면 `arrive`로 화면을 그 자리에서 다시 그린다. 토요일 배치와 월요일 배치는 날짜 지점이 앞 리포트와 같거나 앞서 있어도 날짜로 알아본다.
    let asking = false;
    const arrive = (name) => {
      carry = { y: scrollY, page: window.history.state?.page };
      const params = new URLSearchParams(location.search);
      params.set("r", name);
      window.history.replaceState(window.history.state, "", `?${params}`);
      reshow(false);
    };
    subscribe((found) => {
      const points = found.points?.[index] || {};
      due = !!(isLatest && entry.point && (points[entry.point]?.regular || Object.keys(points).some((point) => point > entry.point)));
      noted?.fade(due);
      const [now, waiting] = judge(found);
      stage = now;
      cardSet?.label?.();
      if (!waiting || asking) return;
      asking = true;
      relist().then((fresh) => {
        asking = false;
        if (signal.aborted || !fresh) return;
        const hit = Object.keys(fresh).filter((name) => fresh[name].index === index && fresh[name].date > entry.date).sort((a, b) => fresh[b].date.localeCompare(fresh[a].date))[0];
        if (hit) arrive(hit);
      });
    }, true);
  }
  const date = entry ? entry.date : `${key.slice(0, 4)}-${key.slice(4, 6)}-${key.slice(6, 8)}`;
  if (!isLatest) {
    const today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
    document.getElementById("past").textContent = `${Math.max(1, Math.round((Date.parse(today) - Date.parse(date)) / 864e5))}일 전 리포트 탐색 중`;
    document.documentElement.classList.add("past");
  }
  report.innerHTML = body;
  const outlook = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === "1개월 지수 방향 예측");
  // 리포트의 "1개월 지수 방향 예측" 절은 "지수와 예측"이라는 제목으로 보인다. 제목으로 절을 찾는 코드는 이 제목을 쓴다.
  if (outlook) outlook.textContent = "지수와 예측";
  indexPick(listing);
  alertBell();
  const focus = +query.get("issue") || 0;
  // 시장 페이지 첫 절인 한 눈에 보기 절의 제목을 미국 거시 지표 절 제목 앞에 둔다. 미국 거시 지표 절이 없으면 문서 끝에 둔다.
  const glance = focus ? null : Object.assign(document.createElement("h2"), { textContent: "한 눈에 보기" });
  if (glance) {
    const macro = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === "미국 거시 지표");
    if (macro) macro.before(glance); else report.append(glance);
  }
  const pages = focus ? null : paginate();
  if (!focus) {
    // 설명 세 절은 리포트 본문에서 빼고 `outlook.json`으로 다시 붙인다. `outlook.json`이 없는 리포트는 설명 절을 보이지 않는다.
    const head = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === "지수와 예측");
    for (let node = head?.nextElementSibling, drop = false; node && node.tagName !== "H2"; node = node.nextElementSibling) {
      if (node.tagName === "H3") drop = OUTLOOK.includes(node.querySelector("mark")?.textContent.trim());
      if (drop) node.dataset.drop = "";
    }
    report.querySelectorAll("[data-drop]").forEach((node) => node.remove());
    cardSet = figures(cards, view);
    if (cardSet?.box) {
      noted = notes(Object.fromEntries(Object.entries(cardSet.slides).map(([name, slide]) => [NOTE_OF[name], slide])));
      noted.set(given?.sections, given?.point ?? "");
      noted.fade(due);
    }
    indicators();
    marketed.then(({ map }) => {
      if (signal.aborted) return;
      if (!map?.[index]?.stocks.length) return glance.remove();
      indexMap(glance, map[index], date, (hook) => subscribe((found) => hook(found.points[index]), true));
    });
  }
  issueCharts();
  toneTags(report);
  fold("상세 이슈 해설", 4, ["이슈 해설"]);
  // 이슈 해설은 그 리포트의 분석 완료 시각(`written`)을 기준으로 한다.
  section("상세 이슈 해설", focus, query.get("at"), entry?.written, history);
  // 번호 이슈 뒤 항목의 번호는 `section`이 먼저 붙인다.
  report.querySelectorAll("h3").forEach(trail);
  // 주소로 바로 연 이슈 화면과 종목 상세의 뒤로가기 단추로 연 리포트 화면(`land`)은 단추가 적은 페이지(이슈 화면은 이슈 페이지, 종목 상세는 시장 페이지)를
  // 맨 위부터 보여 준다. 그 밖에는 `history.state`에 적힌 페이지를 연다.
  const [landKey, landPage] = (sessionStorage.getItem("land") || "").split(" ");
  const land = !focus && landKey === key;
  if (land) sessionStorage.removeItem("land");
  if (!focus) {
    // 노드를 옮기면 넘기기 묶음의 스크롤 위치가 처음으로 돌아가므로, 막을 씌울 상자는 묶음을 만들기 전에 만든다.
    if (document.documentElement.classList.contains("past")) freeze("이벤트 캘린더", latest(listing, key.split("-")[1]));
    events(date, listing);
    help();
    newsTab(index, entry?.written);
    const head = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === "이벤트 캘린더");
    // `place`는 페이지와 바로가기 단추를 새로 묶고 `name` 페이지를 연다. 이름이 없거나 묶음에 없는 페이지면 첫 페이지를 연다.
    const place = (shown, names, name, still) => {
      document.querySelector("nav.jump")?.remove();
      turn = jump(shown, names);
      toCalendar = head?.pick ? (day) => { turn(shown.findIndex((page) => page.contains(head)), head); head.pick(day); } : null;
      turn(Math.max(0, names.indexOf(name)), null, still);
    };
    settle();
    assets(pages, PAGES.map(([name]) => name), place, land ? landPage : carried?.page ?? window.history.state?.page);
  }
  settle();
  if (carried) scrollTo(0, carried.y);
  // 예측과 일정처럼 글자가 작은 그림은 눌러서 미니 앱 안에서 화면 폭으로 띄우고, 두 손가락으로 키우고 줄이며
  // 키운 그림은 한 손가락으로 옮긴다. 원래 크기에서 좌우로 밀면 같은 묶음의 이전·다음 그림으로 넘긴다.
  // 손가락을 움직이지 않고 한 번 누르면 닫는다.
  // 이슈 목록 상자의 썸네일은 누르면 이슈를 열므로 띄우지 않는다.
  report.querySelectorAll("img:not(.thumb)").forEach((img) => img.addEventListener("click", () => viewer(img)));
  // 뒤로 가기로 돌아온 화면은 그림을 모두 받아 문서 높이가 정해진 뒤 떠나기 전 화면 위치로 옮긴다. 그 사이에 사용자가 화면을 움직였거나 화면을 바꿨으면 옮기지 않는다.
  // 옮긴 뒤 2초 안에 늦게 그린 카드가 문서 높이를 바꾸면 다시 옮긴다. 사용자가 화면을 움직였거나 떠나기 전 위치에 닿았으면 더 옮기지 않는다.
  if (returned) {
    Promise.all([...report.querySelectorAll("img")].map((img) => img.complete
      || new Promise((done) => { img.addEventListener("load", done, { once: true }); img.addEventListener("error", done, { once: true }); })))
      .then(() => {
        const y = window.history.state?.y;
        if (signal.aborted || scrollY !== 0 || !y) return;
        let placed = 0;
        const place = () => {
          if (signal.aborted || scrollY !== placed || placed === y) return watch.disconnect();
          scrollTo(0, y);
          placed = scrollY;
        };
        const watch = new ResizeObserver(place);
        place();
        watch.observe(report);
        setTimeout(() => watch.disconnect(), 2000);
      });
  }
}
// 리포트 화면의 절을 `PAGES`의 페이지에 나눠 담는다. 페이지마다 단추 이름과 그 페이지에 넣을 절 제목을 두고, 목록에 없는 절은 앞 절의 페이지에 넣는다.
// 넘기기 묶음은 노드를 옮기면 스크롤 위치가 처음으로 돌아가므로, 리포트를 받은 직후 묶음을 만들기 전에 나눈다.
export const PAGES = [["지수", ["지수와 예측", "이벤트 캘린더"]], ["이슈", ["상세 이슈 해설"]], ["시장", ["한 눈에 보기", "미국 거시 지표"]]];
// 바로가기 단추의 선 아이콘이다. 자산은 오른쪽 변에 여밈 단추가 붙은 지갑이다. 지수는 오른쪽 봉우리가 더 높은 꺾은선 아래를 닫은 둥근 면, 이슈는 불꽃, 시장은 고리를 두른 행성이다. 행성은 앞쪽 고리 둘레를 마스크로 비워 고리가 행성 앞을 지나게 그리고, 뒤쪽 고리는 행성 원판 자리를 비운 마스크로 가려 행성 뒤를 지나게 그린다.
// 행성은 다른 아이콘보다 작아 보여 1.05배로 키우고, 선 굵기는 다른 아이콘과 같게 둔다.
export const PAGE_ICONS = {
  자산: '<rect x="3" y="5.5" width="18" height="13" rx="3"/><path class="clasp" d="M21 9.5h-3.5a2.5 2.5 0 0 0 0 5H21"/>',
  지수: '<path class="ridge" d="M6.23 20.53Q3.55 20.53 3.55 17.85L3.55 14.95Q3.55 13.3 4.63 12.05L7.67 8.52Q8.81 7.19 10.03 8.45L11.54 10.01Q12.62 11.12 13.72 10.04L18.24 5.63Q20.45 3.47 20.45 6.56L20.45 17.85Q20.45 20.53 17.77 20.53Z"><animate attributeName="d" dur="1.2s" begin="indefinite" values="M6.23 20.53Q3.55 20.53 3.55 17.85L3.55 14.95Q3.55 13.3 4.63 12.05L7.67 8.52Q8.81 7.19 10.03 8.45L11.54 10.01Q12.62 11.12 13.72 10.04L18.24 5.63Q20.45 3.47 20.45 6.56L20.45 17.85Q20.45 20.53 17.77 20.53Z;M6.23 20.53Q3.55 20.53 3.55 17.85L3.55 15.98Q3.55 14.33 4.74 13.18L7.55 10.48Q8.81 9.26 10.13 10.41L11.45 11.55Q12.62 12.57 13.8 11.57L18.09 7.95Q20.45 5.95 20.45 9.04L20.45 17.85Q20.45 20.53 17.77 20.53Z;M6.23 20.53Q3.55 20.53 3.55 17.85L3.55 15.98Q3.55 14.33 4.74 13.18L7.55 10.48Q8.81 9.26 10.13 10.41L11.45 11.55Q12.62 12.57 13.8 11.57L18.09 7.95Q20.45 5.95 20.45 9.04L20.45 17.85Q20.45 20.53 17.77 20.53Z;M6.23 20.53Q3.55 20.53 3.55 17.85L3.55 14.42Q3.55 12.77 4.58 11.48L7.72 7.53Q8.81 6.16 9.99 7.45L11.57 9.16Q12.62 10.3 13.68 9.18L18.32 4.27Q20.45 2.03 20.45 5.12L20.45 17.85Q20.45 20.53 17.77 20.53Z;M6.23 20.53Q3.55 20.53 3.55 17.85L3.55 15.25Q3.55 13.61 4.65 12.38L7.64 9.02Q8.81 7.72 10.04 8.96L11.53 10.44Q12.62 11.54 13.74 10.47L18.21 6.22Q20.45 4.09 20.45 7.18L20.45 17.85Q20.45 20.53 17.77 20.53Z;M6.23 20.53Q3.55 20.53 3.55 17.85L3.55 14.95Q3.55 13.3 4.63 12.05L7.67 8.52Q8.81 7.19 10.03 8.45L11.54 10.01Q12.62 11.12 13.72 10.04L18.24 5.63Q20.45 3.47 20.45 6.56L20.45 17.85Q20.45 20.53 17.77 20.53Z" keyTimes="0;.18;.26;.62;.8;1" calcMode="spline" keySplines=".4 0 .6 1;0 0 1 1;.2 .8 .3 1;.45 0 .55 1;.45 0 .55 1"/></path>',
  이슈: '<path class="flame" d="M8.5 14.5C9.88 14.5 11 13.38 11 12C11 10.62 10.5 10 10 9C8.93 6.86 9.78 4.95 12 3C12.5 5.5 14 7.9 16 9.5C18 11.1 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.43 12.71 6 12C6 13.38 7.12 14.5 8.5 14.5Z"><animate attributeName="d" dur="1.3s" begin="indefinite" values="M8.5 14.5C9.88 14.5 11 13.38 11 12C11 10.62 10.5 10 10 9C8.93 6.86 9.78 4.95 12 3C12.5 5.5 14 7.9 16 9.5C18 11.1 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.43 12.71 6 12C6 13.38 7.12 14.5 8.5 14.5Z;M8.5 14.5C9.88 14.5 10.52 13.38 10.4 11.64C10.4 10.17 9.54 9.28 8.8 8.1C7.17 5.42 7.82 3.51 9.2 1.2C10.54 4.42 12.88 7.27 15.2 8.6C17.6 10.65 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.23 12.71 5.6 12C5.6 13.38 7.12 14.5 8.5 14.5Z;M8.5 14.5C9.88 14.5 11.4 13.38 11.5 12.2C11.5 10.87 11.3 10.4 11 9.5C10.53 7.54 11.88 5.43 15 3.6C14.6 5.86 15.3 8.18 17 9.9C18.5 11.3 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.68 12.71 6.5 12C6.5 13.38 7.12 14.5 8.5 14.5Z;M8.5 14.5C9.88 14.5 10.84 13.38 10.8 11.36C10.8 9.82 10.18 8.72 9.6 7.4C8.29 4.54 8.94 3.03 10.8 0.6C11.66 4.06 13.41 7.06 15.5 8.3C17.75 10.5 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.33 12.71 5.8 12C5.8 13.38 7.12 14.5 8.5 14.5Z;M8.5 14.5C9.88 14.5 11.28 13.38 11.35 12.36C11.35 11.07 11.06 10.72 10.7 9.9C10.07 8.18 11.32 6.07 14.2 4.4C14.04 6.34 15 8.6 16.8 10.5C18.4 11.6 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.73 12.71 6.6 12C6.6 13.38 7.12 14.5 8.5 14.5Z;M8.5 14.5C9.88 14.5 10.68 13.38 10.6 11.84C10.6 10.42 9.86 9.68 9.2 8.6C7.77 6.28 8.52 4.47 10.2 2.4C11.24 5.14 13.36 7.76 15.6 9.3C17.8 11 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.28 12.71 5.7 12C5.7 13.38 7.12 14.5 8.5 14.5Z;M8.5 14.5C9.88 14.5 11.12 13.38 11.15 11.76C11.15 10.32 10.74 9.52 10.3 8.4C9.45 5.93 10.55 4.07 13.1 1.9C13.27 4.84 14.43 7.55 16.3 9C18.15 10.85 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.53 12.71 6.2 12C6.2 13.38 7.12 14.5 8.5 14.5Z;M8.5 14.5C9.88 14.5 10.92 13.38 10.9 12.04C10.9 10.67 10.34 10.08 9.8 9.1C8.63 7.05 9.43 5.19 11.5 3.3C12.15 5.68 13.83 7.97 15.9 9.6C17.95 11.15 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.38 12.71 5.9 12C5.9 13.38 7.12 14.5 8.5 14.5Z;M8.5 14.5C9.88 14.5 11 13.38 11 12C11 10.62 10.5 10 10 9C8.93 6.86 9.78 4.95 12 3C12.5 5.5 14 7.9 16 9.5C18 11.1 19 13 19 15C19 18.87 15.87 22 12 22C8.13 22 5 18.87 5 15C5 13.85 5.43 12.71 6 12C6 13.38 7.12 14.5 8.5 14.5Z" keyTimes="0;.11;.24;.37;.5;.62;.74;.87;1" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1;.45 0 .55 1;.45 0 .55 1;.45 0 .55 1;.45 0 .55 1;.45 0 .55 1;.45 0 .55 1"/></path>',
  시장: '<g transform="translate(12 12) scale(1.05) rotate(-28)"><mask id="market-ring" maskUnits="userSpaceOnUse" x="-12" y="-12" width="24" height="24"><rect x="-12" y="-12" width="24" height="24" fill="#fff" stroke="none"/><path class="ring" d="M10.6 0A10.6 4.2 0 0 1 -10.6 0" stroke="#000" stroke-width="3.2"/></mask><mask id="market-body" maskUnits="userSpaceOnUse" x="-30" y="-30" width="60" height="60"><rect x="-30" y="-30" width="60" height="60" fill="#fff" stroke="none"/><circle r="7.5" fill="#000" stroke="none"/></mask><circle r="6.8" mask="url(#market-ring)" vector-effect="non-scaling-stroke"/><g mask="url(#market-body)"><path class="ring" vector-effect="non-scaling-stroke" d="M-10.6 0A10.6 4.2 0 0 1 10.6 0"/></g><path class="ring" vector-effect="non-scaling-stroke" d="M10.6 0A10.6 4.2 0 0 1 -10.6 0"/></g>',
};
// 바로가기 단추로 다른 페이지를 열거나 보고 있는 페이지의 단추를 다시 누르면 그 단추의 아이콘을 한 번 움직인다. 자산은 여밈 단추가 오른쪽 변을 축으로
// 바깥으로 젖혀져 열렸다가 잠시 멈춘 뒤 다시 닫히며 한 번 눌려 자리를 잡는다. 지수는 면이 살짝 가라앉았다가 두 봉우리가 원래보다 조금 높이 솟은 뒤 제자리로 돌아온다.
// 이슈는 불꽃 끝과 몸통, 안쪽 불꽃의 모양이 매 순간 달라지며 밑동을 축으로 흔들리고, 그동안 한 번 크게 타올랐다가 원래 크기로 잦아든다. 지수와 이슈의 모양 변화는 iOS WebKit이 CSS `d` 애니메이션을 지원하지 않아 SVG `<animate>`로 돌린다. 시장은 고리 없는 행성 위로 고리가 떨어져 걸린 뒤 행성 둘레를 한 바퀴 돈다.
// 고리는 끊긴 데 없는 타원으로 떨어지고, 뒤쪽 반은 행성 원판에 겹친 부분만 가려진다. 행성 앞을 지나는 마스크도 고리와 함께 움직이므로, 고리가 떨어지기 전에는 행성이 온전히 보인다.
export const ICON_MOTIONS = {
  자산: (svg) => [svg.querySelector(".clasp").animate([
    { transform: "none" }, { transform: "scaleX(-1)", offset: .32, easing: "cubic-bezier(.2, .8, .3, 1)" },
    { transform: "scaleX(-1)", offset: .55, easing: "cubic-bezier(.55, 0, .4, 1)" }, { transform: "scaleX(1.15)", offset: .8, easing: "ease-out" }, { transform: "none" },
  ], { duration: 1000 })],
  지수: (svg) => (svg.querySelector(".ridge animate").beginElement(), []),
  이슈: (svg) => {
    svg.querySelector(".flame animate").beginElement();
    return [svg.querySelector(".flame").animate([[0, 1], [-8, 1.1], [6, 1.15], [-4, 1.12], [2.5, 1.06], [-1, 1.02], [0, 1]].map(([skew, size]) => ({ transform: `rotate(${skew / 2}deg) skewX(${skew}deg) scale(${size})` })),
      { duration: 1300, easing: "ease-out" })];
  },
  시장: (svg) => [...svg.querySelectorAll(".ring")].map((ring) => ring.animate([
    { opacity: 0, transform: "translate(7px, -13.2px) rotate(0deg)" },
    { opacity: 1, transform: "translate(5.3px, -9.9px) rotate(0deg)", offset: .1, easing: "cubic-bezier(.55, 0, 1, .45)" },
    { transform: "translate(0px, 0px) rotate(0deg)", offset: .35, easing: "ease-out" },
    { transform: "translate(.6px, -1.1px) rotate(0deg)", offset: .43, easing: "ease-in" },
    { transform: "translate(0px, 0px) rotate(0deg)", offset: .5, easing: "cubic-bezier(.3, 0, .2, 1)" },
    { transform: "translate(0px, 0px) rotate(-360deg)" },
  ], { duration: 1500 })),
};
export function paginate() {
  const pages = PAGES.map(() => Object.assign(document.createElement("div"), { className: "page" }));
  let at = 0;
  [...report.children].forEach((node) => {
    const i = node.tagName === "H2" ? PAGES.findIndex(([, titles]) => titles.includes(node.textContent.trim())) : -1;
    if (i >= 0) at = i;
    pages[at].append(node);
  });
  report.append(...pages);
  return pages;
}
// `turn(i, head, still)`은 i번 페이지를 연다. `toCalendar(day)`는 지수 페이지의 이벤트 캘린더에서 거래일 `day`의 장을 연다.
// 둘 다 리포트 화면에서만 만든다.
export let turn = null, toCalendar = null;
const unturn = () => { turn = toCalendar = null; };
// 화면 아래 바로가기 알약에 페이지마다 단추를 두고 `turn`을 돌려준다. 단추를 누르면 그 페이지만 보여 주고, 페이지 맨 위로 옮긴다.
// 보고 있는 페이지의 단추를 다시 누르면 페이지 맨 위로 부드럽게 옮기고 단추의 아이콘을 다시 움직인다.
// 보고 있는 페이지 이름(`page`)은 `history.state`에 적어, 뒤로 가기와 새로 고침으로 돌아와도 그 페이지를 연다.
// 알약 위에서 누른 채 6px 넘게 움직이면 레버가 손가락을 따라 움직이고, 레버 가운데에서 가장 가까운 단추를 흰색으로 쓴다. 손을 떼면 그 단추를 누른 것과 같이 그 페이지를 연다.
// `turn`이 `head`를 받으면 그 절 제목 글자가 화면 맨 위에서 본 페이지 첫 절 제목 글자의 높이에 오도록 옮긴다. 문서 끝이 모자라면 그 페이지 아래 여백을 늘린다.
// 다른 페이지를 열면 페이지들이 바로가기 단추 순서대로 옆으로 흘러간다(`flow`). 오른쪽 페이지를 열면 화면이 왼쪽으로, 왼쪽 페이지를 열면 오른쪽으로 흐르고,
// 두 칸 떨어진 페이지를 열면 가운데 페이지가 맨 위부터 한가운데를 지나간다. `turn`이 `still`을 받거나 움직임 줄이기 설정이면 흐르지 않고 바로 바꾼다.
// 화면 좌우 끝 띠(`atEdge`)에서 시작해 가로로 40px 넘게, 세로 이동의 1.5배 넘게 안쪽으로 밀고 손을 떼면 옆 페이지를 연다. 오른쪽 끝에서 밀면 다음 페이지,
// 왼쪽 끝에서 밀면 앞 페이지다. 뒤로 가기 띠(`.back-edge`)와 넘기기 묶음, 그림 화면, 설명 상자 위에서 시작한 밀기는 받지 않는다.
// 다른 페이지를 열면 흐름이 끝난 뒤(흐르지 않으면 바로) 연 페이지 밖의 나란한 항목 묶음을 처음 항목으로 돌린다(`motion.ts` `home`).
// 바로가기 알약을 다시 만들면 앞 알약의 끝 밀기 손길을 걷는다(`edgeSwipe`).
let edgeSwipe = null;
export function jump(pages, names) {
  const nav = document.createElement("nav");
  nav.className = "jump";
  const lever = nav.appendChild(Object.assign(document.createElement("i"), { className: "lever" }));
  let page = -1;
  const textTop = (head) => {
    const band = getComputedStyle(head, "::before");
    return head.getBoundingClientRect().top + (band.content === "none" ? 0 : parseFloat(band.height) + parseFloat(band.marginBottom));
  };
  // 화면 위치를 여는 페이지의 위치(`y`)로 먼저 옮기고, 흐르는 동안 떠나는 페이지는 떠날 때의 화면 위치(`left`)에, 가운데 페이지는 맨 위에 있는 것처럼 위아래로 맞춰 그린다.
  // 흐르는 도중에 다른 페이지를 열면 앞 흐름을 끝낸 자리에서 새로 흐른다. 흐름이 끝나면 여는 페이지만 남긴다.
  let flowing = null;
  const flow = (from, to, y, left) => {
    flowing?.forEach((run) => run.finish());
    const w = innerWidth, low = Math.min(from, to), steps = Math.abs(to - from);
    report.classList.add("flow");
    const runs = pages.slice(low, Math.max(from, to) + 1).map((node, k) => {
      const j = low + k, dy = j === to ? 0 : j === from ? y - left : y;
      node.classList.remove("off");
      return node.animate([{ transform: `translate(${(j - from) * w}px, ${dy}px)` }, { transform: `translate(${(j - to) * w}px, ${dy}px)` }],
        { duration: 320 + 180 * (steps - 1), easing: "cubic-bezier(.45, 0, .15, 1)" });
    });
    flowing = runs;
    runs[0].finished.then(() => {
      if (flowing !== runs) return;
      flowing = null;
      report.classList.remove("flow");
      pages.forEach((node, j) => node.classList.toggle("off", j !== page));
      home(pages[page]);
    });
  };
  const wave = (i) => {
    if (motion.matches) return;
    const svg = buttons[i].querySelector("svg");
    svg.getAnimations({ subtree: true }).forEach((run) => run.cancel());
    ICON_MOTIONS[names[i]](svg);
  };
  const open = (i, head, still = false) => {
    const from = page, left = scrollY;
    if (i !== page) {
      pages.forEach((node, j) => node.classList.toggle("off", j !== i));
      buttons.forEach((button, j) => button.classList.toggle("on", j === i));
      if (page < 0) lever.style.transition = "none";
      lever.style.width = `${buttons[i].offsetWidth}px`;
      lever.style.transform = `translateX(${buttons[i].offsetLeft}px)`;
      lever.offsetWidth;
      lever.style.transition = "";
      if (page >= 0) wave(i);
      page = i;
      pageName.textContent = names[i];
      history.replaceState({ ...history.state, page: names[i] }, "");
    }
    let top = 0;
    if (head) {
      top = Math.max(0, textTop(head) - textTop(pages[i].querySelector("h2")));
      const lack = top + innerHeight - document.documentElement.scrollHeight;
      if (lack > 0) pages[i].style.paddingBottom = `${parseFloat(getComputedStyle(pages[i]).paddingBottom) + lack}px`;
    }
    if (from >= 0 && from !== i && !still && !motion.matches) flow(from, i, top, left);
    else if (from >= 0 && from !== i) home(pages[i]);
    scrollTo(0, top);
  };
  const press = (i) => {
    feelPress();
    if (i === page) { wave(i); scrollTo({ top: 0, behavior: "smooth" }); }
    else open(i);
  };
  let drag = null, dragged = false;
  const buttons = names.map((name, i) => {
    const button = nav.appendChild(Object.assign(document.createElement("button"), { type: "button" }));
    button.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${PAGE_ICONS[name]}</svg><span>${name}</span>`;
    button.addEventListener("click", () => { if (dragged) dragged = false; else press(i); });
    return button;
  });
  const nearest = (x) => buttons.reduce((best, button, i) =>
    (Math.abs(button.offsetLeft + button.offsetWidth / 2 - x) < Math.abs(buttons[best].offsetLeft + buttons[best].offsetWidth / 2 - x) ? i : best), 0);
  const light = (on) => buttons.forEach((button, j) => button.classList.toggle("on", j === on));
  nav.addEventListener("pointerdown", (event) => {
    drag = { x: event.clientX, left: nav.getBoundingClientRect().left + nav.clientLeft, moved: false, id: event.pointerId, on: page };
  });
  nav.addEventListener("pointermove", (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    if (!drag.moved && Math.abs(event.clientX - drag.x) <= 6) return;
    if (!drag.moved) { drag.moved = true; nav.setPointerCapture(event.pointerId); lever.classList.add("drag"); }
    const width = lever.offsetWidth, first = buttons[0], last = buttons.at(-1);
    const x = Math.min(last.offsetLeft + last.offsetWidth - width, Math.max(first.offsetLeft, event.clientX - drag.left - width / 2));
    lever.style.transform = `translateX(${x}px)`;
    const on = nearest(x + width / 2);
    if (on !== drag.on) { drag.on = on; light(on); feelSlide(); }
  });
  const end = (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    const { moved, on } = drag;
    drag = null;
    if (!moved) return;
    lever.classList.remove("drag");
    if (event.type === "pointercancel") { light(page); lever.style.transform = `translateX(${buttons[page].offsetLeft}px)`; return; }
    // 손을 뗀 자리에서 클릭이 이어지면 그 클릭은 버리고, 이어지지 않으면 다음 손길까지 기다리지 않게 바로 푼다.
    dragged = true;
    setTimeout(() => { dragged = false; }, 0);
    if (on === page) lever.style.transform = `translateX(${buttons[page].offsetLeft}px)`;
    else { feelPress(); open(on); }
  };
  nav.addEventListener("pointerup", end);
  nav.addEventListener("pointercancel", end);
  edgeSwipe?.abort();
  const own = edgeSwipe = new AbortController(), { signal } = own;
  life.signal.addEventListener("abort", () => own.abort(), { once: true, signal });
  let edge = null;
  document.addEventListener("touchstart", (event) => {
    const { target, touches } = event;
    edge = touches.length === 1 && atEdge(touches[0].clientX) && !target.closest(".back-edge, .carousel, .viewer, .help-card, nav.jump") ? { x: touches[0].clientX, y: touches[0].clientY } : null;
  }, { passive: true, signal });
  document.addEventListener("touchend", (event) => {
    if (!edge) return;
    const touch = event.changedTouches[0], dx = touch.clientX - edge.x, dy = touch.clientY - edge.y, to = page + (edge.x > innerWidth / 2 ? 1 : -1);
    edge = null;
    if (Math.abs(dx) <= 40 || Math.abs(dx) <= 1.5 * Math.abs(dy) || Math.sign(dx) !== (to > page ? -1 : 1) || to < 0 || to >= pages.length) return;
    feelSlide();
    open(to);
  }, { passive: true, signal });
  document.body.append(nav);
  return open;
}
