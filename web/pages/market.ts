// @ts-nocheck
import { masthead } from "../shared/chrome";
import { price, signed, tone } from "../shared/format";
import { key, life, visit } from "../shared/route";
import { SESSION_NAME, afterEnd, closeAt, closedTag, sessionAt, sessionSeg, sessionTag, stale } from "../shared/session";
import { feelPress } from "../shared/telegram";
// 시장 페이지 첫 절인 한 눈에 보기 절에 리포트 지수 상위 20종목의 지도를 둔다. `map`은 `r/market.json`의 `map`에서 리포트 지수의 값이다.
// 지도는 리포트 날짜 전날까지의 마지막 종가로 그린다. 칸 넓이는 종가에 주식 수를 곱한 시가총액에 비례하고, 큰 종목부터 가로세로 비가 1에 가까운 칸으로 나눠 담는다(squarified treemap).
// 그 날짜의 애프터장 마지막 체결가가 있으면 지도 위 줄 오른쪽에 정규장(해)·애프터장(초승달) 단추를 두고 애프터장을 고른 채로 연다. 애프터장을 고르면 칸 넓이는 그대로 두고
// 칸과 말풍선의 가격과 등락률, 칸 색을 애프터장 체결가와 그 체결가의 정규장 종가 대비 등락률로 바꾼다. 애프터장 체결가가 없는 종목은 등락률 자리에 "–"를 쓰고 회색으로 칠한다.
// 애프터장 체결가는 지도 값의 `after`이고, 그 값이 없는 종목은 애프터장 값(실시간 값 `afterhours`)의 지도 날짜 체결가다.
// 애프터장이 닫힌 뒤 지도 날짜의 애프터장 값에 주간거래 값(`overnight`)이 붙으면 애프터장 단추를 주간거래('晝') 단추로 바꾸고, 주간거래 체결가로 같은 자리를 그린다.
// 주간거래 체결이 아직 없는 종목은 애프터장 체결가를 쓴다.
// `watch`는 리포트 날짜의 프리장 값(실시간 값 `premarket`)과 지수의 애프터장 값을 받을 때마다 부를 함수를 건다. 애프터장 값을 받으면 위 줄에 체결가를 받은 뉴욕 시각을 쓴다.
// 프리장 값의 앞 세션이 지도 날짜이고 체결가가 있는 종목이 있으면 애프터장 단추를 다음날 프리장(새벽) 단추로 바꾸고, 애프터장 체결가 대신 프리장 체결가로 같은 자리를 그린다.
// 위 줄에는 프리장 날짜와 체결가를 받은 뉴욕 시각을 쓴다. 그 값이 리포트 날짜의 정규장 값(`phase`가 `regular`)이면 단추를 정규장 단추 하나로 줄이고,
// 정규장 체결가로 같은 자리를 그리며, 위 줄에 정규장과 체결가를 받은 뉴욕 시각을 쓴다.
// 사용자가 단추를 누르기 전에는 가장 늦은 세션(프리장, 주간거래, 애프터장, 정규장 순서)을 고른다.
// 칸 색은 앞 세션 종가 대비 등락률로 정한다. 오르면 빨강, 내리면 파랑이고, 보합의 회색에서 등락률이 클수록 채도를 올려 2.5%에서 가장 선명하다. 칸이 작아 글씨가 넘치면 글씨를 줄이고,
// 그래도 넘치면 이름 대신 티커를 쓰고, 다음에 등락률을, 끝으로 티커를 뺀다.
// 칸을 누르면 누른 자리 위(위에 자리가 없으면 아래)에 말풍선을 띄워 종목 이름, 종가와 등락률, 종목 설명 첫 문장을 쓰고, 말풍선의 단추로 그 종목의 상세 화면(`stock`)을 연다.
// 단추가 있으면 상세 화면 주소에 고른 세션(`session`: `regular`, `after`, `overnight`, `pre`)을 적어 상세 화면의 주가 카드가 같은 세션으로 열리게 한다.
// 말풍선을 띄운 종목의 칸은 흰 테두리로 표시한다. 같은 칸을 다시 누르거나 지도 밖을 누르면 말풍선을 닫는다.
export function indexMap(head, map, date, watch) {
  const box = Object.assign(document.createElement("div"), { className: "carousel indexmap" });
  box.innerHTML = '<div class="top"><span></span></div><div class="board"></div>';
  const top = box.querySelector(".top"), label = top.querySelector("span"), board = box.querySelector(".board");
  // `i`번 날짜부터 거슬러 가며 처음 만나는 종가와 그 날짜 번호. 종가가 없으면 `[null, -1]`이다.
  const close = (stock, i) => {
    for (let k = i; k >= 0; k--) if (stock.closes[k] != null) return [stock.closes[k], k];
    return [null, -1];
  };
  const n = map.dates.findLastIndex((d) => d < date);
  const stocks = map.stocks.map((stock) => {
    const [now, k] = close(stock, n), [before] = close(stock, k - 1);
    return now && before ? { ...stock, now, change: (now / before - 1) * 100, cap: stock.shares * now, fresh: k === n } : null;
  }).filter(Boolean).sort((a, b) => b.cap - a.cap);
  if (!stocks.length) return head.remove();
  head.after(box);
  // 정규장 다음 단추(애프터마켓이나 다음날 프리마켓)를 고르거나 리포트 날짜의 정규장 값을 그리면 참이다. `early`는 지도 날짜 다음 프리장이나 정규장의 값이고,
  // `after`는 지도 날짜의 애프터장 값이고 `night`는 그 값에 붙은 주간거래 값이며, 없으면 null이다. `kind`는 정규장 다음 단추의 세션이고, `chosen`은 사용자가 단추를 누른 뒤 참이다.
  let late = false, early = null, after = null, night = null, chosen = false, kind = "after";
  // 정규장 다음 단추의 체결가. 지도 날짜에 종가가 없는 종목은 null이다.
  const extra = (stock) => !stock.fresh ? null : early ? early.stocks[stock.symbol] ?? null
    : night?.stocks[stock.symbol] ?? stock.after?.[n] ?? after?.stocks[stock.symbol] ?? null;
  // 칸과 말풍선에 쓰는 [가격, 등락률]. 체결가가 없는 종목의 애프터장·프리장 값은 [null, null]이다.
  const quote = (stock) => !late ? [stock.now, stock.change] : extra(stock) == null ? [null, null] : [extra(stock), (extra(stock) / stock.now - 1) * 100];
  const seg = sessionSeg((on) => { late = on; chosen = true; draw(); });
  // 체결가가 있는 종목이 있으면 단추를 두고 두 번째 단추 이름을 정하고, 없으면 단추를 빼고 정규장 값으로 돌린다.
  const segment = () => {
    kind = early ? (early.phase === "regular" ? "regular" : "pre") : night ? "overnight" : "after";
    seg.rename(kind, kind === "pre" ? "다음날 프리마켓" : undefined);
    if (stocks.some((stock) => extra(stock) != null)) {
      if (!chosen || kind === "regular") late = true;
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
  // 위 줄 기준 시각 글씨. 정규장 다음 세션 값이 휴장으로 멈춰 있으면(`stale`) "휴장"과 지금 시각을 쓴다.
  const stamp = () => {
    const day = late && early ? date : map.dates[n], time = early ? early.time : night ? night.time : after?.time ?? afterEnd(day);
    label.replaceChildren(!late ? sessionTag("regular", sessionAt("정규장", closeAt(day))) : stale(time) ? closedTag()
      : sessionTag(kind, sessionAt(SESSION_NAME[kind], time)));
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
    value.textContent = now != null ? price(now, "달러") : `${SESSION_NAME[kind]} 체결 없음`;
    change.textContent = move == null ? "" : `${signed(move)}%`;
    const lead = tip.querySelector("p.lead");
    lead.textContent = (stock.about || "").split(/(?<=다\.)\s+/)[0];
    lead.hidden = !stock.about;
    const session = !seg.box.isConnected || kind === "regular" ? {} : { session: !late ? "regular" : kind };
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
  // 프리장 값과 애프터장 값은 받은 시각이 바뀔 때만 다시 그린다. 지도를 아직 그리지 않았으면 처음 그릴 때 새 값을 쓴다.
  watch((own, afters) => {
    const traded = (found) => found && Object.values(found.stocks).some((value) => value != null) ? found : null;
    const found = own?.session === map.dates[n] ? traded(own) : null, tail = traded(afters?.[map.dates[n]]), dark = traded(tail?.overnight);
    if (found?.time === early?.time && tail?.time === after?.time && dark?.time === night?.time) {
      if (width) stamp();
      return;
    }
    early = found;
    after = tail;
    night = dark;
    segment();
    if (width) draw();
  });
}
