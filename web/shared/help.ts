// @ts-nocheck
import { INDEX_NAME } from "./chrome";
import { key, report } from "./route";
// 두 지수의 한 눈에 보기 절이 함께 쓰는 설명 항목이다.
export const MAP_HELP = [
  ["칸 크기", "칸이 클수록 시가총액이 커요."],
  ["칸 색", "그 앞 거래일 종가보다 오르면 빨간색, 내리면 파란색이에요. 조금 움직이면 회색에 가깝고, 많이 움직일수록 색이 선명해요."],
  ["종목 설명", "지도 아래에 종목의 종가와 등락률, 업종, 하는 일을 보여줘요. 처음에는 시가총액 1위 종목이 나오고, 칸을 누르면 그 종목으로 바뀌어요."],
];
// 한 눈에 보기 절의 설명 항목은 리포트 지수마다 다르다.
export const GLANCE_HELP = {
  nasdaq: [
    ["종목", "나스닥 100에서 비중이 큰 20종목이에요. 나스닥 100 시가총액의 약 3분의 2를 차지해요. 알파벳은 두 종류 주식을 합쳐 한 칸에 보여줘요."],
    ...MAP_HELP,
  ],
  biotech: [
    ["종목", "나스닥 바이오테크놀로지 지수에서 비중이 큰 20종목이에요. 이 지수 시가총액의 약 절반을 차지해요."],
    ...MAP_HELP,
  ],
};
// 절 제목마다 설명 상자에 쓸 항목을 둔다. 항목마다 이름을 굵게 쓰고 그 아래에 설명을 쓴다. 지수와 예측 절은 `OUTLOOK_HELP`와 `CARD_HELP`가 항목을 만든다.
export const HELP = {
  "상세 이슈 해설": [
    ["이슈를 고르는 기준", "주가 예측에 영향이 큰 이슈부터 보여줘요. 이슈 하나를 빼고 다시 계산했을 때 예측이 크게 바뀔수록 영향이 커요."],
    ["상승 요인과 하락 요인", "이슈 때문에 주가 예측이 올랐는지 내렸는지 보여줘요. 나쁜 소식도 반등 가능성을 높이면 상승 요인이에요."],
    ["히스토리", "같은 이슈를 다룬 지난 리포트의 해설 제목이에요. 제목을 누르면 그날의 해설이 나와요."],
  ],
  "이벤트 캘린더": [
    ["이벤트 확률표", "앞으로 35일 안에 발표되는 이벤트마다 가능한 결과와 확률을 보여줘요. 이벤트는 주가에 반영되는 거래일에 모아요. 장 마감 뒤나 휴일에 나온 발표는 다음 거래일에 두고 발표일을 함께 적어요. 주가 경로 2만 개를 만들 때 이벤트 확률을 써요."],
    ["확률 변화", "어제 리포트의 확률과 오늘 확률의 차이를 %p로 보여줘요."],
    ["실제 결과", "결과가 나온 다음 날에는 실제로 일어난 결과를 표시해요."],
  ],
};
// 종목 뉴스 탭의 설명 항목. `index`는 보고 있는 리포트 지수다.
const NEWS_INDEX = { nasdaq: "나스닥 100", biotech: "나스닥 바이오테크놀로지 지수" };
export const NEWS_HELP = (index) => [
  ["기사를 고르는 기준", `${NEWS_INDEX[index] || "지수"}에서 비중이 큰 20종목의 해외 보도 가운데 주가를 움직였거나 움직일 사건만 기사로 써요. 새로운 사실이 나오지 않은 종목은 기사가 없어요. 여러 종목에 걸친 사건은 기사 한 편으로 써요.`],
  ["업데이트", "매일 오전 6시와 오후 6시(한국 시각)에 앞 회차 뒤에 나온 보도를 모아 기사를 올려요. 기사 아래 시각은 그 기사를 올린 회차의 시각이에요."],
  ["목록", "가장 최근 회차에 올라온 기사만 보여줘요. 회차가 다룬 12시간 동안 주가가 크게 움직인 종목(시작가 대비 최고가와 최저가 차이)의 기사부터 놓고, 위의 세 종목 기사는 그림과 함께 크게 보여줘요. 지난 기사는 종목 상세의 주요 뉴스에서 볼 수 있어요. 날짜를 되감아도 최신 회차의 기사가 나와요."],
  ["리포트와의 관계", "종목 뉴스는 리포트의 주가 예측에 쓰지 않아요."],
];
export const QUESTION = '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1"/>'
  + '<path d="M6.2 6.2a1.8 1.8 0 1 1 2.6 1.6c-.5.3-.8.6-.8 1.2v.4" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>'
  + '<circle cx="8" cy="11.6" r=".8" fill="currentColor"/></svg>';
// 그림 카드가 없는 리포트의 지수와 예측 설명. 첫 항목 이름은 카드 탭과 같은 리포트 지수의 이름이다.
export const OUTLOOK_HELP = (name) => [
  [name, "파란 실선은 예측 중앙값이에요. 파란 면에는 25거래일 뒤 가격이 25~75% 확률로 들어와요. 회색 점과 면은 지난 리포트의 예측이에요."],
  ["예측과 일정", "이슈와 이벤트를 반영한 경로 2만 개의 등락률 분포예요. 두 파란 선 사이에 경로의 가운데 50%가 들어와요."],
  ["권장 배율", "경로 2만 개의 한 달 평균 등락을 배율로 바꾼 분포예요. 파란 실선이 1.0(지수 추종)보다 왼쪽이면 하락 쪽 판단이고, 오른쪽이면 상승 쪽 판단이에요."],
];
// 그림 카드가 있는 리포트의 지수와 예측 설명. 판단 색 이름은 지수마다 다르다.
export const CARD_HELP = (ink) => [
  ["주가", `예측 단추를 켜면 25거래일 뒤까지의 예측을 주가 위에 그려요. ${ink} 실선은 예측 중앙값이고, ${ink} 면에는 25거래일 뒤 가격이 50% 확률로 들어와요. ${ink} 점 두 개는 예측을 시작한 애프터마켓 가격과 25거래일 뒤 예측 중앙값이에요. 예측을 켜면 큰 글씨가 25거래일 뒤 예측 중앙값으로 바뀌고, '현재' 표시는 가장 최근 가격에 머물러요. 예측을 켠 채 지난 날짜를 누르면 그날 리포트의 예측을 그려요. 회색 점선과 면은 지난 리포트의 예측이에요.`],
  ["예측과 일정", `이슈와 이벤트를 반영한 주가 경로 2만 개로 거래일마다 등락률 범위를 계산해요. 진한 면에 경로의 가운데 50%가, 옅은 면에 가운데 80%가 들어와요.`],
  ["권장 배율", `${ink} 세로선이 권장 배율이에요. 권장 배율이 1.0(지수 추종)보다 작으면 리포트가 하락을 예상한다는 뜻이고, 크면 상승을 예상한다는 뜻이에요.`],
];
export const INK = { nasdaq: "하늘색", biotech: "보라색" };
// 설명이 있는 절 제목 뒤에 물음표 단추를 넣는다. 단추는 글자를 담지 않으므로 절 제목 글자로 절을 찾는 `paginate`와 이벤트 캘린더 찾기가 그대로 동작한다. `section`이 절 제목 안을 바꿔 쓴 뒤에 부른다.
export function help() {
  report.querySelectorAll("h2").forEach((head) => {
    const title = head.textContent.trim(), index = key.split("-")[1];
    if (title !== "지수와 예측" && !HELP[title] && !(title === "한 눈에 보기" && GLANCE_HELP[index])) return;
    const items = title === "한 눈에 보기" ? GLANCE_HELP[index] : title !== "지수와 예측" ? HELP[title]
      : report.querySelector(".carousel.cards") ? CARD_HELP(INK[index] || "하늘색") : OUTLOOK_HELP(INDEX_NAME[index]);
    head.append(question(title, () => {
      const list = document.createElement("ul");
      items.forEach(([name, text]) => {
        const li = list.appendChild(document.createElement("li"));
        li.append(Object.assign(document.createElement("b"), { textContent: name }), text);
      });
      return [list];
    }));
  });
}

// 누르면 `title`을 제목으로, `body`가 돌려준 노드를 본문으로 쓴 설명 상자를 띄우는 물음표 단추.
export function question(title, body) {
  const button = document.createElement("button");
  button.className = "help";
  button.setAttribute("aria-label", `${title} 설명`);
  button.innerHTML = QUESTION;
  button.addEventListener("click", () => {
    const box = document.createElement("div");
    box.className = "help-card";
    const card = box.appendChild(document.createElement("div"));
    card.className = "card";
    const h3 = card.appendChild(document.createElement("h3"));
    h3.append(title);
    const close = h3.appendChild(Object.assign(document.createElement("button"), { textContent: "✕" }));
    close.setAttribute("aria-label", "닫기");
    card.append(...body());
    box.addEventListener("click", (event) => { if (event.target === box || close.contains(event.target)) box.remove(); });
    document.body.append(box);
  });
  return button;
}
