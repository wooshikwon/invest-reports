// @ts-nocheck
export const signed = (v, digits = 2) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(digits)}`;
export const tone = (v) => v > 0 ? "up" : v < 0 ? "down" : "";
export const figure = (v) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
// 달러 값은 주가 카드처럼 앞에 $를 붙이고, 다른 단위는 값 뒤에 붙인다.
export const price = (v, unit) => unit === "달러" ? `$${figure(v)}` : `${figure(v)}${unit}`;
// 서울 시각 날짜 "YYYY-MM-DD"의 요일 한 글자.
export const weekday = (day) => "일월화수목금토"[new Date(`${day}T12:00:00+09:00`).getUTCDay()];
// 주요 이슈 해설과 종목별 뉴스 탭 첫 줄의 갱신 시각. `day`는 서울 시각 "YYYY-MM-DD", `hm`은 "HH:MM"이고 "마지막 업데이트 11/25 (수) 06:00 KST"처럼 쓴다.
export const updated = (day, hm) => `마지막 업데이트 ${+day.slice(5, 7)}/${+day.slice(8, 10)} (${weekday(day)}) ${hm} KST`;
