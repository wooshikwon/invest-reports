// @ts-nocheck
import { ASSET_URL } from "../shared/account";
import { feelPress, tg } from "../shared/telegram";
// 알림 설정 화면(`?alerts=1`)은 리포트 화면 머리 상자의 알림 단추가 여는 화면이다. 미니 앱 봇이 봇 대화창으로 보내는 알림을 종류마다 켜고 끈다.
// 설정은 사람마다 invest-account Worker의 `POST /alerts`에 본인 서명(initData)과 함께 적고, claude-svr의 toss_trader.alerts가 그 설정대로 보낸다. 처음에는 모두 꺼져 있다.
// 거래 30분 전과 거래 집행 완료·실패는 본인(Worker가 `owner`로 답한 사람)에게만 보인다.
// 알림을 켤 때는 봇이 대화창에 메시지를 보내도록 텔레그램의 허락(`requestWriteAccess`)을 먼저 받는다. 허락하지 않으면 켜지 않는다.
const KINDS = [
  ["remind", "거래 30분 전", "집행 시각 30분 전에 그날 주문 요청과 결정 상태를 알려요.", true],
  ["execution", "거래 집행 완료·실패", "집행이 끝나면 체결 내역을, 집행하지 못하면 사유를 알려요.", true],
  ["report", "예측 분석 완료", "나스닥·바이오 판단 리포트가 올라오면 알려요.", false],
  ["news", "종목 뉴스 업데이트", "종목 뉴스가 올라오면 지수마다 기사 제목을 모아 알려요.", false],
  ["move", "나스닥·바이오 3%·5% 등락", "애프터마켓·선물시장·프리마켓·정규장 값이 앞 정규장 종가보다 3%, 5% 넘게 움직이면 알려요. 문턱마다 그 날짜에 한 번만 알려요.", false],
];
const ask = (set = null) => fetch(`${ASSET_URL}/alerts`, { method: "POST", cache: "no-store", body: JSON.stringify({ initData: tg.initData, ...(set ? { set } : {}) }) })
  .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
// 텔레그램이 허락 창을 띄울 수 없는 판(6.9 미만)은 허락을 묻지 않는다. 이미 허락한 사람에게는 텔레그램이 창 없이 참을 답한다.
const allowed = () => new Promise((done) => (tg.requestWriteAccess && tg.isVersionAtLeast?.("6.9") ? tg.requestWriteAccess((granted) => done(!!granted)) : done(true)));

export function mount(root, { signal }) {
  const title = "알림 설정";
  document.title = title;
  document.getElementById("issue-bar").textContent = title;
  const page = Object.assign(document.createElement("div"), { className: "alerts-page" });
  root.replaceChildren(page);
  const status = (text) => { page.innerHTML = `<h2>알림 설정</h2><p class="status">${text}</p>`; };
  if (!(tg && tg.initData)) return status("텔레그램 앱에서 열어야 알림을 설정할 수 있다.");
  status("설정을 불러오는 중이다.");
  ask().then(({ owner, prefs }) => {
    if (signal.aborted) return;
    page.innerHTML = '<h2>알림 설정</h2><p class="lead">켠 알림은 이 봇과의 대화창으로 와요. 처음에는 모두 꺼져 있어요.</p><div class="rows"></div><p class="note"></p>';
    const rows = page.querySelector(".rows"), note = page.querySelector(".note");
    KINDS.filter(([, , , mine]) => owner || !mine).forEach(([kind, name, desc]) => {
      const row = rows.appendChild(Object.assign(document.createElement("div"), { className: "row" }));
      row.innerHTML = `<div><b>${name}</b><span>${desc}</span></div><button type="button" class="switch" role="switch"></button>`;
      const button = row.querySelector("button");
      button.setAttribute("aria-label", name);
      const set = (on) => button.setAttribute("aria-checked", String(on));
      set(!!prefs[kind]);
      button.addEventListener("click", async () => {
        if (button.disabled) return;
        feelPress();
        const on = button.getAttribute("aria-checked") !== "true";
        button.disabled = true;
        note.textContent = "";
        if (on && !(await allowed())) {
          button.disabled = false;
          note.textContent = "봇이 대화창에 메시지를 보내도록 허락해야 알림을 받을 수 있어요.";
          return;
        }
        set(on);
        ask({ [kind]: on }).then((answer) => signal.aborted || set(!!answer.prefs[kind]), () => {
          if (signal.aborted) return;
          set(!on);
          note.textContent = "설정을 저장하지 못했어요. 미니 앱을 다시 열고 눌러 주세요.";
        }).finally(() => { button.disabled = false; });
      });
    });
  }, () => signal.aborted || status("설정을 불러오지 못했다. 미니 앱을 다시 열면 새로 받는다."));
}
export function unmount() {}
