// @ts-nocheck
import { cache } from "./pull";
// 리포트 키가 없거나 형식이 다르면 목록에서 가장 늦은 나스닥 리포트를 연다. 목록에 나스닥 리포트가 없으면 열 리포트를 찾지 못했다고 적는다.
export let listed = null;
// `r/market.json`은 build.py가 지수마다 적는 상위 20종목의 이름, 주식 수, 일별 종가(`map`)다. 시장 페이지의 지수 지도가 쓴다.
export let marketed = null;
// `r/candles.json`은 build.py가 지수마다 날짜별로 적는 [시가, 고가, 저가] ÷ 종가 비율이다. 주가와 예측 카드가 봉 그림을 그릴 때 그날 종가에 곱한다.
export let candled = null;
// 리포트 본문은 이름마다 한 번만 받는다(`reportText`). 화면을 그리면 그 본문을 지우므로, 다시 돌아온 리포트는 서버에 바뀌었는지 다시 묻는다.
export const texts = {};
export const reportText = (name) => (texts[name] ||= fetch(`r/${name}/report.html`, { cache })
  .then((r) => { if (!r.ok) throw new Error(r.status); return r.text(); })
  .catch((error) => { delete texts[name]; throw error; }));
// 이슈 과거 맥락(`history`)과 요약 카드 값(`cards`)은 build.py가 `r/{키}/history.json`·`cards.json`에 따로 적고, 목록 항목의 `parts`에 그 이름을 적는다.
// `parts`에 이름이 없으면 받지 않고 `null`을 돌려준다. 그런 지난 리포트는 같은 값을 `report.html` 안의 `issue-history` 템플릿과 `#cards` 조각에 담고 있다.
// 본문처럼 이름마다 한 번만 받고, 화면을 그리면 지운다.
export const parts = {};
export const reportPart = (name, part, listing) => (listing[name]?.parts?.includes(part)
  ? (parts[`${name}/${part}`] ||= fetch(`r/${name}/${part}.json`, { cache })
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .catch((error) => { delete parts[`${name}/${part}`]; throw error; }))
  : Promise.resolve(null));
export function initData() {
  listed = fetch("r/index.json", { cache }).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
  marketed = fetch("r/market.json", { cache }).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
  candled = fetch("r/candles.json", { cache }).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
}
