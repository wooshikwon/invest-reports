// @ts-nocheck
export const signed = (v, digits = 2) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(digits)}`;
export const tone = (v) => v > 0 ? "up" : v < 0 ? "down" : "";
export const figure = (v) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
// 달러 값은 주가와 예측 카드처럼 앞에 $를 붙이고, 다른 단위는 값 뒤에 붙인다.
export const price = (v, unit) => unit === "달러" ? `$${figure(v)}` : `${figure(v)}${unit}`;
