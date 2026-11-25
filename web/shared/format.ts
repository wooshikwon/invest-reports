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
// 종목 뉴스 목록의 회차 시각. 회차 시작 시각 "2026-11-19T18:00:00+09:00"에서 `now`까지 지난 시간을 "방금 전", "N분 전", "N시간 전", "N일 전", "N주 전", "N개월 전", "N년 전"으로 쓴다.
// 분·시간·일·주는 지난 시간을 단위로 내림해 세고, 개월과 년은 서울 날짜의 달력으로 센다. 지난달 같은 날짜가 지나야 "1개월 전"이므로 주는 "4주 전"까지 쓴다.
export const ago = (time, now = Date.now()) => {
  const minutes = Math.max(0, Math.floor((now - Date.parse(time)) / 6e4));
  if (minutes < 60) return minutes ? `${minutes}분 전` : "방금 전";
  if (minutes < 1440) return `${Math.floor(minutes / 60)}시간 전`;
  const seoul = new Date(now + 9 * 36e5);
  const months = (seoul.getUTCFullYear() - +time.slice(0, 4)) * 12 + seoul.getUTCMonth() + 1 - +time.slice(5, 7) - (seoul.getUTCDate() < +time.slice(8, 10) ? 1 : 0);
  if (months >= 12) return `${Math.floor(months / 12)}년 전`;
  if (months) return `${months}개월 전`;
  const days = Math.floor(minutes / 1440);
  return days < 7 ? `${days}일 전` : `${Math.floor(days / 7)}주 전`;
};
