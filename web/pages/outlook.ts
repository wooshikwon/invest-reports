// @ts-nocheck
import { toCalendar } from "./report";
import { gaugeCard, indexInk } from "../shared/card";
import { INDEX_NAME, INDEX_TITLE, ticker } from "../shared/chrome";
import { candled } from "../shared/data";
import { tone } from "../shared/format";
import { subscribe } from "../shared/live";
import { slider } from "../shared/motion";
import { rolled } from "../shared/roll";
import { key, report } from "../shared/route";
import { SESSION_NAME, afterEnd, closeAt, closedTag, sessionAt, sessionSeg, sessionTag, stale } from "../shared/session";
import { DIMS, PRICE, candleGroups, candleLate, candleOn, candleUnit, drawCandles, ease, extremeAt, kindButton, markDay, markText, nowMark, onTap, shape, zoomDrag } from "../shared/svg";
import { feelPress } from "../shared/telegram";
// 요약의 Outlook 그림 자리에 12M + Predictions(주가), Montecarlo(예측과 일정), Outlook(권장 배율) 순서로 넘기는 묶음을 둔다.
// Montecarlo 그림은 원래 이벤트 캘린더 절에 있으므로 그 자리에서는 뺀다. 12M + Predictions가 없는 리포트는 두 장을 넘긴다.
// 묶음 위에는 그림 이름 탭을 둔다. 탭을 누르면 그 그림으로 넘기고, 넘기면 보고 있는 그림의 탭을 밝힌다.
// 그림 카드 값(`given`, `build.py`가 쓴 `r/{키}/cards.json`. 그 파일이 없는 지난 리포트는 리포트 끝의 `#cards`)이 있는 리포트는 그림 대신 주가, 예측과 일정, 권장 배율 카드 세 장을 넘긴다.
export function figures(given = null, view = { aim: false, stage: () => ({ state: "done", text: "예측" }), watch() {} }) {
  const data = report.querySelector("#cards");
  data?.remove();
  const cards = given ?? (data && JSON.parse(data.textContent));
  if (cards) {
    const set = summaryCards(cards, view);
    ticker.innerHTML = set.quote();
    subscribe((found) => {
      set.live(found, key.split("-")[1]);
      ticker.innerHTML = set.quote();
    }, true);
    const bar = document.createElement("div");
    bar.className = "tabs";
    set.names.forEach((name, i) => {
      const button = Object.assign(document.createElement("button"), { textContent: name });
      button.addEventListener("click", () => box.go(i));
      bar.appendChild(button);
    });
    const change = (i) => [...bar.children].forEach((button, j) => button.classList.toggle("on", i === j));
    // 카드마다 한 장이고, 장의 높이는 보고 있는 장에 맞춘다. `slides`는 카드 이름마다의 장이라, 리포트 화면이 그 장의 카드 아래에 설명 절을 붙인다.
    const head = report.querySelector("h2"), box = slider(set.slides, head, { change, name: "cards", feel: true, fit: true, home: 0 });
    box.prepend(bar);
    const slides = Object.fromEntries(set.names.map((name, i) => [name, box.querySelector(".track").children[i]]));
    return { box, slides, label: () => set.label() };
  }
  const pick = (name) => [...report.querySelectorAll("img")].find((img) => img.getAttribute("src").includes(`/${name}-`));
  const chart = pick("chart"), tree = pick("tree"), predict = pick("predict");
  if (!chart || !tree) return;
  const shown = [[predict, "주가"], [tree, "예측과 일정"], [chart, "권장 배율"]].filter(([img]) => img);
  shown.forEach(([img]) => (img.closest("p") || img).remove());
  const bar = document.createElement("div");
  bar.className = "tabs";
  shown.forEach(([, name], i) => {
    const button = Object.assign(document.createElement("button"), { textContent: name });
    button.addEventListener("click", () => box.go(i));
    bar.appendChild(button);
  });
  const change = (i) => [...bar.children].forEach((button, j) => button.classList.toggle("on", i === j));
  const box = slider(shown.map(([img]) => [img]), report.querySelector("h2"), { change, feel: true, home: 0 });
  box.prepend(bar);
}

// 요약 절의 그림 카드 세 장(주가, 예측과 일정, 권장 배율)을 만든다. 카드 이름 탭에는 "주가", "예측과 일정", "권장 배율"로 쓴다. `data`는 `build.py` `summary_cards`의 값이다.
// 주가 카드의 종가 바탕(날짜·종가·지난 예측)은 늘 리포트 날짜의 값이고, 고른 날짜의 판단만 그 위에 바꿔 그린다.
export function summaryCards(data, view) {
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
  // 날짜 지점은 이 리포트 판단의 기준 가격 날짜 다음 거래일부터의 거래일(`days[1]`, `days[2]`, …)이다. 앱은 날짜를 세지 않고 리포트의 `days`와 실시간 값의 `point`로 지점을 찾는다.
  // `found`는 이 지수의 지점별 실시간 값(`live.ts`의 `points`)이다.
  let found = {};
  // 실시간 값의 사슬(`sessions`). 리포트 판단의 첫 날짜 지점부터 차례로 지점마다 앞 세션의 애프터장 값(`after`), 선물 시간대 값(`futures`), 프리장 값(`pre`), 정규장 값(`regular`)을 늦은 순으로 읽는다.
  // 지점의 값은 앞 세션 종가에 실시간 값의 비율을 곱한 값이다. 앞 세션 종가는 첫 지점이면 기준 가격 날짜 종가이고, 그 뒤 지점이면 앞 지점의 정규장 마감 값이다.
  // 그래서 지점 N 정규장이 끝난 뒤의 애프터장 값은 다음 지점의 `after`로 들어와 사슬을 잇는다. 정규장 값이 없는 지점에서 사슬이 끝난다.
  // 값마다 [값, 위 줄 글씨, 세션(`after`, `futures`, `pre`, `regular`), 체결 뉴욕 시각, 실시간 값, 지점 순번(기준 가격 날짜에서 센 거래일 수), 앞 세션 종가]이다.
  // `regulars`는 지점마다의 정규장 값이고, `latest`는 가장 늦은 값이며, 실시간 값이 없으면 판단의 기준 가격(기준 가격 날짜의 애프터장 마지막 값)이다.
  const sessions = () => {
    const regulars = [];
    let latest = null, prior = hist[close];
    for (let k = 1; k < data.days.length; k++) {
      const rec = found[data.days[k]];
      if (!rec) break;
      if (rec.after?.ratio != null) latest = [prior * rec.after.ratio, sessionAt("애프터마켓", rec.after.time), "after", rec.after.time, rec.after, k, prior];
      if (rec.futures?.ratio != null) latest = [prior * rec.futures.ratio, sessionAt("선물시장", rec.futures.time), "futures", rec.futures.time, rec.futures, k, prior];
      if (rec.pre?.ratio != null) latest = [prior * rec.pre.ratio, sessionAt("프리마켓", rec.pre.time), "pre", rec.pre.time, rec.pre, k, prior];
      if (rec.regular?.ratio == null) break;
      latest = [prior * rec.regular.ratio, sessionAt("정규장", rec.regular.time), "regular", rec.regular.time, rec.regular, k, prior];
      regulars.push(latest);
      prior = latest[0];
    }
    return { regulars, latest: latest ?? [data.base, sessionAt("애프터마켓", afterEnd(data.base_date)), "after", afterEnd(data.base_date), null, 1, hist[close]] };
  };

  // 주가 카드(`price`): 이름 줄 오른쪽에 예측 단추와 세션 단추를 둔다.
  // 그림 아래 −·+ 단추로 종가를 그릴 기간을 고른다. 기간은 3년, 2년, 1년, 6개월, 3개월 다섯 단계이고, +는 한 단계 짧게, −는 한 단계 길게 바꾼다.
  // 기간은 가로축 전체의 길이다. 단추 사이의 점 묶음은 누른 채 끌어 기간을 바로 고른다(`zoomDrag`).
  // 처음에는 가장 짧은 3개월을 그린다. 봉 비율(`r/candles.json`)이 있으면 그 줄 오른쪽 끝에 선·봉 단추(`kindButton`)를 두고,
  // 봉 그림이면 종가 선 대신 3년·2년은 월봉, 1년은 주봉, 6개월·3개월은 일봉을 그린다.
  // 종가는 기준 가격 날짜까지 그리고, 실시간 값의 사슬(`sessions`)을 지점 순번의 거래일 자리에 잇는다. 선 그림이면 정규장 값은 앞 점에서 실선으로 잇고,
  // 그 뒤의 프리장·애프터장·선물 시간대 값은 앞 점을 찍고 점선으로 잇는다. 봉 그림이면 정규장 값은 앞 세션 종가 대비 비율로 받은 시가·고가·저가·종가(`ohlc`)의 등락 색 잠정 봉으로,
  // 그 뒤의 값은 흐린 회색 잠정 봉으로 덧붙인다(`candleLate`).
  // 세션 단추는 가장 늦은 값이 정규장 값이면 정규장 단추 하나이고, 프리장·애프터장 값이면 정규장 단추와 그 세션 단추 한 쌍이다.
  // 정규장 단추를 고르면 사슬의 정규장 값까지만 그리고 '현재' 표시를 마지막 정규장 값(없으면 기준 가격 날짜 종가)에 찍는다. 세션 단추를 고르면 가장 늦은 값까지 그려 거기에 찍는다.
  // 가장 늦은 리포트는 가장 늦은 값을, 지난 리포트는 정규장을 고른 채로 연다. 머리 글씨의 위 줄에는 '현재' 표시 값의 세션과 시각을, 가운데 줄에는 그 값과 앞 세션 종가 대비 등락률을 적고,
  // 정규장 값은 등락률 색(`tone`)으로, 프리장·애프터장 값은 회색으로 쓴다.
  // 그림을 누르면 누른 자리의 거래일로 '현재' 표시를 옮기고 머리 글씨를 그날 정규장 종가와 전날 대비 등락률로 바꾼다(`picked`). 기준 가격 날짜 종가나 그 뒤 실시간 값 자리를 누르면
  // 처음 상태로 돌아온다. 세션 단추나 예측 단추를 누르거나 고른 거래일이 기간 밖으로 나가도 처음 상태로 돌아온다.
  // 예측 단추(`aim`)를 켜면 판단의 예측과 지난 리포트의 예측을 그리고, '현재' 표시를 가장 늦은 값에 찍으며 세션 단추를 모두 끈다. 처음에는 리포트 화면이 건넨 상태(`view.aim`)로 연다.
  // 켠 카드는 위 줄에 "25거래일 뒤 예측 중앙값"을, 가운데 줄에 그 값을 지수색 그라데이션으로 쓰고 지수색 점 뒤에 기준 가격 대비 등락률을 적는다.
  // 켠 카드에서 지난 거래일을 누르면 그날 종가를 기준 가격으로 내린 판단(`r/rewind-{지수}/cards.json`의 프레임)의 예측 범위와 50% 선을 오늘 판단의 예측 대신 그리고,
  // '현재' 표시를 그날 종가에 찍으며, 머리 글씨를 그 판단의 25거래일 뒤 예측 중앙값과 그날 기준 가격 대비 등락률로 바꾼다. 그날 판단이 없는 거래일은 눌러도 바뀌지 않는다.
  // 기준 가격 날짜 종가나 그 뒤 자리를 누르면 오늘 판단의 예측으로 돌아온다.
  // 끈 카드의 가로축은 사슬의 마지막 거래일 자리(없으면 기준 가격 날짜 다음 거래일)에서 끝나고, 켠 카드의 가로축은 기준 가격 날짜 뒤 25거래일에서 끝난다. 그림 왼쪽 끝도 같은 거래일 수만큼 옮겨 기간을 지킨다.
  // 단추를 누르면 기간을 바꿀 때와 같은 곡선으로 가로축과 세로 범위를 옮기면서 예측을 서서히 나타내거나 지운다.
  // 판단의 예측은 기준 가격 점에서 출발하는 25~75% 범위와 50% 선이다. 기준 가격 점은 기준 가격 날짜 다음 거래일 자리에 찍고,
  // 25거래일 뒤 값은 그 거래일 자리에 찍으며, 그 사이 날은 두 자리 사이에 고르게 놓는다.
  // 기준 가격 점과 25거래일 뒤 50% 값의 점은 지수색으로 찍고, 기준 가격 점은 종가와 잇지 않는다. 지난 리포트의 예측은 회색 점선과 면으로 그린다.
  // 판단에 예측이 없으면 지난 리포트의 예측만 그리고, 머리 글씨에는 '현재' 표시의 값을 끈 카드와 같은 모양으로 적는다.
  const price = (() => {
    const c = card(""), s = c.svg, clipId = "price-clip", title = c.title;
    c.box.querySelector(".val b").className = "";
    // `track`은 그림에 잇는 사슬의 값들이고, `picked`는 그림을 눌러 고른 자리(종가 거래일 번호 `i`, 켠 카드면 그날 판단 `f`)다.
    let late = false, chosen = false, track = [], picked = null, aim = false, want = !!view.aim, first = true;
    const toggle = Object.assign(document.createElement("button"), { type: "button", className: "aim", innerHTML: "<span>예측</span>" });
    title.append(toggle);
    // 단추 글자와 단계 상태(`pre`·`running`)는 `view.stage()`가 준 값을 그대로 그린다. 단계는 눌러서 예측을 켜는 동작에 영향을 주지 않는다.
    const label = () => {
      const now = view.stage?.() ?? { state: "done", text: "예측" };
      const span = toggle.firstChild;
      if (span.textContent !== now.text) span.textContent = now.text;
      toggle.classList.toggle("pre", now.state === "pre");
      toggle.classList.toggle("running", now.state === "running");
    };
    label();
    toggle.setAttribute("aria-pressed", "false");
    const seg = sessionSeg((on) => { late = on; chosen = true; picked = null; show(frame); });
    // `ahead`는 예측 단추를 켠 정도(끄면 0, 켜면 1)이고, 단추를 누르는 동안 그 사이 값을 받는다. `reach`는 사슬의 마지막 지점 순번(없으면 1)이다.
    // 가로축 오른쪽 끝(`xmax`)은 끄면 마지막 종가 뒤 `reach` 거래일, 켜면 마지막 종가 뒤 25거래일이다.
    // 기간(`DAYS`)마다 그림 왼쪽 끝(`start`)은 가로축 마지막 거래일(`xmax - 1`)에서 그 거래일 수만큼 앞이다.
    const L = 4, R = W - 4, T = 22, DAYS = [756, 504, 252, 126, 63], most = DAYS.length - 1;
    let ahead = 0, seen = 0, reach = 1, head = () => {};
    const xmax = (r) => last + Math.max(reach, 1 + 24 * r), start = (k, r) => Math.max(0, xmax(r) - 1 - DAYS[k]);
    let span = most, frame = null, raf = 0, ratios = null;
    const zoom = c.foot.appendChild(Object.assign(document.createElement("div"), { className: "zoom" }));
    zoom.innerHTML = `<button type="button" aria-label="기간 늘리기">−</button><span class="steps">${"<i></i>".repeat(DAYS.length)}</span><button type="button" aria-label="기간 줄이기">+</button>`;
    const [wider, narrower] = zoom.querySelectorAll("button");
    const level = () => {
      wider.disabled = span === 0;
      narrower.disabled = span >= most;
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
    // 사슬 값의 잠정 봉 값. 정규장 값은 앞 세션 종가 대비 비율로 받은 시가·고가·저가·종가(`ohlc`)로 등락 색 봉을 그리고, 애프터장·프리장 값은 회색 봉을 그린다.
    const liveBar = (entry) => {
      const o = entry[2] === "regular" ? entry[4]?.ohlc : null, base = entry[6];
      return o ? { open: base * o.open, high: base * o.high, low: base * o.low, close: base * o.close, gray: false } : { close: entry[0], gray: entry[2] !== "regular" };
    };
    const past = (data.past ?? []).map(([x, lo, mid, hi]) => ({ x, lo, mid, hi }));
    const at = (f) => dates.indexOf(f.base_date);
    // 지난 판단을 기준 가격 날짜마다 둔다. 이 리포트 날짜보다 늦은 판단과 이 리포트 판단은 넣지 않는다. `active()`는 그리는 판단(고른 지난 판단이나 이 리포트 판단)이다.
    const judged = {}, active = () => picked?.f ?? frame;
    fetch(`r/rewind-${key.split("-")[1]}/cards.json`, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null)).then((found) => {
      found?.frames.forEach((g) => { if (g.predict && g.day <= data.day && g.base_date !== data.base_date) judged[g.base_date] = g; });
    }).catch(() => {});
    // 기간마다 세로 범위: 보이는 종가(봉 그림이면 보이는 봉의 고가와 저가)·사슬 값을 담고, 예측을 켰으면(`r`가 0보다 크면) 예측 면과 지난 예측도 담는다.
    // 사슬 값과 예측 범위까지 담은 가장 낮은 값 아래에는 최저 글씨가 들어갈 20px을 비운다.
    const range = (x0, r) => {
      const shown = candle() ? candleGroups(dates, hist, ratios, candleUnit(DAYS[span]), last).filter((group) => group[1] >= x0).flatMap((group) => [group[3], group[4]]) : hist.slice(x0, last + 1);
      const band = (r > 0 && active().predict) || { q25: [], q75: [] }, before = r > 0 ? past : [], more = track.flatMap((entry) => [entry[0], liveBar(entry).high, liveBar(entry).low].filter((v) => v != null));
      let lo = Math.min(...shown, ...band.q25, ...before.map((q) => q.lo), ...more);
      const hi = Math.max(...shown, ...band.q75, ...before.map((q) => q.hi), ...more);
      const low = Math.min(...shown, ...more, ...band.q25);
      lo = Math.min(lo, low - (hi - low) * 20 / (B - T - 20));
      return [lo, hi];
    };
    // `x0`는 그림 왼쪽 끝의 거래일 번호이고, `r`는 예측을 그리는 정도다. 기간을 옮기거나 예측 단추를 누르는 동안에는 소수 값을 받아 그 사이를 이어 그리고,
    // 예측의 선과 면, 점은 `r`만큼 흐리게 그린다.
    const draw = (x0, lo, hi, marks, r) => {
      s.replaceChildren();
      const f = active(), fx = at(f), p = r > 0 ? f.predict : null, end = xmax(r);
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
      // 최고·최저 글씨는 기간이 정해진 뒤에만 그린다. 최고·최저는 기간 안 종가와 사슬의 정규장 값에서 고르므로,
      // 지금 정규장 값이 기간의 최고나 최저면 그 점에 붙는다. 봉 그림이면 점 없이 정규장 잠정 봉까지 포함한 가장 높은 고가와 가장 낮은 저가를 봉 위아래에 적는다.
      // 최고·최저 값 뒤 괄호에는 현재가(사슬의 마지막 값, 없으면 기준 가격 날짜 종가)의 그 값 대비 등락률과 그 값이 나온 거래일(`markDay`)을 적는다.
      // 현재가가 그 값이면 괄호에 거래일만 적는다. 거래일은 종가면 그 날짜, 사슬의 정규장 값이면 그 날짜 지점이고, 봉 그림이면 그 봉 안에서 고가나 저가가 나온 날이다.
      // 글씨 상자는 가운데를 그 점에 맞추되 그림 안에 들게 옮긴다(`markText`). 세로로는 최저 글씨를 그 점과 사슬 값(봉 그림이면 잠정 봉의 저가) 가운데
      // 가장 낮은 자리에서 6px(봉이면 4px) 아래에, 최고 글씨를 가장 높은 자리에서 같은 거리 위에 두어 선과 봉, '현재' 표시에 겹치지 않게 한다.
      const extremes = () => {
        const group = s.appendChild(shape("g", { class: "marks" })), now = track.at(-1)?.[0] ?? hist[last];
        const ys = track.flatMap((entry) => [entry[0], ...(groups ? [liveBar(entry).high, liveBar(entry).low] : [])]).filter((v) => v != null).map(Y);
        // 글씨가 예측 범위의 가로 자리 근처(양옆 60px)에 놓이면 범위의 위 끝 위나 아래 끝 아래로 옮겨 범위와 겹치지 않게 한다.
        const fan = p && { from: xs[0] - 60, to: xs.at(-1) + 60, top: Math.min(...p.q75.map(Y)), bottom: Math.max(...p.q25.map(Y)) };
        const floor = Math.max(...ys), ceiling = Math.min(...ys), near = (x) => fan && x > fan.from && x < fan.to;
        const write = (x, y, up, gap, v, day) =>
          markText(group, x, up ? Math.min(y, ceiling, near(x) ? fan.top : y) : Math.max(y, floor, near(x) ? fan.bottom : y), up, gap,
            `${fmt(v)} (${now === v ? "" : `${signed((now / v - 1) * 100)}%, `}${markDay(day)})`, L, R);
        // 봉 `[a, b]`의 고가(`up`)나 저가 `v`가 나온 날. 종가 안의 날을 먼저 고르고, 덧붙인 잠정 봉에서 사슬의 정규장 값이 그보다 높거나 낮으면 그 날짜 지점이다.
        const dayOf = ([a, b], v, up) => {
          const i = a <= last ? extremeAt(hist, ratios, a, Math.min(b, last), up) : -1, own = i < 0 ? null : hist[i] * (ratios[i] || [1, 1, 1])[up ? 1 : 2];
          const live = track.filter((entry) => entry[2] === "regular" && last + entry[5] >= a && last + entry[5] <= b)
            .find((entry) => (up ? liveBar(entry).high : liveBar(entry).low) === v);
          return live && (own == null || (up ? v > own : v < own)) ? data.days[live[5]] : dates[Math.max(i, 0)];
        };
        if (groups) {
          const bars = drawn.filter((bar) => !bar[7]), high = bars.reduce((a, b) => (b[3] > a[3] ? b : a)), low = bars.reduce((a, b) => (b[4] < a[4] ? b : a));
          [[high, high[3], true], [low, low[4], false]].forEach(([bar, v, up]) => write(X((bar[0] + bar[1]) / 2), Y(v), up, 4, v, dayOf(bar, v, up)));
          return;
        }
        const shown = [...hist.slice(i0, last + 1).map((v, k) => [i0 + k, v]), ...track.filter((entry) => entry[2] === "regular").map((entry) => [last + entry[5], entry[0]])];
        const high = shown.reduce((a, b) => (b[1] > a[1] ? b : a)), low = shown.reduce((a, b) => (b[1] < a[1] ? b : a));
        [[high, true], [low, false]].forEach(([[i, v], up]) => {
          group.append(shape("circle", { cx: X(i), cy: Y(v), r: 2.5, fill: PRICE }));
          write(X(i), Y(v), up, 6, v, i <= last ? dates[i] : data.days[i - last]);
        });
      };
      const step = (R - L) / (end - x0);
      // 예측의 0번째와 1번째 값은 기준 가격 날짜 다음 날짜 지점에 함께 놓고, t번째 값은 t번째 날짜 지점에 놓는다.
      const xs = p && p.q50.map((_, k) => X(fx + Math.max(1, k)));
      if (p) g.append(shape("path", { d: `${path(xs.map((x, k) => [x, Y(p.q25[k])]))}L${xs.slice().reverse().map((x, k) => `${x} ${Y(p.q75[xs.length - 1 - k])}`).join("L")}Z`, fill: color, opacity: .22 * r }));
      // 봉 그림이면 리포트 날짜에 고른 정규장 다음 세션 값만 잠정 봉으로 덧붙인다. `center(i)`는 거래일 `i`가 든 봉의 가운데 x이고,
      // `mark(i, y)`는 '현재' 표시의 높이로, 선 그림이면 값의 높이 `y`, 봉 그림이면 그 봉의 고가 5px 위다.
      const drawn = groups && track.reduce((out, entry) => candleLate(out, dates, unit, liveBar(entry), data.days[entry[5]]), groups);
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
      const close = [center(last), Y(hist[last])];
      const now = s.insertBefore(shape("g"), ends);
      // 선 그림이면 사슬 값을 지점 순번의 거래일 자리에 잇는다. 정규장 값은 앞 점에서 실선으로, 그 뒤의 프리장·애프터장·선물 시간대 값은 앞 점을 찍고 점선으로 잇는다.
      let tip = close;
      track.forEach((entry) => {
        const to = [center(last + entry[5]), Y(entry[0])];
        if (drawn) return (tip = to);
        if (entry[2] === "regular") g.append(shape("path", { d: path([tip, to]), ...stroke }));
        else {
          g.append(shape("path", { d: path([tip, to]), ...stroke, "stroke-dasharray": "2 2" }));
          now.append(shape("circle", { cx: tip[0], cy: tip[1], r: 2.5, fill: PRICE }));
        }
        tip = to;
      });
      // '현재' 표시는 고른 자리에, 고르지 않았으면 사슬의 마지막 값(없으면 기준 가격 날짜 종가)에 찍는다. 봉 그림이면 그 거래일이 든 봉의 고가 위에 찍는다.
      if (picked) { if (picked.i >= i0) nowMark(now, center(picked.i), mark(picked.i, Y(hist[picked.i])), "regular"); }
      else nowMark(now, tip[0], mark(last + (track.at(-1)?.[5] ?? 0), tip[1]), track.at(-1)?.[2] ?? "regular");
      // 그림을 누르면 누른 자리의 거래일을 고른다. 켠 카드는 그날 판단이 있는 거래일만 고르고, 기준 가격 날짜 종가나 그 뒤 자리는 처음 상태로 돌린다.
      onTap(s, (x) => {
        const i = Math.round(x0 + (x - L) / (R - L) * (end - x0));
        const day = i < last ? Math.max(i0, i) : null;
        if (aim && day != null && !judged[dates[day]]) return;
        feelPress();
        picked = day == null ? null : aim ? { i: day, f: judged[dates[day]] } : { i: day };
        head();
        tween(span, span, 1);
      });
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
      span = Math.max(0, Math.min(most, span + by));
      if (span === from) return;
      level();
      if (picked?.i != null && picked.i < start(span, ahead)) { picked = null; head(); }
      animate(from, seen);
    };
    wider.addEventListener("click", () => move(-1));
    narrower.addEventListener("click", () => move(1));
    zoomDrag(zoom.querySelector(".steps"), () => span, (i) => move(i - span));
    // 예측 단추를 누른 상태(`want`)는 카드를 넘겨도 그대로 둔다. `aim`은 그린 상태다.
    // 켠 상태가 바뀔 때마다 `view.watch`로 알린다. 리포트 화면은 그 상태를 기기에 남긴다.
    const sync = () => {
      aim = want;
      ahead = aim ? 1 : 0;
      if (first) { first = false; seen = ahead; }
      toggle.classList.toggle("on", aim);
      toggle.setAttribute("aria-pressed", aim);
      view.watch(aim);
    };
    toggle.addEventListener("click", () => {
      feelPress();
      want = !want;
      picked = null;
      sync();
      const from = span;
      settle();
      animate(from, seen);
    });
    // 그림에 잇는 사슬 값과 세션 단추, 머리 글씨를 정한다. 예측을 켠 카드는 가장 늦은 값까지 잇고 세션 단추를 모두 끈다.
    // 예측을 끈 카드는 가장 늦은 리포트면 가장 늦은 값을, 지난 리포트면 정규장을 고르고, 사용자가 누른 단추가 있으면 그 세션을 쓴다. 가장 늦은 값이 정규장 값이면 늘 그 값을 고른다.
    const settle = () => {
      const f = frame, { regulars, latest } = sessions(), regular = latest[2] === "regular";
      if (!aim && (!chosen || regular)) late = regular || !document.documentElement.classList.contains("past");
      track = aim || late ? (regular ? regulars : [...regulars, latest]) : regulars;
      reach = Math.max(1, ...track.map((entry) => entry[5]));
      seg.rename(latest[2]);
      seg.mark(aim ? null : late);
      [...seg.box.children].forEach((button) => (button.disabled = aim));
      title.append(seg.box);
      head = () => {
        const g = aim ? active() : null, p = g?.predict, tip = track.at(-1), rate = (a, b) => Math.round((a / b - 1) * 1e4) / 100;
        const ink = !!p && (!picked || !!picked.f), value = p?.q50.at(-1);
        c.box.classList.toggle("ext", !p && !picked && !!tip && tip[2] !== "regular");
        c.box.classList.toggle("ink", ink);
        c.box.querySelector(".val b").className = ink ? "ink" : "";
        if (ink) {
          c.box.querySelector(".state").className = "state";
          return c.head(`${signed((value / g.base - 1) * 100)}%`, fmt(value), picked ? `${+g.day.slice(5, 7)}/${+g.day.slice(8, 10)} 판단 · 25거래일 뒤 예측 중앙값` : "25거래일 뒤 예측 중앙값");
        }
        const i = picked?.i ?? last;
        if (picked || !tip) {
          const move = i > 0 ? rate(hist[i], hist[i - 1]) : 0;
          c.box.querySelector(".state").className = `state ${tone(move)}`;
          return c.head(`${signed(move, 2)}%`, fmt(hist[i]), sessionTag("regular", sessionAt("정규장", closeAt(dates[i]))));
        }
        // 휴장 판정은 지금 보이는 값이 사슬의 가장 늦은 값일 때만 한다. 정규장 단추로 고른 지난 정규장 값은 그 시각 그대로 쓴다.
        const move = rate(tip[0], tip[6]), { latest } = sessions(), front = tip[2] === latest[2] && tip[3] === latest[3];
        c.box.querySelector(".state").className = `state ${tip[2] === "regular" ? tone(move) : ""}`;
        c.head(`${signed(move, 2)}%`, fmt(tip[0]), front && stale(tip[3], tip[2]) ? closedTag() : sessionTag(tip[2], tip[1]));
      };
      head();
    };
    // 실시간 값이 바뀌면 같은 카드를 다시 그린다. 가로축 끝이 바뀌었거나 예측을 켜고 끈 상태가 바뀌었으면 − 단추처럼 그림을 이어 옮긴다.
    const show = (f) => {
      frame = f;
      sync();
      const from = span, was = reach;
      settle();
      if (reach !== was || ahead !== seen) animate(from, seen);
      else if (!raf) tween(span, span, 1);
    };
    return { box: c.box, show, label };
  })();

  // 예측과 일정: 등락률 분위수의 10~90% 옅은 면과 25~75% 면, 50% 실선을 주가 카드의 예측과 같은 지수색으로 그린다. 위쪽 번호는 이슈 일정이 있는 날이고,
  // 마지막 거래일에는 일정이 없어도 번호를 달고, 처음에는 첫 번호를 고른다. 번호를 누르면 위 값을 그날의 25~75% 등락률로 바꾸고,
  // 그 오른쪽에 그날의 10~90% 등락률을 작은 회색 글씨로 적으며, 세로선이 50% 선과 만나는 곳에 그날의 예측 중앙값을 지수색으로 적는다. 0% 가로선에는 글씨를 달지 않는다. 그림 아래 줄 가운데에는 고른 일정의 날짜와 이름을 적고, 이름이 줄을 넘으면 말줄임표로 줄인다.
  // 그 줄 양옆의 꺽쇠를 누르면 앞뒤 일정을 고르고, 일정 이름을 누르면 같은 페이지 아래의 이벤트 캘린더에서 같은 거래일을 연다(`toCalendar`).
  // 그림의 왼쪽 끝은 판단의 첫 날짜 지점(`days[1]`)이고, 등락률은 판단의 기준 가격 대비 값이다.
  // 기준 가격 날짜 종가에서 실시간 값의 사슬(`sessions`)을 지점 순번의 거래일 자리에 주가 카드처럼 잇는다. 정규장 값은 실선으로, 그 뒤의 프리장·애프터장·선물 시간대 값은
  // 앞 점을 찍고 점선으로 잇고, 사슬의 마지막 값(없으면 기준 가격 날짜 종가)에 '현재' 표시를 찍는다. 1분 값이 바뀌면 다시 그린다. 세션 단추는 두지 않는다.
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
      // 고른 세로선이 50% 선과 만나는 곳에 점을 찍고 그날의 예측 중앙값을 지수색 글씨로 적는다. 세로선이 그림 왼쪽 반에 있으면 글씨를 오른쪽에, 오른쪽 반에 있으면 왼쪽에 둔다.
      const right = X(d) < (L + R) / 2, mid = pct["50"][d];
      values.replaceChildren(shape("circle", { cx: X(d), cy: Y(mid), r: 2.5, fill: color, stroke: "#171719", "stroke-width": 1 }),
        shape("text", { x: X(d) + (right ? 6 : -6), y: Y(mid) - 6, "font-size": 11, "font-weight": 700, fill: color, "text-anchor": right ? "start" : "end",
          stroke: "#171719", "stroke-width": 3, "stroke-linejoin": "round", "paint-order": "stroke" }, `${signed(mid)}%`));
      const wide = Object.assign(document.createElement("span"), { className: "wide", textContent: `${signed(pct["10"][d])}~${signed(pct["90"][d])}%` });
      c.head("", [...percent(pct["25"][d]), Object.assign(document.createElement("span"), { className: "sep", textContent: "~" }), ...percent(pct["75"][d]), wide],
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
      // 선의 시작인 기준 가격 날짜 종가 [거래일, 등락률]과 사슬 값 [거래일, 등락률, 세션]이다.
      const { regulars, latest } = sessions(), track = latest[2] === "regular" ? regulars : [...regulars, latest];
      const end = [0, (hist[close] / f.base - 1) * 100], tips = track.map((entry) => [entry[5], (entry[0] / f.base - 1) * 100, entry[2]]);
      const reach = Math.max(15, ...[pct["10"], pct["90"]].flat().map(Math.abs), ...[end, ...tips].map((v) => Math.abs(v[1])));
      const top = Math.ceil(reach / 5) * 5;
      // 거래일의 가로 자리다. 날짜 지점(1번째 거래일)을 왼쪽 끝에 두고, 기준 가격 날짜(0번째)도 왼쪽 끝에 둔다.
      const X = (d) => L + Math.max(0, d - 1) / (n - 1) * (R - L), Y = (v) => B - (Math.max(-top, Math.min(top, v)) + top) / (2 * top) * (B - T);
      const band = (a, b, opacity) => shape("path", { d: `${path(pct[a].map((v, d) => [X(d), Y(v)]))}L${pct[b].slice().reverse().map((v, d) => `${X(n - d)} ${Y(v)}`).join("L")}Z`, fill: color, opacity });
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
      s.append(shape("path", { d: `${path(pct["25"].map((v, d) => [X(d), Y(v)]))}L${pct["75"].slice().reverse().map((v, d) => `${X(n - d)} ${Y(v)}`).join("L")}Z`, fill: color, opacity: .22 }));
      s.append(shape("path", { d: path(pct["50"].map((v, d) => [X(d), Y(v)])), fill: "none", stroke: color, "stroke-width": 1.4, "stroke-linejoin": "round" }));
      let from = [X(end[0]), Y(end[1])];
      tips.forEach(([d, v, kind]) => {
        const to = [X(d), Y(v)];
        if (kind === "regular") s.append(shape("path", { d: path([from, to]), fill: "none", stroke: PRICE, "stroke-width": 1.6, "stroke-linecap": "round" }));
        else {
          s.append(shape("path", { d: path([from, to]), fill: "none", stroke: PRICE, "stroke-width": 1.6, "stroke-linecap": "round", "stroke-dasharray": "2 2" }));
          s.append(shape("circle", { cx: from[0], cy: from[1], r: 2.5, fill: PRICE }));
        }
        from = to;
      });
      nowMark(s, ...from, tips.at(-1)?.[2] ?? "regular");
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

  const parts = [[price, "주가"], [tree, "예측과 일정"], [chart, "권장 배율"]];
  const show = () => parts.forEach(([part]) => part.show(data));
  show();
  // 머리 상자가 화면 위에 붙으면 보이는 시세는 "나스닥 선물시장 $25,518 +1.95%"처럼 지수 이름, 사슬의 가장 늦은 값의 세션 이름, 그 값, 등락률을 한 줄에 쓴다.
  // 등락률은 정규장 값이면 앞 세션 종가 대비이고, 애프터장·선물 시간대·프리장 값(판단의 기준 가격 포함)이면 마지막 정규장 값(없으면 기준 가격 날짜의 정규장 종가) 대비다.
  // 주가 카드처럼 정규장 값이면 값을 흰색으로, 등락률을 반올림한 등락률로 오름 빨강·내림 파랑으로 칠해 0.00%를 칠하지 않고, 정규장이 아닌 세션 값이면 값과 등락률을 회색으로 쓴다.
  const rate = (ratio) => Math.round(ratio * 1e4) / 100;
  const quote = () => {
    const { regulars, latest } = sessions(), reg = regulars.at(-1), kind = latest[2];
    const move = rate(latest[0] / (kind === "regular" ? latest[6] : reg ? reg[0] : hist[close]) - 1);
    return `<span class="name">${INDEX_NAME[key.split("-")[1]]}</span><span class="kind">${stale(latest[3], kind) ? "휴장" : SESSION_NAME[kind]}</span>`
      + `<b${kind === "regular" ? "" : ' class="late"'}>${fmt(latest[0])}</b><b class="rate ${kind === "regular" ? tone(move) : "late"}">${signed(move, 2)}%</b>`;
  };
  // `live(all, index)`는 실시간 값 전체(`all`)에서 지수(`index`)의 지점별 값을 받아, 값이 바뀌었으면 카드를 다시 그리고 바뀐 큰 글씨 숫자를 굴린다.
  // 화면을 연 뒤 처음 받은 실시간 값은 리포트 값으로 먼저 그린 카드를 받은 값으로 바로 바꾸고, 그 뒤 값이 바뀐 회차만 굴린다.
  // 값이 그대로인 회차에도 휴장이면(`stale`) 기준 시각의 지금 시각을 바꾸려고 카드를 다시 그린다.
  let primed = false;
  const live = (all, index) => {
    const next = all.points?.[index] ?? {}, first = !primed;
    const changed = JSON.stringify(next) !== JSON.stringify(found);
    found = next;
    primed = true;
    if (!changed) {
      const { latest } = sessions();
      if (stale(latest[3], latest[2])) show();
      return;
    }
    if (first) show();
    else rolled(show);
  };
  return { names: parts.map(([, name]) => name), slides: parts.map(([part]) => [part.box]), quote, live, label: () => price.label?.() };
}
