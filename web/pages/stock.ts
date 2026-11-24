// @ts-nocheck
import { headlines } from "./news";
import { backward } from "../shared/back";
import { INDEX_NAME } from "../shared/chrome";
import { marketed } from "../shared/data";
import { price, signed, tone } from "../shared/format";
import { GAUGES, dailyTaps, gauge } from "../shared/gauge";
import { question } from "../shared/help";
import { chain, subscribe } from "../shared/live";
import { slider } from "../shared/motion";
import { query, report } from "../shared/route";
import { SESSION_NAME, afterEnd, closeAt, closedText, sessionAt, sessionSeg, stale } from "../shared/session";
import { DIMS, candleOn, candleUnit, dailyBounds, ease, kindButton, nearest, onTap, zoomDrag } from "../shared/svg";
import { feelPress } from "../shared/telegram";
import { gallery, viewer } from "../shared/viewer";
// 종목 상세(`stock`)를 이슈 화면과 같은 틀에 그린다. `data`는 `build.py` `stock_pages`가 적는 `r/stocks/{티커}.json`이다.
// 대표 이미지(`images`)가 있으면 절 제목 위에 이슈 그림과 같은 모양으로 싣고, 두 장 이상이면 넘기기 묶음에 담는다.
// 절 제목은 "나스닥 시총 3위"처럼 지도 지수의 이름과 그 지수 안 시가총액 순위다. 위쪽 한 줄 띠와 창 제목에는 종목 이름을 쓴다.
// 첫 상자에는 주가 카드와 기업 설명을 둔다. 주가 카드는 이름 자리에 종목 이름과 티커를 쓰고, 마지막 종가와 앞 세션 종가 대비 등락률을 쓰며,
// 그림 아래 −·+ 단추로 1년, 6개월, 3개월 가운데 기간을 골라 일별 종가 선을 다시 그린다. 종가가 기간보다 짧으면 있는 종가를 모두 그리고, 같은 그림이 되는 기간은 하나만 둔다.
// 단추 사이의 점 묶음은 누른 채 끌어 기간을 바로 고른다(`zoomDrag`). 봉 비율(`candles`)이 있으면 그 줄 오른쪽 끝에 선·봉 단추(`kindButton`)를 두고, 봉 그림이면 종가 선 대신 1년은 주봉, 6개월·3개월은 일봉을 그린다.
// 처음에는 가장 짧은 기간을 그린다.
// 그림을 누르면 누른 자리에서 가장 가까운 종가 점(그림에 보이는 범위 안)으로 '현재' 표시를 옮겨 찍으며,
// 위 줄에 그 종가 날짜를, 가운데 줄에 그 종가와 앞 종가 대비 등락률을 쓴다. + 단추로는 그 종가가 빠지는 기간까지 줄이지 않는다.
// 지난 날짜에는 세션 단추를 두지 않고, 마지막 종가 점이나 그 뒤 세션 값 자리를 누르면 처음과 같은 세션의 마지막 종가로 돌아간다.
// 카드 맨 위 줄에는 기준일 글씨를 쓰고, 그 아래 이름 줄에 종목 이름과 티커를 쓴다.
// 마지막 종가 뒤의 값은 지수 화면과 같은 날짜 지점의 실시간 사슬(`live.ts` `chain`)에서 고른다. 사슬은 날짜 지점마다 앞 세션의 애프터마켓, 주간거래, 프리마켓, 정규장 값을
// 차례로 읽고, 정규장 값이 있으면 그 값이 마지막 정규장이 된다. 정규장이 끝난 날의 값 뒤에 다음 세션 값이 오면 그날 종가를 종가 목록에 붙여 카드를 다시 그리고 그 뒤 값을 잇는다.
// 정규장 다음 값이 있으면 이름 줄 오른쪽에 정규장 단추와 그 값의 세션(애프터마켓·주간거래·프리마켓) 단추를 둔다. 실시간 값이 없으면 `r/market.json` 지도 값의 애프터장 체결가를 쓴다.
// 정규장 다음 단추를 고르면 값과 등락률을 그 체결가와 마지막 종가 대비 등락률로 바꿔 회색으로 쓰고, 그림에 그 체결가를 점선으로 잇는다.
// 처음 고르는 세션은 주소의 `session`이고, 주소에 없으면 가장 늦은 세션이다.
// 사슬의 가장 늦은 값이 아직 끝나지 않은 정규장 값이면 단추를 정규장 단추 하나로 줄이고, 그 체결가와 등락률을 등락률 색으로 쓰며 그림에 점선으로 잇는다.
// 첫 상자 아래에는 주요 뉴스 절을 두고 그 종목을 단 종목 뉴스 기사의 제목을 쓴다(`pages/news.ts` `headlines`).
// 공시 상세 절은 주요 뉴스 절 아래에 두고, 탭 띠와 넘기기 묶음에 실적, 매출 구성, 최근 공시 카드를 담는다. 카드 이름 뒤 물음표 단추는 카드의 `help` 문단을 보여 주고, 그림 아래에 해설(`text`)을 둔다.
// 재무 값이 없는 카드는 그림과 해설 대신 안내 문장(`empty`)을 쓴다. 카드가 없으면 공시 상세 절을 두지 않는다.
// 종목 상세는 `mount`로 그리고 `unmount`로 걷는다. 종목 상세가 거는 손길과 받는 값은 모두 수명(`life`)에 묶여 있어 `unmount`가 따로 걷을 것은 없다.
export const mount = (root, { data }) => stockDetail(data);
export const unmount = () => {};
function stockDetail(data) {
  document.title = data.name;
  document.getElementById("issue-bar").textContent = data.name;
  const head = Object.assign(document.createElement("h2"), { className: "issues inside" });
  const label = head.appendChild(Object.assign(document.createElement("span"), { textContent: `${INDEX_NAME[data.index]} 시총 ${data.rank}위` }));
  const box = Object.assign(document.createElement("div"), { className: "issue-box inside" });
  const page = box.appendChild(Object.assign(document.createElement("div"), { className: "issue-page on" }));
  report.replaceChildren(head, box);
  if (data.images?.length) {
    const figure = Object.assign(document.createElement("figure"), { className: "issue-image" });
    for (const image of data.images) {
      const photo = figure.appendChild(Object.assign(document.createElement("figure"), { className: "photo" }));
      const frame = photo.appendChild(Object.assign(document.createElement("div"), { className: "frame" }));
      const img = frame.appendChild(Object.assign(document.createElement("img"), { src: image.src, width: image.width, height: image.height, alt: "" }));
      img.addEventListener("click", () => viewer(img));
      frame.append(Object.assign(document.createElement("span"), { className: "ai", textContent: "AI 생성 이미지" }));
      photo.append(Object.assign(document.createElement("figcaption"), { textContent: image.caption }));
    }
    head.before(figure);
    gallery(figure);
  }
  backward(["stock", "session"], "시장");
  // 주가 카드는 종가 목록(`closes`)으로 만들고, 카드의 `live(shown)`에 정규장 다음 값을 건넨다. 실시간 사슬이 정규장을 마친 날을 더 담으면 그 종가를 붙인 목록으로 카드를 다시 만든다.
  const priceCard = (closes, ratios) => {
    const last = closes.length - 1;
    const [day, now] = closes[last], change = (now / closes[last - 1][1] - 1) * 100;
    const label = (v) => `$${Math.round(v).toLocaleString("en-US")}`, points = closes.map(([d, v]) => [d, v, label(v)]);
    const candles = ratios?.some(Boolean) ? ratios : null;
    const SPAN = [...new Set([252, 126, 63].map((days) => Math.min(days, closes.length)))];
    let span = SPAN.length - 1;
    // 그림 높이는 주가 카드의 그림 높이와 같다.
    const PLOT = 236;
    // 고른 기간의 봉 그림 설정. 선 그림이면 null이다.
    const candle = () => (candleOn && candles ? { ratios: candles, unit: candleUnit(SPAN[span]), label } : null);
    const color = change > 0 ? "#ff5c5c" : change < 0 ? "#5b9bff" : DIMS;
    const [card] = gauge({ name: `${data.name} ${data.symbol}`, asof: sessionAt("정규장", closeAt(day)), value: price(now, "달러"),
      state: [`${signed(change)}%`, color], figure: { type: "daily", points, candle: candle(), height: PLOT, start: closes.length - SPAN[span] } });
    const top = card.querySelector(".top"), asof = card.querySelector(".asof"), value = card.querySelector(".val b"), state = card.querySelector(".state");
    top.classList.add("title");
    card.prepend(Object.assign(document.createElement("div"), { className: "top" }));
    card.firstChild.append(asof);
    asof.classList.add("kind");
    asof.dataset.kind = "regular";
    // `later`는 마지막 종가 뒤의 값 {세션(`kind`), 체결가, 시각, 날짜 지점}이고 없으면 null이다. 세션이 `regular`면 아직 끝나지 않은 정규장 값이고,
    // 그 값의 [시가, 고가, 저가](`bar`)로 잠정 봉을 그린다.
    // `stop`은 그림을 눌러 고른 종가 번호이고, `most()`는 그 종가가 그림 안에 드는 가장 짧은 기간의 번호다.
    let late = asked !== "regular", later = null, stop = last;
    const most = () => { let k = SPAN.length - 1; while (k > 0 && stop < closes.length - SPAN[k]) k--; return k; };
    const kindOf = () => later?.kind;
    // [체결가, 기준 시각 글씨, 세션, 날짜 지점, 시각]. 시각으로 휴장인지(`stale`) 가린다. 지도 값만 있으면 날짜 지점을 모르므로 null이다.
    const extra = () => stop < last || !later ? null : [later.price, sessionAt(SESSION_NAME[later.kind], later.time), later.kind, later.point, later.time];
    // 가로축은 단추와 관계없이 다음 세션 값이 있으면 다음 거래일까지 담아, 단추를 바꿔도 종가 선이 움직이지 않는다.
    // 기간(`SPAN`)마다 그림 왼쪽 끝(`begin`)은 마지막 종가에서 그 거래일 수만큼 앞의 종가 번호다.
    const begin = (k) => closes.length - SPAN[k];
    const figure = (start) => {
      const shown = extra();
      return { points, extra: late && shown ? shown[0] : null, point: shown?.[3] ?? null, kind: shown?.[2], bar: late && shown ? later.bar ?? null : null,
               reach: shown ? 1 : 0, candle: candle(), height: PLOT, stop, start };
    };
    // 그림을 누르면 누른 자리에서 가장 가까운 종가 점(첫 종가 제외)을 고른다. 기간을 옮기는 도중에는 받지 않는다.
    const tappable = (svg) => {
      onTap(svg, (x) => {
        if (raf) return;
        const [xs, idx] = dailyTaps(figure(begin(span))), to = idx[nearest(xs, x)];
        if (to === stop || to < 1) return;
        feelPress();
        stop = to;
        late = asked !== "regular";
        level();
        repaint();
      });
      return svg;
    };
    const draw = (start = begin(span), bounds = null, marks = true) => {
      card.querySelector(":scope > svg").replaceWith(tappable(GAUGES.daily({ ...figure(start), bounds, marks })));
    };
    // `from` 기간에서 `to` 기간으로 가는 도중 `t`(0~1) 지점의 그림. 주가 카드처럼 왼쪽 끝과 세로 범위를 같은 곡선으로 옮기고,
    // 넓히는 동안 새로 들어온 과거 종가가 범위 밖이면 범위를 그만큼 먼저 넓힌다. 최고·최저 글자는 기간이 정해진 뒤에만 적는다.
    let raf = 0;
    const tween = (from, to, t) => {
      const e = ease(t), [a, b] = [begin(from), begin(to)], [a0, a1] = dailyBounds(figure(a)), [b0, b1] = dailyBounds(figure(b));
      const x0 = a + (b - a) * e, [c0, c1] = dailyBounds(figure(Math.floor(x0)));
      draw(x0, [Math.min(a0 + (b0 - a0) * e, c0), Math.max(a1 + (b1 - a1) * e, c1)], t >= 1);
    };
    const animate = (from) => {
      cancelAnimationFrame(raf);
      const duration = matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 550, t0 = performance.now();
      const step = (now) => { const t = duration ? Math.min(1, (now - t0) / duration) : 1; tween(from, span, t); raf = t < 1 ? requestAnimationFrame(step) : 0; };
      raf = requestAnimationFrame(step);
    };
    const seg = sessionSeg((on) => { late = on; repaint(); });
    const repaint = () => {
      const open = later?.kind === "regular";
      if (open) late = true;
      const shown = extra(), on = late && shown, move = on ? (shown[0] / now - 1) * 100 : (closes[stop][1] / closes[stop - 1][1] - 1) * 100;
      const kind = kindOf();
      seg.rename(kind);
      seg.mark(late);
      if (shown) top.append(seg.box); else seg.box.remove();
      const closed = on && stale(shown[4]);
      asof.textContent = closed ? closedText() : on ? shown[1] : sessionAt("정규장", closeAt(closes[stop][0]));
      asof.dataset.kind = closed ? "closed" : on ? kind : "regular";
      value.textContent = price(on ? shown[0] : closes[stop][1], "달러");
      card.classList.toggle("ext", !!on && !open);
      state.lastChild.textContent = `${signed(move)}%`;
      state.style.color = on && !open ? "" : move > 0 ? "#ff5c5c" : move < 0 ? "#5b9bff" : DIMS;
      state.className = `state ${on && !open ? tone(move) : ""}`;
      // 기간을 옮기는 도중이면 다음 장면이 바뀐 값으로 그린다.
      if (!raf) draw();
    };
    const zoom = card.appendChild(Object.assign(document.createElement("div"), { className: "foot" }))
      .appendChild(Object.assign(document.createElement("div"), { className: "zoom" }));
    zoom.innerHTML = `<button type="button" aria-label="기간 늘리기">−</button><span class="steps">${"<i></i>".repeat(SPAN.length)}</span><button type="button" aria-label="기간 줄이기">+</button>`;
    const [wider, narrower] = zoom.querySelectorAll("button");
    const level = () => {
      wider.disabled = span === 0;
      narrower.disabled = span >= most();
      zoom.querySelectorAll(".steps i").forEach((dot, i) => dot.classList.toggle("on", i === span));
    };
    const move = (by) => {
      const from = span;
      span = Math.max(0, Math.min(most(), span + by));
      if (span === from) return;
      level();
      animate(from);
    };
    wider.addEventListener("click", () => { feelPress(); move(-1); });
    narrower.addEventListener("click", () => { feelPress(); move(1); });
    zoomDrag(zoom.querySelector(".steps"), () => span, (i) => move(i - span));
    level();
    if (candles) zoom.append(kindButton(() => { cancelAnimationFrame(raf); raf = 0; draw(); }));
    tappable(card.querySelector(":scope > svg"));
    // 값이 바뀌었거나 휴장 판정 글씨의 지금 시각을 바꿔야 할 때 다시 그린다.
    const live = (next) => {
      const same = JSON.stringify(next) === JSON.stringify(later);
      later = next;
      if (!same || (late && later && stale(later.time))) repaint();
    };
    repaint();
    return { card, closes, live };
  };
  // 지도 화면에서 고른 세션(`session`)이 `regular`면 정규장을 고른 채로 연다.
  const asked = query.get("session");
  if (data.closes.length > 1) {
    // 정규장 다음 값은 실시간 사슬(`chain`)에서 고른다. 사슬이 정규장을 마친 날이 있고 그 뒤 값도 있으면 그날 종가를 붙인 목록으로 카드를 그리고 뒤 값을 잇는다.
    // 실시간 값이 없으면 `r/market.json` 지도 값의 마지막 종가 날짜 애프터장 체결가(`after`)를 쓴다.
    let made = null, points = null, after = null;
    const show = () => {
      const { regular, late } = chain(points, data.closes, (value) => value.stocks?.[data.symbol] ?? null);
      const [day] = data.closes[data.closes.length - 1], bar = regular.live ? points?.[regular.date]?.regular?.bars?.[data.symbol] ?? null : null;
      let closes = data.closes, ratios = data.candles, next = late;
      // 정규장을 마친 날은 그날 시가·고가·저가를 종가 대비 비율로 바꿔 봉 비율 목록에도 붙인다.
      if (regular.live && late) {
        closes = [...closes, [regular.date, regular.price]];
        ratios = ratios && [...ratios, bar ? bar.map((v) => v / regular.price) : null];
      } else if (regular.live) next = { kind: "regular", price: regular.price, time: regular.time, point: regular.date, bar };
      else if (!late && after != null) next = { kind: "after", price: after, time: afterEnd(day), point: null };
      if (made?.closes.length !== closes.length) {
        const fresh = priceCard(closes, ratios);
        made ? made.card.replaceWith(fresh.card) : page.append(fresh.card);
        made = fresh;
      }
      made.live(next);
    };
    show();
    marketed.then(({ map }) => {
      const own = map?.[data.index]?.stocks.find((stock) => stock.symbol === data.symbol);
      after = own?.after?.[map[data.index].dates.indexOf(data.closes[data.closes.length - 1][0])] ?? null;
      show();
    });
    subscribe((found) => { points = found.points[data.index]; show(); }, true);
  }
  if (data.about) page.append(Object.assign(document.createElement("h4"), { innerHTML: "<mark>기업 설명</mark>" }),
                             Object.assign(document.createElement("p"), { textContent: data.about }));
  const news = headlines(box, data.symbol);
  if (!data.cards.length) return;
  const filings = Object.assign(document.createElement("h2"), { className: "issues inside", textContent: "공시 상세" });
  news.after(filings);
  const slides = data.cards.map((c) => {
    const [card, name] = gauge(c);
    name.append(question(c.name, () => c.help.map((text) => Object.assign(document.createElement("p"), { textContent: text }))));
    const text = c.empty || c.text;
    if (text) card.append(Object.assign(document.createElement("p"), { className: c.empty ? "empty" : "", textContent: text }));
    return [card];
  });
  const bar = Object.assign(document.createElement("div"), { className: "tabs glide" });
  bar.innerHTML = '<div class="strip"></div>';
  const strip = bar.firstChild;
  data.cards.forEach((c, i) => {
    const button = Object.assign(document.createElement("button"), { textContent: c.tab });
    button.addEventListener("click", () => carousel.go(i));
    strip.appendChild(button);
  });
  const change = (i) => [...strip.children].forEach((button, j) => button.classList.toggle("on", i === j));
  filings.after(bar);
  const carousel = slider(slides, bar, { fit: true, change, name: "filings", feel: true });
  carousel.prepend(bar);
  change(0);
}
