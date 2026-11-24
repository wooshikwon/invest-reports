// @ts-nocheck
// 기사 본문에서 종목마다 처음 나오는 이름 하나를 종목 상세로 가는 단추(`button.stock`)로 감싼다.
// 이름은 `r/market.json` 지도 종목의 부르는 이름(`call`)과 별칭(`aliases`)이다. 같은 자리에서 시작하는 이름은 긴 이름을 먼저 잡는다.
// 이름 앞 글자가 글자·숫자이면 잡지 않고, 이름 바로 뒤 글자가 글자·숫자이면 조사의 첫 글자일 때만 잡는다. 그래서 "인텔리전스", "애플리케이션", "메타버스"는 잡지 않는다.
// 일반 낱말과 겹치는 이름(`ambiguous`)은 그 기사의 종목일 때만 잡는다. 단추·링크·그림·본문 소제목(`h5`) 안의 글자는 보지 않는다.
const LETTER = /[\p{L}\p{N}]/u;
const PARTICLE = new Set("이가은는을를의와과에도로으만까보처나랑며");
const SKIP = "button, a, figure, h5, code, mark";
const ICON = '<svg class="lens" width="11" height="11" viewBox="0 0 12 12" aria-hidden="true"><circle cx="5" cy="5" r="3.6" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M7.7 7.7L10.8 10.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';

// `market`은 `r/market.json`이고, 두 지수의 지도 종목을 (이름, 심볼) 목록으로 만든다. `tickers`는 기사의 종목이다.
export function stockNames(market, tickers) {
  const forms = [];
  for (const board of Object.values(market?.map || {})) {
    for (const stock of board.stocks || []) {
      if (stock.ambiguous && !tickers.includes(stock.symbol)) continue;
      for (const name of new Set([stock.call || stock.name, ...(stock.aliases || [])])) if (name) forms.push({ name, symbol: stock.symbol });
    }
  }
  return forms.sort((a, b) => b.name.length - a.name.length);
}

const fits = (text, start, end) => {
  const before = text[start - 1], after = text[end];
  return !(before && LETTER.test(before)) && !(after && LETTER.test(after) && !PARTICLE.has(after));
};

// `nodes`(본문 블록) 안의 글자에서 종목마다 첫 이름을 단추로 감싸고, 감싼 심볼 목록을 돌려준다.
export function linkStocks(nodes, forms) {
  const done = new Set();
  for (const block of nodes) {
    if (block.matches?.(SKIP)) continue;
    const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT, { acceptNode: (node) => (node.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
    const texts = [];
    while (walker.nextNode()) texts.push(walker.currentNode);
    for (const node of texts) {
      const text = node.data;
      const hits = [];
      for (const { name, symbol } of forms) {
        if (done.has(symbol)) continue;
        for (let at = text.indexOf(name); at >= 0; at = text.indexOf(name, at + 1)) {
          if (fits(text, at, at + name.length)) { hits.push({ start: at, end: at + name.length, symbol }); break; }
        }
      }
      hits.sort((a, b) => a.start - b.start || b.end - a.end);
      const chosen = [];
      for (const hit of hits) {
        if (done.has(hit.symbol) || chosen.some((c) => hit.start < c.end && c.start < hit.end)) continue;
        chosen.push(hit);
        done.add(hit.symbol);
      }
      for (const { start, end, symbol } of chosen.sort((a, b) => b.start - a.start)) {
        const tail = node.splitText(start);
        tail.splitText(end - start);
        const button = Object.assign(document.createElement("button"), { type: "button", className: "stock" });
        button.dataset.stock = symbol;
        button.insertAdjacentHTML("beforeend", ICON);
        button.append(tail.data);
        tail.replaceWith(button);
      }
    }
  }
  return [...done];
}
