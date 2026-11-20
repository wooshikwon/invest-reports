// @ts-nocheck
import { toCalendar } from "./report";
import { gaugeCard, indexInk } from "../shared/card";
import { INDEX_NAME, INDEX_TITLE, ticker } from "../shared/chrome";
import { candled } from "../shared/data";
import { tone } from "../shared/format";
import { subscribe } from "../shared/live";
import { slider } from "../shared/motion";
import { cardRewind } from "../shared/rewind";
import { key, report } from "../shared/route";
import { SESSION_NAME, afterEnd, closeAt, sessionAt, sessionSeg, sessionTag } from "../shared/session";
import { DIMS, PRICE, candleGroups, candleLate, candleOn, candleUnit, drawCandles, ease, kindButton, nowMark, shape, zoomDrag } from "../shared/svg";
import { feelPress } from "../shared/telegram";
// 요약의 Outlook 그림 자리에 12M + Predictions(지수와 예측), Montecarlo(일정과 예측), Outlook(권장 배율) 순서로 넘기는 묶음을 둔다.
// Montecarlo 그림은 원래 이벤트 캘린더 절에 있으므로 그 자리에서는 뺀다. 12M + Predictions가 없는 리포트는 두 장을 넘긴다.
// 묶음 위에는 그림 이름 탭을 둔다. 탭을 누르면 그 그림으로 넘기고, 넘기면 보고 있는 그림의 탭을 밝힌다.
// 그림 카드 값(`given`, `build.py`가 쓴 `r/{키}/cards.json`. 그 파일이 없는 지난 리포트는 리포트 끝의 `#cards`)이 있는 리포트는 그림 대신 주가와 예측, 일정, 권장 배율 카드 세 장을 넘긴다.
export function figures(date, given = null) {
  const data = report.querySelector("#cards");
  data?.remove();
  const cards = given ?? (data && JSON.parse(data.textContent));
  if (cards) {
    const set = summaryCards(cards, date);
    ticker.innerHTML = set.quote();
    subscribe((found) => {
      set.live(found, key.split("-")[1]);
      ticker.innerHTML = set.quote();
    });
    const bar = document.createElement("div");
    bar.className = "tabs";
    set.names.forEach((name, i) => {
      const button = Object.assign(document.createElement("button"), { textContent: name });
      button.addEventListener("click", () => box.go(i));
      bar.appendChild(button);
    });
    const change = (i) => [...bar.children].forEach((button, j) => button.classList.toggle("on", i === j));
    const head = report.querySelector("h2"), box = slider(set.slides, head, { change, name: "cards", feel: true });
    box.prepend(bar);
    cardRewind(box, date, set);
    return;
  }
  const pick = (name) => [...report.querySelectorAll("img")].find((img) => img.getAttribute("src").includes(`/${name}-`));
  const chart = pick("chart"), tree = pick("tree"), predict = pick("predict");
  if (!chart || !tree) return;
  const shown = [[predict, "지수와 예측"], [tree, "일정"], [chart, "권장 배율"]].filter(([img]) => img);
  shown.forEach(([img]) => (img.closest("p") || img).remove());
  const bar = document.createElement("div");
  bar.className = "tabs";
  shown.forEach(([, name], i) => {
    const button = Object.assign(document.createElement("button"), { textContent: name });
    button.addEventListener("click", () => box.go(i));
    bar.appendChild(button);
  });
  const change = (i) => [...bar.children].forEach((button, j) => button.classList.toggle("on", i === j));
  const box = slider(shown.map(([img]) => [img]), report.querySelector("h2"), { change, feel: true });
  box.prepend(bar);
}

// 요약 절의 그림 카드 세 장(주가와 예측, 일정과 예측, 권장 배율)을 만든다. 카드 이름 탭에는 "주가와 예측", "일정", "권장 배율"로 쓴다. `data`는 `build.py` `summary_cards`의 값이다.
// 돌려준 `show(frame)`은 되감기 슬라이더가 고른 날짜의 판단(`cards.json`의 프레임)으로 카드를 다시 그린다.
// 주가와 예측 카드의 종가 바탕(날짜·종가·지난 예측)은 늘 리포트 날짜의 값이고, 고른 날짜의 판단만 그 위에 바꿔 그린다.
export function summaryCards(data, date) {
  // 카드는 모두 같은 높이(`H`)의 그림에 같은 높이(`B`)의 가로축을 긋는다.
  const dates = data.dates, hist = data.history, W = 320, H = 236, B = 212;
  // 예측 선과 면, 범위 값 글씨는 지수색 그라데이션(`color`)으로 칠한다.
  const color = indexInk(W);
  const fmt = (v) => `$${Math.round(v).toLocaleString("en-US")}`;
  const signed = (v, digits = 1) => `${v > 0 ? "+" : v < 0 ? "\u2212" : ""}${Math.abs(v).toFixed(digits)}`;
  const path = (points) => `M${points.map(([x, y]) => `${x} ${y}`).join("L")}`;
  const last = dates.length - 1, close = dates.indexOf(data.base_date);
  // 카드마다 위 줄 아래 이름 줄(`title`)에 "나스닥 100"처럼 지수 이름(`INDEX_TITLE`)을 쓴다. 이름 줄이 같은 높이를 차지해 카드를 넘겨도 값과 그림이 같은 높이에 있다.
  const card = (ctx) => {
    const c = gaugeCard(ctx, W, H);
    c.title = c.box.insertBefore(Object.assign(document.createElement("div"), { className: "top title" }), c.box.querySelector(".val"));
    c.title.append(Object.assign(document.createElement("span"), { className: "name", textContent: INDEX_TITLE[key.split("-")[1]] || INDEX_NAME[key.split("-")[1]] }));
    return c;
  };
  // 날짜 지점(`point`)은 이 리포트 판단의 기준 가격 날짜 다음 거래일(`days[1]`)이다. 앱은 날짜를 세지 않고 리포트의 `days`와 실시간 값의 `point`로 지점을 찾는다.
  // `found`는 이 지수의 지점별 실시간 값(`live.ts`의 `points`)이고 `loaded`는 지수의 1분 값(`index`)이다.
  const point = data.days[1];
  let found = {}, loaded = null;
  // 프레임 `f`의 판단에서 기준 가격 날짜 다음 지점의 값 [값, 위 줄 글씨, 세션(`pre`, `after`, `regular`), 체결 뉴욕 시각, 실시간 값]. 없으면 null이다.
  // 지점의 정규장 값(`regular`)이 있으면 그 값이고, 없으면 프리장 값(`pre`), 없으면 앞 세션의 애프터장 값(`after`)이며, 없으면 판단의 기준 가격(애프터장 마지막 값)이다.
  // 값은 기준 가격 날짜 종가에 실시간 값의 비율을 곱한 값이다. 나스닥의 선물 시간대 애프터장 값(`basis`가 `futures`)은 위 줄 글씨에 "선물 가격"을 덧붙인다.
  // 리포트 날짜 판단의 종가가 이미 있는 지점(`dates`에 든 지점)에는 판단의 종가를 먼저 그리고 실시간 값을 쓰지 않는다. 지난 날짜의 판단은 그날 프리장 값만 쓴다.
  const nextOf = (f) => {
    const own = f.days[1], rec = f.day === date && dates.includes(own) ? {} : found[own] ?? {}, base = hist[dates.indexOf(f.base_date)];
    const pick = f.day === date ? rec : { pre: rec.pre };
    if (pick.regular?.ratio != null) return [base * pick.regular.ratio, sessionAt("정규장", pick.regular.time), "regular", pick.regular.time, pick.regular];
    if (pick.pre?.ratio != null) return [base * pick.pre.ratio, sessionAt("프리마켓", pick.pre.time), "pre", pick.pre.time, pick.pre];
    if (pick.after?.ratio != null) {
      const text = sessionAt("애프터마켓", pick.after.time);
      return [base * pick.after.ratio, pick.after.basis === "futures" ? `${text} · 선물 가격` : text, "after", pick.after.time, pick.after];
    }
    return [f.base, sessionAt("애프터마켓", afterEnd(f.base_date)), "after", afterEnd(f.base_date), null];
  };
  const upcoming = () => nextOf(data);

  // 주가와 예측 카드(`price`): 이름 줄 오른쪽에 예측 단추와 세션 단추를 둔다.
  // 그림 아래 −·+ 단추로 종가를 그릴 기간을 고른다. 기간은 3년, 2년, 1년, 6개월, 3개월 다섯 단계이고, +는 한 단계 짧게, −는 한 단계 길게 바꾼다.
  // 기간은 가로축 전체의 길이다. 단추 사이의 점 묶음은 누른 채 끌어 기간을 바로 고른다(`zoomDrag`).
  // 처음에는 가장 짧은 3개월을 그린다. 봉 비율(`r/candles.json`)이 있으면 그 줄 오른쪽 끝에 선·봉 단추(`kindButton`)를 두고,
  // 봉 그림이면 종가 선 대신 3년·2년은 월봉, 1년은 주봉, 6개월·3개월은 일봉을 그린다.
  // 봉 그림이면 리포트 날짜에 고른 정규장 다음 세션 값을 다음 거래일이 든 기간의 흐린 잠정 봉(`candleLate`)으로 그린다.
  // 카드는 되감기 슬라이더가 고른 날짜와 관계없이 종가를 마지막 정규장 종가까지 그리고, 예측을 끈 카드는 고른 날짜의 값에 '현재' 표시(`nowMark`)를 찍는다.
  // '현재' 표시는 고른 날짜 판단의 기준 가격 날짜 종가에 찍고, 봉 그림이면 그 종가가 든 봉의 고가 위에 찍는다.
  // 그 종가가 예측을 켠 그림 왼쪽 끝 밖에 있으면 그 종가가 드는 가장 짧은 기간으로 넓히고, + 단추로는 그 종가가 빠지는 기간까지 줄이지 않는다.
  // 위 줄에 그 종가 날짜를, 가운데 줄에 그 종가와 전날 대비 등락률을 정규장 등락률 색(`tone`)의 점과 글씨로 적는다.
  // 기준 가격 날짜 다음 세션 값이 있으면 이름 줄 오른쪽 끝에 정규장·애프터장이나 정규장·프리장 단추를 둔다. 지난 날짜의 다음 세션 값은 그날 프리장 값이 있으면 그 값이고, 없으면 그날 판단의 기준 가격이다.
  // 애프터장·프리장·정규장 값은 기준 가격 날짜 종가에 실시간 값(`points`)의 비율을 곱한 값이며, 정규장, 프리장, 애프터장 순으로 있는 값을 쓴다.
  // 정규장 다음 단추를 고르면 위 줄에 그 세션 이름과 시각을, 가운데 줄에 그 값과 정규장 종가 대비 등락률을 회색으로 적는다.
  // 리포트 날짜의 프리장 값이 정규장 값(`phase`가 `regular`)이면 단추를 정규장 단추 하나로 줄이고, 위 줄에 정규장과 시각을, 가운데 줄에 그 값과 앞 종가 대비 등락률을 등락률 색으로 적는다.
  // 선 그림이면 정규장 다음 세션 값은 세션과 체결 시각에 관계없이 다음 거래일 자리에 '현재' 표시로 찍어 고른 날짜의 종가 점에서 점선으로 잇는다.
  // 봉 그림이면 그 값의 '현재' 표시는 다음 거래일이 든 봉의 고가 위에 찍는다.
  // 예측을 끈 카드는 가장 늦은 리포트의 리포트 날짜에 가장 늦은 세션을, 지난 날짜와 지난 리포트는 정규장을 고른다. 단추를 누르면 되감기 슬라이더가 다른 날짜를 고를 때까지 누른 세션을 유지한다.
  // 예측 단추(`aim`)를 켜면 고른 날짜 판단의 예측과 지난 리포트의 예측을 그린다. 처음에는 끈 채로 연다.
  // 켠 카드는 고른 날짜 판단에 예측이 있으면 위 줄에 "25거래일 뒤 예측 중앙값"을, 가운데 줄에 그 값을 지수색 그라데이션으로 쓰고 지수색 점 뒤에 기준 가격 대비 등락률을 적는다.
  // 켠 카드는 되감기 슬라이더가 고른 날짜와 관계없이 '현재' 표시를 리포트 날짜의 가장 늦은 세션 값(`upcoming()`)에, 그 값이 없으면 마지막 정규장 종가에 찍고,
  // 세션 단추를 모두 끈다. 되감기 슬라이더는 예측만 고른 날짜 판단의 예측으로 바꾼다.
  // 끈 카드의 가로축은 마지막 종가 다음 거래일에서 끝나고, 켠 카드의 가로축은 마지막 종가 뒤 25거래일에서 끝난다. 그림 왼쪽 끝도 같은 거래일 수만큼 옮겨 기간을 지킨다.
  // 단추를 누르면 기간을 바꿀 때와 같은 곡선으로 가로축과 세로 범위를 옮기면서 예측을 서서히 나타내거나 지운다.
  // 판단의 예측은 기준 가격 점에서 출발하는 25~75% 범위와 50% 선이다. 기준 가격 점은 애프터마켓·프리마켓 '현재' 표시처럼 기준 가격 날짜 다음 거래일 자리에 찍고,
  // 25거래일 뒤 값은 그 거래일 자리에 찍으며, 그 사이 날은 두 자리 사이에 고르게 놓는다.
  // 기준 가격 점과 25거래일 뒤 50% 값의 점은 지수색으로 찍고, 기준 가격 점은 종가와 잇지 않는다. 지난 리포트의 예측은 회색 점선과 면으로 그린다.
  // 고른 날짜 판단에 예측이 없으면 지난 리포트의 예측만 그리고, 머리 글씨에는 '현재' 표시의 값을 끈 카드와 같은 모양으로 적는다.
  const price = (() => {
    const c = card(""), s = c.svg, clipId = "price-clip", title = c.title;
    c.box.querySelector(".val b").className = "";
    let late = false, chosen = false, ext = null, aim = false;
    // 고른 날짜 값의 정규장 다음 세션 [값, 위 줄 글씨, 세션(`pre`, `after`, `regular`)]. 없으면 null이다. 리포트 날짜는 `upcoming()`이고,
    // 지난 날짜의 정규장 다음 세션은 그날 프리장 값의 앞 세션이 그날 판단의 기준 가격 날짜이면 그 프리장 값이고, 아니면 그날 판단의 기준 가격인 애프터장 값이다.
    const extra = (f) => nextOf(f);
    const toggle = Object.assign(document.createElement("button"), { type: "button", className: "aim", innerHTML: "<span>예측</span>" });
    title.append(toggle);
    toggle.setAttribute("aria-pressed", "false");
    const seg = sessionSeg((on) => { late = on; chosen = true; show(frame); });
    // `stop`은 '현재' 표시를 찍는 고른 날짜의 거래일 번호다. `ahead`는 예측 단추를 켠 정도(끄면 0, 켜면 1)이고, 단추를 누르는 동안 그 사이 값을 받는다.
    // 가로축 오른쪽 끝(`xmax`)은 끄면 마지막 종가 다음 거래일, 켜면 마지막 종가 뒤 25거래일이다.
    // 기간(`DAYS`)마다 그림 왼쪽 끝(`start`)은 가로축 마지막 거래일(`xmax - 1`)에서 그 거래일 수만큼 앞이다.
    const L = 4, R = W - 4, T = 22, DAYS = [756, 504, 252, 126, 63];
    let stop = last, ahead = 0, seen = 0, head = () => {};
    const xmax = (r) => last + 1 + 24 * r, start = (k, r) => Math.max(0, xmax(r) - 1 - DAYS[k]);
    let span = DAYS.length - 1, frame = null, raf = 0, ratios = null;
    // 고른 날짜의 종가가 예측을 켠 그림 안에 드는 가장 짧은 기간의 번호다.
    const most = () => { let k = DAYS.length - 1; while (k > 0 && stop < start(k, 1)) k--; return k; };
    const zoom = c.foot.appendChild(Object.assign(document.createElement("div"), { className: "zoom" }));
    zoom.innerHTML = `<button type="button" aria-label="기간 늘리기">−</button><span class="steps">${"<i></i>".repeat(DAYS.length)}</span><button type="button" aria-label="기간 줄이기">+</button>`;
    const [wider, narrower] = zoom.querySelectorAll("button");
    const level = () => {
      wider.disabled = span === 0;
      narrower.disabled = span >= most();
      zoom.querySelectorAll(".steps i").forEach((dot, i) => dot.classList.toggle("on", i === span));
    };
    level();
    // 봉 그림이면 참이다.
    const candle = () => candleOn && !!ratios;
    candled.then((found) => {
      const days = found[key.split("-")[1]];
      if (!days) return;
      ratios = dates.map((day) => days[day] ?? null);
      zoom.append(kindButton(() => { cancelAnimationFrame(raf); raf = 0; tween(span, span, 1); }));
      if (candleOn && frame) tween(span, span, 1);
    });
    // 날짜 지점의 잠정 봉 값. 정규장 값은 앞 세션 종가 대비 비율로 받은 시가·고가·저가·종가(`ohlc`)로 등락 색 봉을 그리고, 애프터장·프리장 값은 회색 봉을 그린다.
    const liveBar = (shown) => {
      const o = shown[2] === "regular" ? shown[4]?.ohlc : null, base = hist[close];
      return o ? { open: base * o.open, high: base * o.high, low: base * o.low, close: base * o.close, gray: false } : { close: shown[0], gray: shown[2] !== "regular" };
    };
    const past = (data.past ?? []).map(([x, lo, mid, hi]) => ({ x, lo, mid, hi }));
    const at = (f) => dates.indexOf(f.base_date);
    // 기간마다 세로 범위: 보이는 종가(봉 그림이면 보이는 봉의 고가와 저가)·정규장 다음 세션 값을 담고, 예측을 켰으면(`r`가 0보다 크면) 예측 면과 지난 예측도 담는다.
    // 최저 점 아래에는 글씨가 들어갈 20px을 비운다.
    const range = (x0, r) => {
      const shown = candle() ? candleGroups(dates, hist, ratios, candleUnit(DAYS[span]), last).filter((group) => group[1] >= x0).flatMap((group) => [group[3], group[4]]) : hist.slice(x0, last + 1);
      const band = (r > 0 && frame.predict) || { q25: [], q75: [] }, before = r > 0 ? past : [], more = ext ? [ext[0], ...[liveBar(ext).high, liveBar(ext).low].filter((v) => v != null)] : [];
      let lo = Math.min(...shown, ...band.q25, ...before.map((q) => q.lo), ...more);
      const hi = Math.max(...shown, ...band.q75, ...before.map((q) => q.hi), ...more);
      const low = Math.min(...shown);
      lo = Math.min(lo, low - (hi - low) * 20 / (B - T - 20));
      return [lo, hi];
    };
    // `x0`는 그림 왼쪽 끝의 거래일 번호이고, `r`는 예측을 그리는 정도다. 기간을 옮기거나 예측 단추를 누르는 동안에는 소수 값을 받아 그 사이를 이어 그리고,
    // 예측의 선과 면, 점은 `r`만큼 흐리게 그린다.
    const draw = (x0, lo, hi, marks, r) => {
      s.replaceChildren();
      const f = frame, fx = at(f), p = r > 0 ? f.predict : null, end = xmax(r);
      const X = (i) => L + (i - x0) / (end - x0) * (R - L), Y = (v) => B - (v - lo) / (hi - lo) * (B - T);
      // 덧붙인 잠정 봉이 그림 오른쪽 끝에서 3px까지 나가므로 그 3px도 그린다.
      const clip = shape("clipPath", { id: clipId });
      clip.append(shape("rect", { x: L, y: 0, width: R - L + 3, height: B }));
      s.append(clip);
      const g = s.appendChild(shape("g", { "clip-path": `url(#${clipId})` }));
      // 달 이름은 6월·12월, 분기 달, 나머지 달 순서로 남긴다. 이름 사이 간격이 42px보다 좁아지면 아래 단계의 달 이름부터 흐리게 지운다.
      const perMonth = 21 * (R - L) / (end - x0), fade = (months) => Math.max(0, Math.min(1, (months * perMonth - 30) / 12));
      let month = "";
      dates.forEach((d, i) => {
        if (d.slice(0, 7) === month) return;
        month = d.slice(0, 7);
        const x = X(i), m = +d.slice(5, 7), opacity = fade(m % 6 === 0 ? 6 : m % 3 === 0 ? 3 : 1);
        if (x >= L + 12 && opacity > 0) s.append(shape("text", { x, y: B + 17, "font-size": 11, fill: DIMS, "text-anchor": "middle", opacity }, `${m}월`));
      });
      s.append(shape("line", { x1: L, x2: R, y1: B, y2: B, stroke: DIMS, "stroke-width": 1 }));
      if (r > 0 && past.length) {
        g.append(shape("path", { d: `${path(past.map((q) => [X(q.x), Y(q.lo)]))}L${past.slice().reverse().map((q) => `${X(q.x)} ${Y(q.hi)}`).join("L")}Z`, fill: "rgba(167, 171, 176, .16)", opacity: r }));
        g.append(shape("path", { d: path(past.map((q) => [X(q.x), Y(q.mid)])), fill: "none", stroke: "#A7ABB0", "stroke-width": 1.2, "stroke-dasharray": "2 3", opacity: .8 * r }));
      }
      const i0 = Math.max(0, Math.floor(x0)), width = 1.4 - .4 * Math.max(0, Math.min(1, (last - x0 - 63) / 693));
      const stroke = { fill: "none", stroke: PRICE, "stroke-width": width, "stroke-linejoin": "round" };
      // 봉 그림이면 그림 왼쪽 끝부터 마지막 종가까지 보이는 봉이다.
      const unit = candleUnit(DAYS[span]), groups = candle() ? candleGroups(dates, hist, ratios, unit, last).filter((group) => group[1] >= i0) : null;
      // 최고·최저 글씨는 기간이 정해진 뒤에만 그리고, 가운데를 그림 양 끝에서 30px 안쪽에 둔다. 봉 그림이면 점 없이 가장 높은 고가와 가장 낮은 저가를 봉 위아래에 적는다.
      const extremes = () => {
        const group = s.appendChild(shape("g", { class: "marks" }));
        if (groups) {
          const high = groups.reduce((a, b) => (b[3] > a[3] ? b : a)), low = groups.reduce((a, b) => (b[4] < a[4] ? b : a));
          [[high, high[3], -5, "최고"], [low, low[4], 13, "최저"]].forEach(([[a, b], v, dy, text]) => {
            group.append(shape("text", { x: Math.min(Math.max(X((a + b) / 2), L + 30), R - 30), y: Y(v) + dy, "font-size": 11, fill: DIMS, "text-anchor": "middle" }, `${text} ${fmt(v)}`));
          });
          return;
        }
        const shown = hist.slice(i0, last + 1);
        [[i0 + shown.indexOf(Math.max(...shown)), -7, "최고"], [i0 + shown.indexOf(Math.min(...shown)), 15, "최저"]].forEach(([i, dy, text]) => {
          group.append(shape("circle", { cx: X(i), cy: Y(hist[i]), r: 2.5, fill: PRICE }));
          group.append(shape("text", { x: Math.min(Math.max(X(i), L + 30), R - 30), y: Y(hist[i]) + dy, "font-size": 11, fill: DIMS, "text-anchor": "middle" }, `${text} ${fmt(hist[i])}`));
        });
      };
      const step = (R - L) / (end - x0);
      // 예측의 0번째와 1번째 값은 기준 가격 날짜 다음 날짜 지점에 함께 놓고, t번째 값은 t번째 날짜 지점에 놓는다.
      const xs = p && p.q50.map((_, k) => X(fx + Math.max(1, k)));
      if (p) g.append(shape("path", { d: `${path(xs.map((x, k) => [x, Y(p.q25[k])]))}L${xs.slice().reverse().map((x, k) => `${x} ${Y(p.q75[xs.length - 1 - k])}`).join("L")}Z`, fill: color, opacity: .22 * r }));
      // 봉 그림이면 리포트 날짜에 고른 정규장 다음 세션 값만 잠정 봉으로 덧붙인다. `center(i)`는 거래일 `i`가 든 봉의 가운데 x이고,
      // `mark(i, y)`는 '현재' 표시의 높이로, 선 그림이면 값의 높이 `y`, 봉 그림이면 그 봉의 고가 5px 위다.
      const drawn = groups && (ext && stop === last ? candleLate(groups, dates, unit, liveBar(ext), point) : groups);
      const centers = drawn ? drawCandles(g, drawn, X, Y, step, R + 3) : null;
      const bar = (i) => Math.max(0, drawn.findLastIndex(([a]) => a <= i));
      const center = (i) => (drawn ? centers[bar(i)] : X(i)), mark = (i, y) => (drawn ? Y(drawn[bar(i)][3]) - 5 : y);
      if (!drawn) g.append(shape("path", { d: path(hist.slice(i0, last + 1).map((v, k) => [X(i0 + k), Y(v)])), ...stroke }));
      // 예측의 시작점과 끝점은 '현재' 표시보다 위에 그린다.
      const ends = p ? shape("g", { opacity: r }) : null;
      if (p) {
        s.append(shape("path", { d: path(xs.map((x, k) => [x, Y(p.q50[k])])), fill: "none", stroke: color, "stroke-width": 1.4, "stroke-linejoin": "round", opacity: r }));
        [[xs[0], f.base], [xs.at(-1), p.q50.at(-1)]].forEach(([cx, v]) => ends.append(shape("circle", { cx, cy: Y(v), r: 2.5, fill: color, stroke: "#171719", "stroke-width": 1 })));
        s.append(ends);
      }
      if (marks) extremes();
      const close = [center(stop), Y(hist[stop])];
      const now = s.insertBefore(shape("g"), ends);
      // 날짜 슬라이더가 고른 종가가 아직 그림 왼쪽 끝 앞이면(기간을 넓히는 도중) '현재' 표시를 찍지 않는다.
      if (stop < i0) return;
      if (!ext) return nowMark(now, close[0], mark(stop, close[1]), "regular");
      // 선 그림이면 정규장 다음 세션 값은 다음 거래일 자리에 찍어 고른 날짜의 종가 점에서 점선으로 잇는다.
      const next = [center(stop + 1), Y(ext[0])];
      if (!drawn) {
        g.append(shape("path", { d: path([close, next]), ...stroke, "stroke-dasharray": "2 2" }));
        now.append(shape("circle", { cx: close[0], cy: close[1], r: 2.5, fill: PRICE }));
      }
      nowMark(now, next[0], mark(stop + 1, next[1]), ext[2]);
    };
    // `from` 기간과 예측 정도 `r0`에서 `to` 기간과 `r1`로 가는 도중 `t`(0~1) 지점의 그림. 왼쪽 끝과 오른쪽 끝, 세로 범위를 같은 곡선으로 옮기고, 넓히는 동안 새로 들어온
    // 과거 종가가 범위 밖이면 범위를 그만큼 먼저 넓혀 선이 가로축 아래로 내려가지 않게 한다.
    const tween = (from, to, t, r0 = ahead, r1 = ahead) => {
      const e = ease(t), r = r0 + (r1 - r0) * e, [a, b] = [start(from, r0), start(to, r1)], [a0, a1] = range(a, r0), [b0, b1] = range(b, r1);
      const x0 = a + (b - a) * e, [c0, c1] = range(Math.max(0, Math.floor(x0)), Math.min(r0, r1));
      seen = r;
      draw(x0, Math.min(a0 + (b0 - a0) * e, c0), Math.max(a1 + (b1 - a1) * e, c1), t >= 1, r);
    };
    const animate = (from, r0) => {
      cancelAnimationFrame(raf);
      const duration = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 550, t0 = performance.now();
      const step = (now) => { const t = duration ? Math.min(1, (now - t0) / duration) : 1; tween(from, span, t, r0, ahead); raf = t < 1 ? requestAnimationFrame(step) : 0; };
      raf = requestAnimationFrame(step);
    };
    const move = (by) => {
      const from = span;
      span = Math.max(0, Math.min(most(), span + by));
      if (span === from) return;
      level();
      animate(from, seen);
    };
    wider.addEventListener("click", () => move(-1));
    narrower.addEventListener("click", () => move(1));
    zoomDrag(zoom.querySelector(".steps"), () => span, (i) => move(i - span));
    toggle.addEventListener("click", () => {
      feelPress();
      aim = !aim;
      ahead = aim ? 1 : 0;
      toggle.classList.toggle("on", aim);
      toggle.setAttribute("aria-pressed", aim);
      const from = span;
      settle();
      animate(from, seen);
    });
    // '현재' 표시를 찍을 값과 세션 단추, 머리 글씨를 정한다. 예측을 켠 카드는 가장 늦은 값을 쓰고 세션 단추를 모두 끈다.
    // 예측을 끈 카드는 가장 늦은 리포트의 리포트 날짜에 가장 늦은 세션을, 지난 날짜와 지난 리포트는 정규장을 고르고, 사용자가 누른 단추가 있으면 그 세션을 쓴다.
    // 리포트 날짜의 정규장 값은 늘 고른 채로 둔다.
    const settle = () => {
      const f = frame, now = f.day === date;
      stop = now || aim ? last : at(f);
      span = Math.min(span, most());
      level();
      const session = Math.round((hist[stop] / hist[stop - 1] - 1) * 1e4) / 100, shown = aim ? upcoming() : extra(f), regular = shown?.[2] === "regular";
      if (!aim && (!chosen || regular)) late = !!shown && now && (regular || !document.documentElement.classList.contains("past"));
      ext = shown && (aim || late) ? shown : null;
      seg.rename(shown?.[2] ?? "after");
      seg.mark(aim ? null : late);
      [...seg.box.children].forEach((button) => (button.disabled = aim));
      if (shown) title.append(seg.box); else seg.box.remove();
      head = () => {
        const p = aim ? f.predict : null, move = ext && Math.round((ext[0] / hist[stop] - 1) * 1e4) / 100, end = p?.q50.at(-1);
        c.box.classList.toggle("ext", !!ext && !regular && !p);
        c.box.classList.toggle("ink", !!p);
        c.box.querySelector(".val b").className = p ? "ink" : "";
        c.box.querySelector(".state").className = `state ${p ? "" : ext ? (regular ? tone(move) : "") : tone(session)}`;
        if (p) c.head(`${signed((end / f.base - 1) * 100)}%`, fmt(end), "25거래일 뒤 예측 중앙값");
        else if (ext) c.head(`${signed(move, 2)}%`, fmt(ext[0]), sessionTag(ext[2], ext[1]));
        else c.head(`${signed(session, 2)}%`, fmt(hist[stop]), sessionTag("regular", sessionAt("정규장", closeAt(dates[stop]))));
      };
      head();
    };
    // 되감기 슬라이더가 다른 날짜를 고르면 사용자가 고른 단추를 지운다.
    const show = (f) => {
      if (f !== frame) chosen = false;
      frame = f;
      const from = span;
      settle();
      // 고른 날짜의 종가가 그림 밖으로 나가 기간을 넓혔으면 − 단추처럼 그림을 이어 옮긴다. 기간을 옮기는 도중이면 다음 장면이 고른 날짜로 그린다.
      if (span !== from) animate(from, seen);
      else if (!raf) tween(span, span, 1);
    };
    return { box: c.box, show };
  })();

  // 일정과 예측: 등락률 분위수의 10~90% 옅은 면과 25~75% 면, 50% 실선을 주가와 예측 카드의 예측과 같은 지수색으로 그린다. 위쪽 번호는 이슈 일정이 있는 날이고,
  // 마지막 거래일에는 일정이 없어도 번호를 달고, 처음에는 첫 번호를 고른다. 번호를 누르면 위 값을 그날의 25~75% 등락률로 바꾸고
  // 세로선과 범위 끝이 만나는 곳에 그날의 등락률을 적는다. 그림 아래 줄 가운데에는 고른 일정의 날짜와 이름을 적고, 이름이 줄을 넘으면 말줄임표로 줄인다.
  // 그 줄 양옆의 꺽쇠를 누르면 앞뒤 일정을 고르고, 일정 이름을 누르면 같은 페이지 아래의 이벤트 캘린더에서 같은 거래일을 연다(`toCalendar`).
  // 지난 날짜를 고르면 그날 기준 가격 뒤의 실제 종가 등락률을 흰 선으로 그린다. 등락률은 고른 날짜 판단의 기준 가격 대비 값이다.
  // 선의 끝은 리포트 날짜를 고르면 기준 가격 날짜의 정규장 종가이고, 지난 날짜를 고르면 실제 종가 선이 기준 가격 날짜까지 닿을 때 그 선의 끝이다.
  // 리포트 날짜 판단의 기준 가격 날짜 다음 세션 값(`upcoming()`)이 있으면 그 끝 종가 점에서 세션 값까지 점선으로 잇고 세션 값에 '현재' 표시를 찍는다.
  // 세션 값은 정규장 종가(16:00 ET)에서 체결 뉴욕 시각까지 지난 시간만큼 거래일 자리를 옮겨 놓는다. 세션 값이 없으면 끝 종가에 정규장 '현재' 표시를 찍는다.
  // 세션 값은 늘 리포트 날짜의 가장 늦은 값이므로 고른 날짜와 관계없이 같은 값을 그리고, 세션 단추를 두지 않는다.
  const tree = (() => {
    const c = card("25거래일 뒤 범위"), s = c.svg;
    const L = 4, R = W - 4, T = 38;
    const box = c.foot.appendChild(Object.assign(document.createElement("div"), { className: "evbox" }));
    const chevron = (d, label) => Object.assign(document.createElement("button"), { type: "button", ariaLabel: label,
      innerHTML: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="${d}"/></svg>` });
    const prev = chevron("M10 3 5 8l5 5", "이전 일정"), next = chevron("M6 3l5 5-5 5", "다음 일정");
    const line = Object.assign(document.createElement("span"), { className: "t" });
    box.append(prev, line, next);
    let frame = null, pick = null, events = [], scale = null;
    prev.addEventListener("click", () => { if (pick > 0) { pick -= 1; mark(); } });
    next.addEventListener("click", () => { if (pick < events.length - 1) { pick += 1; mark(); } });
    line.addEventListener("click", () => {
      const [d, names] = events[pick];
      if (!names.length || !toCalendar) return;
      feelPress();
      toCalendar(frame.days[d]);
    });
    const percent = (v) => [signed(v), Object.assign(document.createElement("small"), { textContent: "%" })];
    const mark = () => {
      s.querySelectorAll("[data-ev]").forEach((node) => {
        const on = +node.dataset.ev === pick;
        if (node.tagName === "line") {
          node.setAttribute("stroke", on ? color : "rgba(122, 130, 140, .35)");
          node.setAttribute("stroke-opacity", on ? .7 : 1);
        }
        else if (node.tagName === "circle") node.setAttribute("fill", on ? color : "#2A2D33");
        else node.setAttribute("fill", on ? "#0b1a24" : "#EAEAEA");
      });
      const [d, names, day] = events[pick], pct = frame.tree.pct, { X, Y, values } = scale;
      // 고른 세로선이 10~90%와 25~75% 범위의 위아래 끝과 만나는 네 곳에 작은 점을 찍고 그날의 등락률을 회색으로 적는다. 10~90% 범위의 점과 값은 더 연하게 그린다. 글씨는 세로선이 그림 왼쪽 반에 있으면
      // 오른쪽에, 오른쪽 반에 있으면 왼쪽에 둔다. 위아래 글씨가 12px보다 가까우면 네 글씨의 평균 높이를 지키며 12px 간격으로 벌린다.
      const right = X(d) < (L + R) / 2, ys = ["90", "75", "25", "10"].map((q) => Y(pct[q][d]) + 4);
      const at = ys.reduce((out, y) => [...out, out.length ? Math.max(y, out[out.length - 1] + 12) : y], []);
      const shift = (ys.reduce((a, b) => a + b) - at.reduce((a, b) => a + b)) / at.length;
      const ink = (q) => q === "25" || q === "75" ? "#A7ABB0" : "#45494F";
      values.replaceChildren(...["90", "75", "25", "10"].map((q) => shape("circle", { cx: X(d), cy: Y(pct[q][d]), r: 1.6, fill: ink(q) })),
        ...["90", "75", "25", "10"].map((q, k) => shape("text", { x: X(d) + (right ? 5 : -5), y: at[k] + shift, "font-size": 11, fill: ink(q),
        "text-anchor": right ? "start" : "end", stroke: "#171719", "stroke-width": 3, "stroke-linejoin": "round", "paint-order": "stroke" }, `${signed(pct[q][d])}%`)));
      c.head("", [...percent(pct["25"][d]), Object.assign(document.createElement("span"), { className: "sep", textContent: "~" }), ...percent(pct["75"][d])],
        `${d}거래일 뒤 범위`);
      line.replaceChildren(Object.assign(document.createElement("span"), { className: "d", textContent: day }),
        Object.assign(document.createElement("span"), { className: "n", textContent: names.length ? names.join(", ") : "예측 마지막 날" }));
      line.classList.toggle("go", names.length > 0);
      prev.disabled = pick === 0;
      next.disabled = pick === events.length - 1;
    };
    const draw = () => {
      s.replaceChildren();
      const f = frame, pct = f.tree.pct, n = pct["50"].length - 1;
      events = f.tree.events.at(-1)?.[0] === n ? f.tree.events : [...f.tree.events, [n, [], f.days[n].slice(5).split("-").map(Number).join("/")]];
      pick ??= 0;
      const actual = f.day === date ? [] : f.tree.actual.slice(0, (f.days.indexOf(data.base_date) + 1) || undefined);
      // 선의 끝 종가 [거래일, 등락률]과 세션 값 [거래일, 등락률, 세션]이다. 끝 종가가 기준 가격 날짜가 아니면 둘 다 없다.
      const end = f.day === date ? [0, (hist[close] / f.base - 1) * 100]
        : actual.length && f.days[actual.length - 1] === data.base_date ? [actual.length - 1, actual.at(-1)] : null;
      // 세션 값은 리포트 날짜 판단의 기준 가격 날짜 다음 날짜 지점(`point`)에 놓는다. 그 지점은 프레임의 `days`에서 찾고, 프레임이 지점에 닿지 않으면 세션 값이 없다.
      const here = f.days.indexOf(point), shown = end && here > 0 ? nextOf(data) : null;
      const tail = shown ? [here, (shown[0] / f.base - 1) * 100, shown[2]] : null;
      const reach = Math.max(15, ...[pct["10"], pct["90"], actual].flat().map(Math.abs), ...[end, tail].filter(Boolean).map((v) => Math.abs(v[1])));
      const top = Math.ceil(reach / 5) * 5;
      // 날짜 지점의 가로 자리다. 분위수 선의 0번째 값은 1번째 값과 같은 날짜 지점(`days[1]`)에 놓으므로 분위수의 가로 자리(`Q`)는 0번째를 1번째에 둔다.
      const X = (d) => L + d / n * (R - L), Q = (d) => X(Math.max(1, d)), Y = (v) => B - (Math.max(-top, Math.min(top, v)) + top) / (2 * top) * (B - T);
      const band = (a, b, opacity) => shape("path", { d: `${path(pct[a].map((v, d) => [Q(d), Y(v)]))}L${pct[b].slice().reverse().map((v, d) => `${Q(n - d)} ${Y(v)}`).join("L")}Z`, fill: color, opacity });
      s.append(band("10", "90", .14));
      s.append(shape("line", { x1: L, x2: R, y1: Y(0), y2: Y(0), stroke: "rgba(122, 130, 140, .55)" }));
      // 이웃 번호와 16px보다 가까운 번호는 한 줄 위에 그린다.
      let before = -99, row = 0;
      const hits = [];
      events.forEach(([d], i) => {
        row = X(d) - before < 16 && row === 0 ? 1 : 0;
        before = X(d);
        const cy = T - 9 - row * 17;
        s.append(shape("line", { x1: X(d), x2: X(d), y1: cy, y2: B, "stroke-width": 1, "stroke-dasharray": "2 3", "data-ev": i }));
        s.append(shape("circle", { cx: X(d), cy, r: 7.5, "data-ev": i }));
        s.append(shape("text", { x: X(d), y: cy + 3.5, "font-size": 9.5, "font-weight": 600, "text-anchor": "middle", "pointer-events": "none", "data-ev": i }, i + 1));
        // 번호 원과 그 아래 세로선 양옆 7px까지를 누르면 그 일정을 고른다. 누르는 면은 범위 띠에 가리지 않게 맨 마지막에 붙인다.
        const touch = { fill: "transparent", style: "cursor:pointer" };
        [shape("circle", { cx: X(d), cy, r: 13, ...touch }), shape("rect", { x: X(d) - 7, y: cy, width: 14, height: B - cy, ...touch })].forEach((hit) => {
          hit.addEventListener("click", () => { pick = i; mark(); });
          hits.push(hit);
        });
      });
      s.append(shape("line", { x1: L, x2: R, y1: B, y2: B, stroke: DIMS }));
      f.tree.ticks.forEach(([t, day]) => s.append(shape("text", { x: X(t), y: B + 17, "font-size": 11, fill: DIMS, "text-anchor": t === 0 ? "start" : t === n ? "end" : "middle" }, day)));
      s.append(shape("path", { d: `${path(pct["25"].map((v, d) => [Q(d), Y(v)]))}L${pct["75"].slice().reverse().map((v, d) => `${Q(n - d)} ${Y(v)}`).join("L")}Z`, fill: color, opacity: .22 }));
      s.append(shape("path", { d: path(pct["50"].map((v, d) => [Q(d), Y(v)])), fill: "none", stroke: color, "stroke-width": 1.4, "stroke-linejoin": "round" }));
      if (actual.length) {
        const points = actual.map((v, d) => [X(d), Y(v)]), lineStyle = { fill: "none", "stroke-linejoin": "round", "stroke-linecap": "round" };
        s.append(shape("path", { d: path(points), ...lineStyle, stroke: "rgba(0, 0, 0, .6)", "stroke-width": 3.2 }));
        s.append(shape("path", { d: path(points), ...lineStyle, stroke: PRICE, "stroke-width": 1.6 }));
        if (!end) s.append(shape("circle", { cx: points.at(-1)[0], cy: points.at(-1)[1], r: 2.5, fill: PRICE }));
      }
      if (end) {
        const from = [X(end[0]), Y(end[1])], to = tail && [X(tail[0]), Y(tail[1])];
        if (to) s.append(shape("path", { d: path([from, to]), fill: "none", stroke: PRICE, "stroke-width": 1.6, "stroke-linecap": "round", "stroke-dasharray": "2 2" }));
        if (to) s.append(shape("circle", { cx: from[0], cy: from[1], r: 2.5, fill: PRICE }));
        nowMark(s, ...(to ?? from), tail?.[2] ?? "regular");
      }
      // 0% 글씨는 종가 선과 '현재' 표시가 시작하는 왼쪽 끝을 비우도록 그림 오른쪽 끝에 둔다.
      s.append(shape("text", { x: R, y: Y(0) - 4, "font-size": 11, fill: DIMS, "text-anchor": "end", "pointer-events": "none",
        stroke: "#171719", "stroke-width": 3, "stroke-linejoin": "round", "paint-order": "stroke" }, "0%"));
      scale = { X, Y, values: s.appendChild(shape("g", { "pointer-events": "none" })) };
      s.append(...hits);
      mark();
    };
    return {
      box: c.box,
      show(f) {
        if (frame?.day !== f.day) pick = null;
        frame = f;
        draw();
      },
    };
  })();

  // 권장 배율: 경로마다의 평균 배율 분포를 오늘 판단(판단 색)과 이슈가 없을 때의 기준(회색)으로 그리고, 평균 배율에 세로선을 긋는다.
  const chart = (() => {
    const c = card("지수 추종 = 1.0"), s = c.svg;
    const L = 4, R = W - 4, T = 22;
    return {
      box: c.box,
      show(f) {
        const den = f.chart, n = den.points, m = 1 + den.mean;
        c.head("", m.toFixed(3));
        const xs = Array.from({ length: n }, (_, i) => 1 + den.low + (den.high - den.low) * i / (n - 1));
        const X = (v) => L + (v - xs[0]) / (xs[n - 1] - xs[0]) * (R - L), peak = Math.max(...den.today, ...den.quiet);
        const Y = (v) => B - v / peak * (B - T);
        const area = (values) => `M${X(xs[0])} ${B}L${values.map((v, i) => `${X(xs[i])} ${Y(v)}`).join("L")}L${X(xs[n - 1])} ${B}Z`;
        s.replaceChildren();
        s.append(shape("path", { d: area(den.quiet), fill: "rgba(167, 171, 176, .14)" }));
        s.append(shape("path", { d: area(den.today), fill: color, opacity: .2 }));
        s.append(shape("line", { x1: X(1), x2: X(1), y1: T, y2: B, stroke: "#A7ABB0", "stroke-width": 1, "stroke-dasharray": "2 3" }));
        s.append(shape("line", { x1: X(m), x2: X(m), y1: T, y2: B, stroke: color, "stroke-width": 1.6 }));
        s.append(shape("line", { x1: L, x2: R, y1: B, y2: B, stroke: DIMS }));
        [[0.5, "E 큰 하락"], [0.75, "D 하락"], [1, "C 횡보"], [1.25, "B 상승"], [1.5, "A 큰 상승"]].forEach(([v, text]) => {
          s.append(shape("line", { x1: X(v), x2: X(v), y1: B, y2: B + 4, stroke: DIMS }));
          s.append(shape("text", { x: X(v), y: B + 17, "font-size": 11, fill: Math.abs(v - m) < 0.125 ? "#EAEAEA" : DIMS, "text-anchor": "middle" }, text));
        });
      },
    };
  })();

  const parts = [[price, "주가와 예측"], [tree, "일정"], [chart, "권장 배율"]];
  let frame = data;
  const show = (f) => { frame = f; parts.forEach(([part]) => part.show(f)); };
  show(data);
  // 머리 상자 시세는 위 줄에 기준 가격 날짜의 정규장 종가를, 아래 줄에 리포트 날짜 판단의 기준 가격 날짜 다음 날짜 지점의 값(`nextOf`)을 쓴다.
  // 그 값이 프리장 값이면 아래 줄에 프리마켓 가격과 정규장 종가 대비 등락률을, 애프터장 값(판단의 기준 가격이나 실시간 애프터장·선물 시간대 값)이면 애프터마켓 가격과 등락률을 쓴다.
  // 정규장 값이면 아래 줄을 두지 않고, 위 줄에 그 값과 앞 종가 대비 등락률을 쓴다. 위 줄 등락률은 반올림한 값으로 색을 정해 0.00%를 칠하지 않는다.
  // 지수의 1분 값(`index`)이 있으면 마지막 줄에 지수 값과 그 값을 받은 시각(`loaded`)을 서울 시각으로 쓴다.
  const rate = (ratio) => Math.round(ratio * 1e4) / 100;
  const day = rate(hist[close] / hist[close - 1] - 1);
  const clock = (text) => new Date(text).toLocaleTimeString("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false });
  const quote = () => {
    const next = upcoming();
    const line = (name, value) => `<small>${name} ${fmt(value)} ${signed(rate(value / hist[close] - 1), 2)}%</small>`;
    const open = next[2] === "regular", value = open ? next[0] : hist[close], move = open ? rate(next[0] / hist[close] - 1) : day;
    const tail = open ? "" : line(next[2] === "pre" ? "프리마켓" : "애프터마켓", next[0]);
    const idx = loaded && `<small class="loaded">지수 ${fmt(loaded.price)} · ${clock(loaded.loaded)} KST 로드</small>`;
    return `<span class="row"><span>${INDEX_NAME[key.split("-")[1]]}</span><b class="price ${tone(move)}">${fmt(value)}</b>`
      + `<b class="${tone(move)}">${signed(move, 2)}%</b>${tail}${idx || ""}</span>`;
  };
  // `live(all, index)`는 실시간 값 전체(`all`)에서 지수(`index`)의 지점별 값과 지수 1분 값을 받아, 값을 받은 시각이 바뀌었으면 고른 날짜로 카드를 다시 그린다.
  const SYMBOL = { nasdaq: "^NDX", biotech: "^NBI" };
  const live = (all, index) => {
    const next = all.points?.[index] ?? {}, tick = all.index?.[SYMBOL[index]] ?? null;
    const changed = JSON.stringify(next) !== JSON.stringify(found);
    loaded = tick;
    found = next;
    if (!changed) return;
    show(frame);
  };
  return { names: parts.map(([, name]) => name), slides: parts.map(([part]) => [part.box]), show, quote, live };
}
