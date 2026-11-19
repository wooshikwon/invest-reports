// @ts-nocheck
import { candled } from "../shared/data";
import { GAUGES, gauge } from "../shared/gauge";
import { question } from "../shared/help";
import { later, slider } from "../shared/motion";
import { dial, rewindOffset } from "../shared/rewind";
import { key, life, report } from "../shared/route";
import { candleOn, candleUnit, kindButton } from "../shared/svg";
// 미국 거시 지표를 지표마다 한 장의 카드로 바꿔 넘기는 묶음으로 만들고, 위에 지표 이름 탭 띠를 둔다. 카드 값은 `build.py`가
// 소제목에 단 `data-card`를 쓰고, 해설은 소제목 뒤 문단이며 해설이 없으면 카드에 해설 문단을 두지 않는다. 카드 값이 없는 소제목은 해설과 함께 지우고, 카드가 하나도 없으면 절을 지운다.
// 탭을 누르면 그 지표로 넘기고, 넘기면 보고 있는 지표의 탭을 밝힌다. 카드 아래 점은 보고 있는 장을 따른다.
// 카드 이름 뒤의 물음표 단추는 그 지표의 `help` 문단을 보여 준다. 카드의 그림과 해설 사이에는 날짜 슬라이더를 둔다(`indicatorRewind`).
// 일별 선 그림(`daily`)을 그리는 유가 카드는 WTI 봉 비율(`r/candles.json`의 `oil`)이 오면 그림 아래 줄 오른쪽 끝에 선·봉 단추(`kindButton`)를 두고,
// 봉 그림이면 그림이 담는 1년을 주봉으로 그린다(`candleUnit`). 봉 비율은 미국 장 날짜를 키로 적고 그림의 날짜는 그 하루 뒤이므로, 그림의 날짜에서 하루를 빼서 찾는다.
export function indicators(date) {
  const head = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === "미국 거시 지표");
  if (!head) return;
  // 첫 소제목 앞의 노드는 그대로 두고 묶음을 그 뒤에 둔다.
  const cards = [];
  let card = null, started = false, anchor = head;
  for (let node = head.nextElementSibling; node && node.tagName !== "H2";) {
    const next = node.nextElementSibling;
    if (node.tagName === "H3") {
      started = true;
      card = node.dataset.card ? { name: node.textContent.trim(), ...JSON.parse(node.dataset.card), text: [] } : null;
      if (card) cards.push(card);
    } else if (card) card.text.push(node.textContent.trim());
    if (started) node.remove(); else anchor = node;
    node = next;
  }
  if (!cards.length) {
    for (let node = head.nextElementSibling; node && node.tagName !== "H2";) { const next = node.nextElementSibling; node.remove(); node = next; }
    head.remove();
    return;
  }
  let oil = null;
  const figureOf = (figure) => {
    const ratios = oil && candleOn && figure.type === "daily"
      ? figure.points.map(([day]) => oil[new Date(Date.parse(day) - 864e5).toISOString().slice(0, 10)] ?? null) : null;
    const drawn = GAUGES[figure.type](ratios ? { ...figure, candle: { ratios, unit: candleUnit(figure.points.length), label: (v) => `$${v.toFixed(2)}` } } : figure);
    drawn.classList.add("figure");
    return drawn;
  };
  // `paints[k](figure, stop)`는 k번째 카드의 그림을 `figure`로 다시 그리고, 일별 선 그림이면 '현재' 표시를 `stop`번 점에 찍는다. 값을 주지 않으면 마지막으로 그린 값으로 다시 그린다.
  const spots = [], paints = [], daily = [];
  const slides = cards.map((c) => {
    const [box, name] = gauge(c);
    name.append(question(c.name, () => c.help.map((text) => Object.assign(document.createElement("p"), { textContent: text }))));
    let figure = c.figure, stop;
    const paint = (next = figure, at = stop) => { figure = next; stop = at; box.querySelector(":scope > .figure")?.replaceWith(figureOf({ ...figure, stop })); };
    paints.push(paint);
    if (figure?.type === "daily") daily.push([box, paint]);
    spots.push(box.appendChild(document.createElement("div")));
    const text = c.text.filter(Boolean).join(" ");
    if (text) box.append(Object.assign(document.createElement("p"), { textContent: text }));
    return [box];
  });
  const bar = document.createElement("div");
  bar.className = "tabs glide";
  bar.innerHTML = '<div class="strip"></div>';
  const strip = bar.firstChild;
  cards.forEach((c, i) => {
    const button = Object.assign(document.createElement("button"), { textContent: c.tab });
    button.addEventListener("click", () => box.go(i));
    strip.appendChild(button);
  });
  let seen = 0;
  const change = (i) => {
    [...strip.children].forEach((button, j) => button.classList.toggle("on", i === j));
    const room = Math.max(0, strip.scrollWidth - (bar.clientWidth - 2 * parseFloat(getComputedStyle(bar).paddingLeft)));
    strip.style.transform = `translateX(${-Math.min(room, strip.children[(seen = i)].offsetLeft)}px)`;
  };
  anchor.after(bar);
  const box = slider(slides, bar, { fit: true, change, name: "indicators", area: head, feel: true });
  box.prepend(bar);
  later(() => change(seen));
  const resize = new ResizeObserver(() => {
    strip.style.transition = "none";
    change(seen);
    strip.getBoundingClientRect();
    strip.style.transition = "";
  });
  resize.observe(box);
  life.signal.addEventListener("abort", () => resize.disconnect());
  indicatorRewind(cards, spots, paints, date);
  candled.then((found) => {
    if (!found.oil) return;
    oil = found.oil;
    daily.forEach(([box, paint]) => {
      const foot = Object.assign(document.createElement("div"), { className: "foot" });
      box.querySelector(":scope > .figure").after(foot);
      foot.appendChild(Object.assign(document.createElement("div"), { className: "zoom" })).append(kindButton(() => paint()));
      if (candleOn) paint();
    });
  });
}

// 지표 카드마다 그림과 해설 사이의 자리 `spots`에 지난 리포트 날짜로 되감는 슬라이더를 둔다(build.py `r/rewind-{지수}/indicators.json`).
// 리포트 날짜와 그 앞 날짜 가운데 그 지표의 카드 값이 있는 날짜만 고를 수 있고, 리포트 날짜에 카드 값이 없는 지표에는 슬라이더를 두지 않는다.
// 날짜를 고르면 그날 카드 값으로 그 카드의 기준일·값·그림만 다시 그리고, 이름과 물음표 단추, 해설은 리포트 날짜의 것을 그대로 둔다.
// 일별 선 그림(유가)은 리포트 날짜의 그림을 그대로 두고, 그날 그림의 마지막 날짜에 '현재' 표시만 옮겨 찍는다.
export function indicatorRewind(cards, spots, paints, date) {
  fetch(`r/rewind-${key.split("-")[1]}/indicators.json`, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null)).then((data) => {
    if (!data) return;
    const frames = data.frames.filter((frame) => frame.day <= date && rewindOffset(frame.day, date) >= 0);
    cards.forEach((c, k) => {
      const own = frames.filter((frame) => frame.cards[c.name]);
      const start = own.findIndex((frame) => frame.day === date);
      if (start < 0) return;
      const box = spots[k].parentNode;
      let drawn = start, frame = 0;
      const draw = () => {
        frame = 0;
        const [fresh] = gauge({ name: c.name, ...own[drawn].cards[c.name] });
        box.querySelector(".asof").textContent = fresh.querySelector(".asof").textContent;
        const val = box.querySelector(":scope > .val"), next = fresh.querySelector(":scope > .val");
        if (val && next) val.replaceWith(next); else if (val) val.remove(); else if (next) box.querySelector(".top").after(next);
        const figure = own[drawn].cards[c.name].figure;
        if (figure.type !== "daily") paints[k](figure);
        else paints[k](c.figure, c.figure.points.findLastIndex(([day]) => day <= figure.points.at(-1)[0]));
      };
      dial(spots[k], date, own.map((f) => f.day), start, (i) => {
        if (i === drawn) return;
        drawn = i;
        if (!frame) frame = requestAnimationFrame(draw);
      });
    });
  }).catch(() => {});
}
