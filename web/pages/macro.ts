// @ts-nocheck
import { candled } from "../shared/data";
import { GAUGES, columnTaps, dailyTaps, gauge } from "../shared/gauge";
import { question } from "../shared/help";
import { subscribe } from "../shared/live";
import { later, slider } from "../shared/motion";
import { life, report } from "../shared/route";
import { candleOn, candleUnit, kindButton, nearest, onTap } from "../shared/svg";
import { feelPress } from "../shared/telegram";
// 미국 거시 지표를 지표마다 한 장의 카드로 바꿔 넘기는 묶음으로 만들고, 위에 지표 이름 탭 띠를 둔다. 카드 값은 `build.py`가
// 소제목에 단 `data-card`를 쓰고, 해설은 소제목 뒤 문단이며 해설이 없으면 카드에 해설 문단을 두지 않는다. 카드 값이 없는 소제목은 해설과 함께 지우고, 카드가 하나도 없으면 절을 지운다.
// 탭을 누르면 그 지표로 넘기고, 넘기면 보고 있는 지표의 탭을 밝힌다. 카드 아래 점은 보고 있는 장을 따른다.
// 카드 이름 뒤의 물음표 단추는 그 지표의 `help` 문단을 보여 준다. 주별 막대 그림과 일별 선 그림은 누른 자리에서 가장 가까운 막대나 점을 고른다. 고른 막대나 점은 그림에서 강조하고(막대는 흰색, 선은 '현재' 표시), 카드의 큰 값과 기준일 글씨를 그 값과 날짜로 바꾸며, 앞 1년 순위(`state`)는 마지막 값의 것이므로 숨긴다. 마지막 막대나 점을 누르면 처음 상태로 돌아간다. 반원 속도계와 금리 경로는 점마다 값이 없어 누르기를 두지 않는다.
// 일별 선 그림(`daily`)을 그리는 유가 카드는 WTI 봉 비율(`r/candles.json`의 `oil`)이 오면 그림 아래 줄 오른쪽 끝에 선·봉 단추(`kindButton`)를 두고,
// 유가 카드는 실시간 값의 WTI 1분 값(`index`의 `CL=F`)이 있으면 그림 위에 그 값과 받은 시각(`loaded`)을 서울 시각으로 적는다.
// 봉 그림이면 그림이 담는 1년을 주봉으로 그린다(`candleUnit`). 봉 비율은 미국 장 날짜를 키로 적고 그림의 날짜는 그 하루 뒤이므로, 그림의 날짜에서 하루를 빼서 찾는다.
export function indicators() {
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
  // `paints[k](figure, stop)`는 k번째 카드의 그림을 `figure`로 다시 그리고, 고른 막대나 '현재' 표시를 `stop`번 점에 찍는다. 값을 주지 않으면 마지막으로 그린 값으로 다시 그린다.
  const daily = [];
  const slides = cards.map((c) => {
    const [box, name] = gauge(c);
    name.append(question(c.name, () => c.help.map((text) => Object.assign(document.createElement("p"), { textContent: text }))));
    let figure = c.figure, stop;
    const taps = { columns: columnTaps, daily: dailyTaps }[figure?.type];
    const asof = box.querySelector(".asof"), first = asof.textContent, num = box.querySelector(":scope > .val b")?.firstChild, firstNum = num?.nodeValue;
    const state = box.querySelector(".state");
    // 고른 점의 값과 날짜로 큰 값과 기준일을 바꾼다. 마지막 점이면 처음 글씨로 돌린다.
    const show = (i) => {
      const [day, value] = figure.type === "columns" ? figure.bars[i] : figure.points[i], last = i === (figure.bars ?? figure.points).length - 1;
      asof.textContent = last ? first : first.replace(/[\d/]+ KST$/, `${day.includes("-") ? `${+day.slice(5, 7)}/${+day.slice(8)}` : day} KST`);
      if (num) num.nodeValue = last ? firstNum : value.toFixed(2);
      if (state) state.style.visibility = last ? "" : "hidden";
      return last ? undefined : i;
    };
    const paint = (next = figure, at = stop) => {
      figure = next; stop = at;
      const drawn = figureOf({ ...figure, stop });
      box.querySelector(":scope > .figure")?.replaceWith(drawn);
      if (taps) onTap(drawn, (x) => {
        const [xs, idx] = taps(figure), i = idx[nearest(xs, x)];
        if (i === (stop ?? idx.at(-1))) return;
        feelPress();
        paint(figure, show(i));
      });
    };
    if (figure?.type === "daily") daily.push([box, paint]);
    if (taps) paint();
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
  subscribe((all) => {
    const tick = all.index?.["CL=F"];
    daily.forEach(([box]) => {
      let note = box.querySelector(":scope > .loaded");
      if (!note && !tick) return;
      if (!note) {
        note = Object.assign(document.createElement("small"), { className: "loaded" });
        note.setAttribute("style", "text-align:center;color:#7A828C;font-size:11px;margin-top:4px");
        box.querySelector(":scope > .figure").before(note);
      }
      note.style.display = tick ? "block" : "none";
      if (!tick) return;
      const at = new Date(tick.loaded).toLocaleTimeString("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false });
      note.textContent = `WTI $${tick.price.toFixed(2)} · ${at} KST 로드`;
    });
  });
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
