// @ts-nocheck
import { masthead } from "../shared/chrome";
import { price, signed, tone } from "../shared/format";
import { key, life, visit } from "../shared/route";
import { chain } from "../shared/live";
import { SESSION_NAME, afterEnd, closeAt, closedTag, sessionAt, sessionSeg, sessionTag, stale } from "../shared/session";
import { feelPress } from "../shared/telegram";
// 시장 페이지 첫 절인 한 눈에 보기 절에 리포트 지수 상위 20종목의 지도를 둔다. `map`은 `r/market.json`의 `map`에서 리포트 지수의 값이다.
// 지도의 확정 종가는 리포트 날짜 전날까지의 마지막 종가다. 칸 넓이는 그 종가에 주식 수를 곱한 시가총액에 비례하고, 큰 종목부터 가로세로 비가 1에 가까운 칸으로 나눠 담는다(squarified treemap).
// 가장 늦은 리포트는 그 뒤의 실시간 값을 지수 화면과 같은 날짜 지점의 사슬(`live.ts` `chain`)로 잇는다. 사슬은 날짜 지점마다 앞 세션의 애프터마켓, 주간거래, 프리마켓, 정규장 값을
// 차례로 읽고, 정규장 값이 있으면 그 값이 마지막 정규장이 된다. 정규장 단추(해)는 마지막 정규장의 체결가와 그 앞 종가 대비 등락률을, 정규장 다음 단추는 사슬의 가장 늦은
// 애프터마켓(초승달)·주간거래('晝')·프리마켓(새벽) 값과 마지막 정규장 대비 등락률을 칸과 말풍선에 쓴다. 정규장 다음 값이 없으면 단추를 두지 않고 정규장 값을 쓴다.
// 실시간 애프터장 값이 없으면 `map`의 애프터장 체결가(`after`)를 마지막 종가 날짜의 애프터마켓 값으로 쓴다. 정규장 다음 값이 없는 종목은 등락률 자리에 "–"를 쓰고 회색으로 칠한다.
// 위 줄에는 고른 값의 세션과 체결 시각을 쓰고, 그 값이 멈춰 있으면(`stale`) "휴장"과 지금 시각을 쓴다. 지난 리포트는 실시간 값을 잇지 않는다.
// 사용자가 단추를 누르기 전에는 정규장 다음 값을 고른다.
// 칸 색은 고른 값의 등락률로 정한다. 오르면 빨강, 내리면 파랑이고, 보합의 회색에서 등락률이 클수록 채도를 올려 2.5%에서 가장 선명하다. 칸이 작아 글씨가 넘치면 글씨를 줄이고,
// 그래도 넘치면 이름 대신 티커를 쓰고, 다음에 등락률을, 끝으로 티커를 뺀다.
// 칸을 누르면 누른 자리 위(위에 자리가 없으면 아래)에 말풍선을 띄워 종목 이름, 고른 값과 등락률, 종목 설명 첫 문장을 쓰고, 말풍선의 단추로 그 종목의 상세 화면(`stock`)을 연다.
// 단추가 있으면 상세 화면 주소에 고른 세션(`session`)을 적어 상세 화면의 주가 카드가 같은 세션으로 열리게 한다.
// 말풍선을 띄운 종목의 칸은 흰 테두리로 표시한다. 같은 칸을 다시 누르거나 지도 밖을 누르면 말풍선을 닫는다.
// `watch(hook)`은 실시간 값을 받을 때마다 그 지수의 날짜 지점별 값(`points`)으로 `hook`을 부른다.
export function indexMap(head, map, date, watch) {
  const box = Object.assign(document.createElement("div"), { className: "carousel indexmap" });
  box.innerHTML = '<div class="top"><span></span></div><div class="board"></div>';
  const top = box.querySelector(".top"), label = top.querySelector("span"), board = box.querySelector(".board");
  const n = map.dates.findLastIndex((d) => d < date);
  // 종목마다 지도 날짜까지의 확정 종가 [날짜, 가격]. 종가가 두 개 미만인 종목은 그리지 않는다.
  const stocks = map.stocks.map((stock) => {
    const series = map.dates.slice(0, n + 1).map((day, i) => [day, stock.closes[i]]).filter(([, v]) => v != null);
    return series.length > 1 ? { ...stock, series, cap: stock.shares * series[series.length - 1][1] } : null;
  }).filter(Boolean).sort((a, b) => b.cap - a.cap);
  if (!stocks.length) return head.remove();
  head.after(box);
  const past = document.documentElement.classList.contains("past");
  // `points`는 그 지수의 실시간 날짜 지점별 값이다. `late`는 정규장 다음 단추를 고르면 참이고, `chosen`은 사용자가 단추를 누른 뒤 참이다.
  let points = null, seen = null, late = false, chosen = false;
  const run = (stock) => chain(past ? null : points, stock.series, (value) => value.stocks?.[stock.symbol] ?? null);
  // 지수의 사슬. 지도 날짜에서 출발해 체결가가 있는 종목이 하나라도 있는 값을 잇는다. 위 줄 글씨와 단추의 세션을 정한다.
  const lead = () => chain(past ? null : points, [[map.dates[n], 1]], (value) => (Object.values(value.stocks || {}).some((v) => v != null) ? 1 : null));
  // 정규장 다음 단추의 세션. 사슬의 가장 늦은 값이 없으면 지도 값의 애프터장 체결가가 있을 때만 애프터마켓이다.
  const kindOf = () => {
    const { regular, late: next } = lead();
    if (next) return next.kind;
    return !regular.live && stocks.some((stock) => stock.after?.[n] != null) ? "after" : null;
  };
  // 칸과 말풍선에 쓰는 [가격, 등락률]. 정규장 다음 값이 없는 종목은 [null, null]이다.
  const quote = (stock) => {
    const { regular, late: next } = run(stock);
    if (!late) return [regular.price, regular.prev ? (regular.price / regular.prev - 1) * 100 : null];
    const value = next?.price ?? (kindOf() === "after" && regular.date === map.dates[n] ? stock.after?.[n] ?? null : null);
    return value == null ? [null, null] : [value, (value / regular.price - 1) * 100];
  };
  const seg = sessionSeg((on) => { late = on; chosen = true; draw(); });
  const segment = () => {
    const kind = kindOf();
    if (kind) {
      seg.rename(kind);
      if (!chosen) late = true;
      seg.mark(late);
      return top.append(seg.box);
    }
    seg.box.remove();
    late = false;
    seg.mark(false);
  };
  segment();
  // 칸 색은 보합의 무채색 회색에서 출발해 등락률의 크기만큼 빨강이나 파랑의 채도를 올리고, 2.5%부터는 가장 선명한 색으로 칠한다.
  const shade = (change) => `color-mix(in oklab, ${change > 0 ? "#ec3b47" : "#1f78ee"} ${Math.round(100 * Math.min(1, Math.abs(change) / 2.5))}%, #3a3d44)`;
  let tip = null, width = 0;
  const untip = () => { tip?.tile.classList.remove("on"); tip?.remove(); tip = null; };
  // 위 줄 기준 시각 글씨. 고른 값이 멈춰 있으면(`stale`) "휴장"과 지금 시각을 쓴다.
  const stamp = () => {
    const { regular, late: next } = lead(), kind = kindOf();
    if (late && kind) {
      const time = next?.time ?? afterEnd(map.dates[n]);
      return label.replaceChildren(stale(time) ? closedTag() : sessionTag(kind, sessionAt(SESSION_NAME[kind], time)));
    }
    // 정규장 값이 사슬의 가장 늦은 값일 때만 휴장을 가린다. 그 뒤 값이 있으면 이미 끝난 정규장이라 그 시각 그대로 쓴다.
    label.replaceChildren(!regular.live ? sessionTag("regular", sessionAt("정규장", closeAt(regular.date)))
      : !next && stale(regular.time) ? closedTag() : sessionTag("regular", sessionAt("정규장", regular.time)));
  };
  const draw = () => {
    untip();
    stamp();
    board.replaceChildren();
    const W = board.clientWidth, H = Math.round(W * .95), total = stocks.reduce((sum, stock) => sum + stock.cap, 0);
    board.style.height = `${H}px`;
    // 남은 칸(`x`, `y`, `w`, `h`)의 짧은 변을 따라 한 줄(`row`)씩 쌓는다. 종목을 줄에 더해 줄에서 가장 길쭉한 칸의 비가 나빠지면 줄을 닫는다.
    let x = 0, y = 0, w = W, h = H, row = [];
    const sum = (cells) => cells.reduce((s, cell) => s + cell.area, 0);
    const worst = (cells, side) => {
      const s = sum(cells), areas = cells.map((cell) => cell.area);
      return Math.max(side * side * Math.max(...areas) / (s * s), s * s / (side * side * Math.min(...areas)));
    };
    const lay = () => {
      const thick = sum(row) / Math.min(w, h);
      let at = 0;
      row.forEach((cell) => {
        const long = cell.area / thick;
        Object.assign(cell, w >= h ? { x, y: y + at, w: thick, h: long } : { x: x + at, y, w: long, h: thick });
        at += long;
      });
      if (w >= h) { x += thick; w -= thick; } else { y += thick; h -= thick; }
      row = [];
    };
    const cells = stocks.map((stock) => ({ stock, area: stock.cap / total * W * H }));
    cells.forEach((cell) => {
      if (row.length && worst([...row, cell], Math.min(w, h)) > worst(row, Math.min(w, h))) lay();
      row.push(cell);
    });
    if (row.length) lay();
    // 칸마다 이름·종목 기호·종목 기호만 순서로, 각 글자를 18px 아래에서 10px까지 줄여 가며 처음 들어가는 것을 쓴다.
    // 모든 칸의 시도를 한 차례씩 함께 쓰고 함께 재어, 차례마다 배치를 한 번만 한다. 칸은 크기가 정해진 절대 위치라 서로의 결과를 바꾸지 않는다.
    const tiles = cells.map((cell) => {
      const tile = board.appendChild(document.createElement("button"));
      const [, change] = quote(cell.stock);
      tile.type = "button";
      tile.stock = cell.stock;
      Object.assign(tile.style, { left: `${cell.x + 1}px`, top: `${cell.y + 1}px`, width: `${cell.w - 2}px`, height: `${cell.h - 2}px`, background: shade(change ?? 0) });
      tile.append(Object.assign(document.createElement("b"), { textContent: cell.stock.name }),
                  Object.assign(document.createElement("span"), { textContent: change == null ? "–" : `${signed(change)}%` }));
      const [name, move] = tile.children, tries = [];
      [[cell.stock.name, true], [cell.stock.symbol, true], [cell.stock.symbol, false]].forEach(([text, both]) => {
        for (let size = Math.round(Math.min(18, Math.max(10, Math.sqrt(cell.w * cell.h) / 7))); size >= 10; size--) tries.push([text, both, size]);
      });
      return { tile, name, move, tries, at: 0, placed: false };
    });
    const fits = ({ tile, name, move }) => [name, move].every((part) => part.hidden || part.scrollWidth <= tile.clientWidth - 2)
      && [name, move].reduce((s, part) => s + (part.hidden ? 0 : part.offsetHeight + 1), 0) <= tile.clientHeight - 2;
    for (let open = tiles; open.length;) {
      open.forEach((t) => {
        const [text, both, size] = t.tries[t.at];
        t.name.textContent = text;
        t.move.hidden = !both;
        t.tile.style.fontSize = `${size}px`;
      });
      open = open.filter((t) => !(t.placed = fits(t)) && ++t.at < t.tries.length);
    }
    tiles.forEach(({ name, placed }) => (name.hidden = !placed));
  };
  board.addEventListener("click", (event) => {
    const tile = event.target.closest(".board > button");
    if (!tile) return;
    const again = tip?.tile === tile;
    untip();
    if (again) return;
    feelPress();
    const stock = tile.stock, [now, move] = quote(stock);
    tip = Object.assign(document.createElement("div"), { className: "bubble quote" });
    tip.tile = tile;
    // 종목 상세는 늘 최신 값을 보이므로, 지난 리포트의 말풍선에는 상세로 가는 단추를 두지 않는다.
    const past = document.documentElement.classList.contains("past");
    tip.innerHTML = `<b></b><p class="price"><span></span><span class="${tone(move ?? 0)}"></span></p><p class="lead"></p>`
      + (past ? "" : '<button type="button">자세히 보기<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg></button>');
    tip.querySelector("b").textContent = stock.name;
    const [value, change] = tip.querySelectorAll("p.price span");
    value.textContent = now != null ? price(now, "달러") : `${SESSION_NAME[kindOf()]} 체결 없음`;
    change.textContent = move == null ? "" : `${signed(move)}%`;
    const lead = tip.querySelector("p.lead");
    lead.textContent = (stock.about || "").split(/(?<=다\.)\s+/)[0];
    lead.hidden = !stock.about;
    const session = !seg.box.isConnected ? {} : { session: !late ? "regular" : kindOf() };
    tip.querySelector("button")?.addEventListener("click", () => { feelPress(); visit(key, { stock: stock.symbol, ...session }); });
    board.append(tip);
    tile.classList.add("on");
    // 키보드로 누르면 누른 자리가 없으므로 칸 가운데에 띄운다.
    const at = board.getBoundingClientRect(), r = tile.getBoundingClientRect();
    const [cx, cy] = event.detail ? [event.clientX, event.clientY] : [r.left + r.width / 2, r.top + r.height / 2];
    const px = cx - at.left, py = cy - at.top, size = { width: tip.offsetWidth, height: tip.offsetHeight };
    const left = Math.min(at.width - size.width, Math.max(0, px - size.width / 2));
    const below = cy - size.height - 14 < masthead.getBoundingClientRect().bottom;
    tip.classList.toggle("below", below);
    tip.style.left = `${left}px`;
    tip.style.top = `${below ? py + 14 : py - size.height - 14}px`;
    tip.style.setProperty("--tail", `${Math.min(size.width - 18, Math.max(18, px - left))}px`);
  });
  addEventListener("pointerdown", (event) => { if (tip && !board.contains(event.target)) untip(); }, { capture: true, passive: true, signal: life.signal });
  const resize = new ResizeObserver(() => {
    if (!board.clientWidth || board.clientWidth === width) return;
    width = board.clientWidth;
    draw();
  });
  resize.observe(board);
  life.signal.addEventListener("abort", () => resize.disconnect());
  // 실시간 값이 바뀔 때만 다시 그리고, 그대로면 위 줄의 휴장 시각만 고친다. 지도를 아직 그리지 않았으면 처음 그릴 때 새 값을 쓴다.
  watch((found) => {
    const text = JSON.stringify(found ?? null);
    if (text === seen) {
      if (width) stamp();
      return;
    }
    seen = text;
    points = found;
    segment();
    if (width) draw();
  });
}
