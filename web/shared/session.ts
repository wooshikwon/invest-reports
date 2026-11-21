// @ts-nocheck
import { feelPress } from "./telegram";
// `usZone(day)`는 그날 뉴욕 시간대 이름(EST·EDT)이다.
export const NEW_YORK = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", timeZoneName: "short" });
export const usZone = (day) => NEW_YORK.formatToParts(new Date(`${day}T17:00:00Z`)).find((part) => part.type === "timeZoneName").value;
// 그림의 가로축은 거래일 번호이고, 정규장 종가(16:00 ET)를 그날 번호에 놓는다. 한 거래일은 다음 종가까지의 24시간이다.
// 판단의 기준 가격은 애프터장이 닫히는 20:00 ET의 체결가이므로 예측과 예측과 일정 카드는 기준 가격을 종가에서 `BASE_AFTER` 거래일 뒤에 놓는다.
export const BASE_AFTER = 4 / 24;
// 기준 시각 글씨는 "미국 11/17 애프터마켓, 08:15 KST"처럼 "미국" 뒤에 세션의 뉴욕 날짜, 세션 이름을 쓰고 쉼표 뒤에 체결 시각의 서울 시각을 쓴다(`sessionAt(name, time)`). 세 번째 값 `clock`을 주면 서울 시각을 `time` 대신 `clock`으로 쓴다.
// `time`은 뉴욕 시각 글씨이므로 앞 열 글자가 세션의 뉴욕 날짜다. 종가의 기준 시각은 정규장이 닫히는 16:00 ET(`closeAt(day)`)이고,
// `afterEnd(day)`는 그날 애프터장이 닫히는 20:00 ET의 뉴욕 시각 글씨다.
export const sessionAt = (name, time, clock = time) => `미국 ${time.slice(5, 7)}/${time.slice(8, 10)} ${name}, ${new Date(Date.parse(clock) + 9 * 3600e3).toISOString().slice(11, 16)} KST`;
export const nyAt = (day, clock) => `${day}T${clock}:00${usZone(day) === "EDT" ? "-04:00" : "-05:00"}`;
export const closeAt = (day) => nyAt(day, "16:00"), afterEnd = (day) => nyAt(day, "20:00");
// 기준 시각 글씨를 `kind` 세션(`regular`, `after`, `pre`)의 색으로 쓰는 글씨 조각이다.
export const sessionTag = (kind, text) => {
  const tag = Object.assign(document.createElement("span"), { className: "kind", textContent: text });
  tag.dataset.kind = kind;
  return tag;
};

// 세션 단추의 그림과 이름이다. 정규장은 해, 애프터장은 초승달, 프리장은 언덕 위로 반쯤 오른 해와 빛살이다. 해의 원판, 초승달, 반쯤 오른 해는 채우는 면(`f`)이다.
export const SESSION_ICON = {
  regular: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle class="f" cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/></svg>',
  after: '<svg viewBox="0 0 24 24" aria-hidden="true"><path class="f" d="M20 14.6A8.2 8.2 0 1 1 9.4 4a6.6 6.6 0 0 0 10.6 10.6Z"/></svg>',
  pre: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 20.5C6 17 9 16 12 16s6 1 10 4.5"/><path class="f" d="M7.5 16.6a4.5 4.5 0 0 1 9 0Z"/><path d="M12 6.2v2.6M5.4 9.6l1.7 1.7M18.6 9.6l-1.7 1.7"/></svg>',
};
export const SESSION_NAME = { regular: "정규장", after: "애프터마켓", pre: "프리마켓" };
// 정규장 값과 정규장 다음 세션(애프터장이나 프리장)의 값을 고르는 단추 한 쌍(`box`)이다. 지도와 종목 상세의 주가 카드, 주가 카드가 같이 쓴다.
// 단추는 글씨 대신 세션 그림을 그리고, 세션 이름을 단추의 이름(`aria-label`)과 풍선 글씨(`title`)로, 세션 종류를 `data-kind`로 단다.
// `pick(late)`는 사용자가 다른 단추를 누를 때 부르고, `late`는 정규장 다음 단추를 고르면 참이다. `mark(late)`는 고른 단추를 칠하고,
// `rename(kind, name)`은 정규장 다음 단추를 `kind` 세션(`pre`, `after`, `regular`)의 그림으로 바꾸고 이름을 `name`으로 단다.
// 리포트 날짜의 정규장 값(`regular`)이면 앞 단추를 숨겨 정규장 단추 하나만 남긴다.
export function sessionSeg(pick) {
  const box = Object.assign(document.createElement("div"), { className: "session" });
  box.innerHTML = `<button type="button" data-kind="regular" aria-label="정규장" title="정규장">${SESSION_ICON.regular}</button><button type="button"></button>`;
  const mark = (late) => [...box.children].forEach((button, i) => button.classList.toggle("on", !!i === late));
  box.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button || button.disabled || button.classList.contains("on")) return;
    feelPress();
    mark(button === box.lastElementChild);
    pick(button === box.lastElementChild);
  });
  const rename = (kind, name = SESSION_NAME[kind]) => {
    const button = box.lastElementChild;
    box.firstElementChild.hidden = kind === "regular";
    button.dataset.kind = kind;
    if (button.title === name) return;
    Object.assign(button, { innerHTML: SESSION_ICON[kind], title: name });
    button.setAttribute("aria-label", name);
  };
  return { box, mark, rename };
}
