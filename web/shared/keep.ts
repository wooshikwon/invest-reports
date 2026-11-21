// @ts-nocheck
// 사용자가 단추로 고른 화면 상태는 기기(`localStorage`)에 남기고, 다음에 열 때도 남긴 값으로 보인다. 값을 바꾸면 바꾼 값을 다시 남긴다.
// 남기는 상태는 내 투자 절의 금액 단위·총 자산 단추·그림 카드와 판단 보기 단추(`asset-view`), 거래 내역의 출처 필터와 조회 기간(`asset-view`),
// 주가 카드의 예측 단추(`aim`), 선·봉 단추(`chart-kind`), 머리 상자의 지수 단추(`index`)다. 상태마다 이름 하나에 값을 JSON으로 적는다.
export const kept = (name) => { try { return JSON.parse(localStorage.getItem(name)); } catch { return null; } };
export const keep = (name, value) => { try { localStorage.setItem(name, JSON.stringify(value)); } catch {} };
