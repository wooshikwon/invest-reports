// @ts-nocheck
import { masthead } from "../shared/chrome";
import { glide, slider } from "../shared/motion";
import { key, life, report, visit } from "../shared/route";
import { feelPress } from "../shared/telegram";
// 이벤트 캘린더를 발표가 주가에 닿는 거래일마다 한 장으로 모아 넘기는 묶음으로 바꾸고, 위에 날짜 띠를 둔다.
// 날짜 띠에는 리포트 날짜 뒤 35일까지 이벤트가 있는 날짜와 리포트 날짜를 두고, 리포트 날짜 전에는 `build.py`가 넣은 지난 이벤트의 날짜를 모두 둔다.
// 거래일은 `build.py`가 소제목에 단 `data-day`를 쓰고, 35일 뒤 이벤트는 지운다. 일정과 예측 카드도 같은 거래일에 일정을 둔다. 처음에는 리포트 날짜를 보여 주고,
// 그날 이벤트가 없으면 빈 안내 한 줄을 둔다. 날짜를 누르면 그 날짜의 장으로 넘어간다. 이벤트는 소제목과 표를 늘 펼쳐 둔다.
// 날짜를 꾹 누르면 그 날짜 위에 말풍선을 띄운다. 말풍선에는 그 날짜의 리포트로 가는 단추를 둔다.
// 지난 리포트에서 `title` 절의 제목부터 다음 절 제목 앞까지를 상자 하나에 담아 막을 씌우고, 막 위에 `target` 리포트로 가는 단추를 둔다.
// 지난 리포트의 이벤트 캘린더는 그 리포트 날짜에서 본 예정이라, 날짜를 오가며 보면 지금 보는 리포트의 날짜와 헷갈린다.
export function freeze(title, target) {
  const head = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === title);
  if (!head) return;
  const wrap = Object.assign(document.createElement("div"), { className: "frozen" });
  head.before(wrap);
  for (let node = head; node && !(node !== head && node.tagName === "H2");) {
    const next = node.nextElementSibling;
    wrap.append(node);
    node = next;
  }
  const go = Object.assign(document.createElement("button"), { type: "button", className: "latest" });
  go.innerHTML = '최신 리포트로 가기<svg width="6" height="10" viewBox="0 0 6 10" aria-hidden="true"><path d="M1 1l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  go.addEventListener("click", () => { feelPress(); visit(target); });
  // 단추는 절 제목 앞에 두어, 제목 뒤 노드를 날짜 묶음으로 나누는 `events`가 단추를 건드리지 않는다.
  wrap.prepend(go);
}
export function events(date, listing) {
  const head = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === "이벤트 캘린더");
  if (!head) return;
  head.classList.add("events");
  // 지난 리포트에서는 절 바깥을 미는 동작으로 장을 넘기지 않는다. 절을 덮는 막은 `freeze`가 먼저 씌워 둔다.
  const frozen = document.documentElement.classList.contains("past");
  const shift = (day, n) => new Date(Date.parse(day) + n * 864e5).toISOString().slice(0, 10);
  const last = shift(date, 35);
  const groups = new Map([[date, []]]);
  // 첫 소제목 앞의 노드는 그대로 두고, 소제목부터 다음 소제목 앞까지는 그 소제목의 날짜 묶음에 넣는다.
  let group;
  for (let node = head.nextElementSibling; node && node.tagName !== "H2";) {
    const next = node.nextElementSibling;
    if (node.tagName === "H3") {
      const day = node.dataset.day;
      group = day <= last ? groups.get(day) || groups.set(day, []).get(day) : null;
    }
    if (group) group.push(node); else if (group === null) node.remove();
    node = next;
  }
  const days = [...groups.keys()].sort();
  if (!groups.get(date).length) {
    groups.get(date).push(Object.assign(document.createElement("div"), { className: "empty", textContent: "오늘 예정된 이벤트가 없습니다" }));
  }
  // 날짜 위 별: `build.py`가 소제목에 단 `data-level`을 세어, 중요도 높음과 보통은 지수색 별, 낮음은 회색 별로 그린다.
  const marks = (nodes) => {
    const levels = nodes.filter((node) => node.tagName === "H3" && node.dataset.level)
      .map((node) => (node.dataset.level === "low" ? "low" : "key"));
    const order = ["key", "low"].filter((level) => levels.includes(level));
    const dot = (level) => `<span class="lv-${level}"></span>`;
    const inner = levels.length > 5
      ? order.map((level) => dot(level) + `<em>${levels.filter((l) => l === level).length}</em>`).join("")
      : order.flatMap((level) => levels.filter((l) => l === level).map(dot)).join("");
    return `<i>${inner}</i>`;
  };
  const bar = document.createElement("div");
  bar.className = "days";
  bar.innerHTML = '<div class="strip"></div>';
  const strip = bar.firstChild;
  days.forEach((day) => {
    const [, m, d] = day.split("-");
    const button = document.createElement("button");
    button.innerHTML = `${marks(groups.get(day))}<b>${m}/${d}</b><small>${day === date ? "오늘" : "일월화수목금토"[new Date(day).getUTCDay()]}</small>`;
    if (day === date) button.classList.add("today");
    strip.appendChild(button);
  });
  // 띠를 i번 날짜 상자가 화면 가운데에 오는 위치로 옮긴다. `now`면 바로 옮기고, 아니면 `glide`로 미끄러뜨린다. 띠에 손을 대면 미끄러뜨리기를 멈춘다.
  // 날짜를 눌러 장이 여러 장을 지나가는 동안에는 지나가는 날짜마다 띠를 옮기지 않고, 누른 날짜로만 옮긴다.
  let seen = days.includes(history.state?.day) ? days.indexOf(history.state.day) : days.indexOf(date), aim = null, sliding = null;
  const reach = (i, now = false) => {
    sliding?.();
    const spot = strip.children[i].getBoundingClientRect();
    const left = Math.max(0, Math.min(bar.scrollWidth - bar.clientWidth,
      bar.scrollLeft + spot.left - bar.getBoundingClientRect().left - (bar.clientWidth - spot.width) / 2));
    if (now) bar.scrollLeft = left;
    else sliding = glide(bar.scrollLeft, left, (x) => (bar.scrollLeft = x), () => (sliding = null));
  };
  bar.addEventListener("touchstart", () => { sliding?.(); sliding = null; }, { passive: true });
  // 고른 날짜는 자기 기록(`day`)에 적고, 뒤로 가기로 다시 연 리포트 화면은 그 날짜의 장부터 보여 준다.
  const change = (i) => {
    [...strip.children].forEach((button, j) => button.classList.toggle("on", i === j));
    seen = i;
    history.replaceState({ ...history.state, day: days[i] }, "");
    if (aim === null) reach(i); else if (aim === i) aim = null;
  };
  // 날짜 상자는 가장 넓은 상자의 폭으로 맞추고, 띠를 보고 있는 날짜나 누른 날짜(`aim`)로 바로 옮긴다. 띠가 미끄러지는 중이면 그 날짜로 다시 미끄러뜨린다.
  const fill = () => {
    const buttons = [...strip.children];
    buttons.forEach((button) => (button.style.width = ""));
    const width = Math.max(...buttons.map((button) => button.getBoundingClientRect().width));
    buttons.forEach((button) => (button.style.width = `${width}px`));
    reach(aim ?? seen, !sliding);
  };
  // 리포트 날짜 상자가 모두 화면 왼쪽이나 오른쪽 밖으로 나가 있으면 그쪽 끝의 빛을 켠다. 상자가 조금이라도 보이면 켜지 않는다.
  const rail = Object.assign(document.createElement("div"), { className: "days-rail" });
  const edges = ["left", "right"].map((side) => Object.assign(document.createElement("i"), { className: `edge ${side}` }));
  rail.append(bar, ...edges);
  const mark = strip.children[days.indexOf(date)];
  const nudge = () => {
    if (!mark) return;
    const view = bar.getBoundingClientRect(), spot = mark.getBoundingClientRect();
    edges[0].classList.toggle("on", spot.right <= view.left);
    edges[1].classList.toggle("on", spot.left >= view.right);
  };
  bar.addEventListener("scroll", nudge, { passive: true });
  head.after(rail);
  const box = slider(days.map((day) => groups.get(day)), rail, { fit: true, start: seen, change, name: "events", area: frozen ? null : head, feel: true });
  box.prepend(rail);
  const resize = new ResizeObserver(() => { fill(); nudge(); });
  resize.observe(box);
  life.signal.addEventListener("abort", () => resize.disconnect());
  // 소제목마다 그 소제목과 다음 소제목 앞까지의 노드를 이벤트 상자 하나에 담는다.
  box.querySelectorAll(".slide > h3").forEach((h3) => {
    const event = Object.assign(document.createElement("div"), { className: "event" });
    h3.before(event);
    let node = h3.nextElementSibling;
    event.appendChild(h3);
    while (node && node.tagName !== "H3") {
      const next = node.nextElementSibling;
      event.appendChild(node);
      node = next;
    }
  });
  box.querySelectorAll("table.events:not(.judged)").forEach((table) => {
    const rows = [...table.querySelectorAll("tbody tr")].map((row) => [row, parseFloat(row.querySelector(".chance")?.textContent)]);
    const top = Math.max(...rows.map(([, chance]) => chance).filter((chance) => !isNaN(chance)));
    rows.forEach(([row, chance]) => row.classList.toggle("top", chance === top));
  });
  // 이 절이 리포트 끝이라 묶음이 짧아지면 문서가 짧아져 화면이 위로 당겨지므로, 묶음은 이미 보인 높이보다 짧아지지 않게 한다.
  // 날짜를 넘겨 묶음이 짧아지기 전에 최소 높이를 맞추도록, 묶음을 누르기 시작할 때마다 다시 잰다.
  const hold = () => {
    box.style.minHeight = `${Math.max(box.getBoundingClientRect().height, parseFloat(box.style.minHeight) || 0)}px`;
  };
  box.addEventListener("pointerdown", hold, { passive: true });
  box.querySelector(".track").addEventListener("touchstart", () => (aim = null), { passive: true });
  // 이벤트 캘린더 밖에서 일정을 고를 때 쓴다. 띠를 그 일정의 날짜로 바로 옮기고 그 날짜의 장을 바로 보여 준다.
  // 캘린더와 일정과 예측 카드는 모두 일정이 주가에 닿는 거래일에 일정을 두므로 `day`의 장을 연다.
  // 35일 뒤라 장이 없는 날짜면 `day`에 가장 가까운 날짜를 고르고, 앞뒤 날짜가 같은 거리면 뒤 날짜를 고른다.
  head.pick = (day) => {
    const far = (d) => Math.abs(Date.parse(d) - Date.parse(day));
    const near = days.reduce((best, d) => (far(d) <= far(best) ? d : best));
    const i = days.indexOf(near);
    reach(i, true);
    if (i === seen) return;
    aim = i;
    box.go(i, true);
  };
  const arrow = '<svg width="6" height="10" viewBox="0 0 6 10" aria-hidden="true"><path d="M1 1l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  // 실제 갈래 줄에 `build.py`가 결과를 다룬 이슈(`data-result`, `리포트 키/이슈 번호`)를 달았으면 그 줄 바로 아래에 "자세히 보기" 줄을 넣는다.
  // 단추를 누르면 그 이슈를 히스토리에 담은 가장 늦은 리포트(`r/index.json`의 `later`)의 이슈 화면을 열고 히스토리에서 결과 리포트 날짜를 고른다.
  // 그런 리포트가 없으면 결과 리포트의 그 이슈 화면을 연다.
  box.querySelectorAll("table.judged tbody tr.hit[data-result]").forEach((row) => {
    const [source, number] = row.dataset.result.split("/");
    const more = document.createElement("tr");
    more.className = "more";
    const cell = more.appendChild(Object.assign(document.createElement("td"), { colSpan: row.cells.length }));
    const go = cell.appendChild(Object.assign(document.createElement("button"), { type: "button" }));
    go.innerHTML = `자세히 보기${arrow}`;
    go.addEventListener("click", () => {
      feelPress();
      const [target, issue] = (listing[source]?.later?.[number] ?? row.dataset.result).split("/");
      visit(target, target === source ? { issue } : { issue, at: listing[source].date });
    });
    row.after(more);
  });
  // `own`은 그 날짜의 같은 지수 리포트로 가는 단추를 만든다. 그 날짜의 리포트가 없거나 보고 있는 리포트이면 아무것도 만들지 않는다.
  const index = key.split("-")[1];
  const own = (day) => {
    const name = Object.keys(listing).find((name) => listing[name].index === index && listing[name].date === day);
    if (!name || name === key) return null;
    const go = Object.assign(document.createElement("button"), { type: "button" });
    go.innerHTML = `이날 리포트 보기${arrow}`;
    go.addEventListener("click", () => { feelPress(); visit(name); });
    return go;
  };
  // 날짜를 450ms 동안 8px 넘게 움직이지 않고 누르고 있으면 그 날짜의 리포트를 여는 단추를 말풍선으로 띄운다. 말풍선을 띄운 누르기는 날짜를 고르지 않는다.
  // 그 날짜의 리포트가 없거나 보고 있는 리포트인 날짜는 말풍선을 띄우지 않고, 손을 떼면 그 날짜를 고른다.
  // 말풍선 밖을 누르거나 띠를 밀면 말풍선을 닫는다.
  let bubble = null, pressing = null, held = false;
  const unpop = () => { bubble?.remove(); bubble = null; };
  const pop = (button, go) => {
    unpop();
    feelPress();
    bubble = Object.assign(document.createElement("div"), { className: "bubble" });
    bubble.append(go);
    document.body.append(bubble);
    // 말풍선은 날짜 상자 위에 두고, 위쪽이 머리 상자에 가리면 아래에 둔다. 화면 양 끝에서 12px 안쪽에 두고, 꼬리는 날짜 상자 가운데를 가리킨다.
    // 말풍선은 커지며 나타나므로 크기는 줄어든 상자가 아닌 실제 크기로 잰다.
    const at = button.getBoundingClientRect(), size = { width: bubble.offsetWidth, height: bubble.offsetHeight };
    const left = Math.min(innerWidth - 12 - size.width, Math.max(12, at.left + at.width / 2 - size.width / 2));
    const below = at.top - size.height - 10 < masthead.getBoundingClientRect().bottom;
    bubble.classList.toggle("below", below);
    bubble.style.left = `${left + scrollX}px`;
    bubble.style.top = `${(below ? at.bottom + 10 : at.top - size.height - 10) + scrollY}px`;
    bubble.style.setProperty("--tail", `${at.left + at.width / 2 - left}px`);
  };
  addEventListener("pointerdown", (event) => { if (bubble && !bubble.contains(event.target)) unpop(); }, { capture: true, passive: true, signal: life.signal });
  bar.addEventListener("scroll", unpop, { passive: true });
  [...strip.children].forEach((button, i) => {
    const lift = () => { clearTimeout(pressing?.timer); pressing = null; };
    button.addEventListener("pointerdown", (event) => {
      held = false;
      pressing = { x: event.clientX, y: event.clientY, timer: setTimeout(() => {
        lift();
        const go = own(days[i]);
        if (!go) return;
        held = true;
        pop(button, go);
      }, 450) };
    }, { passive: true });
    button.addEventListener("pointermove", (event) => {
      if (pressing && Math.hypot(event.clientX - pressing.x, event.clientY - pressing.y) > 8) lift();
    }, { passive: true });
    ["pointerup", "pointercancel", "pointerleave"].forEach((type) => button.addEventListener(type, lift, { passive: true }));
    button.addEventListener("contextmenu", (event) => event.preventDefault());
  });
  [...strip.children].forEach((button, i) => button.addEventListener("click", () => {
    if (held) { held = false; return; }
    hold();
    if (i === seen) return;
    aim = i;
    reach(i);
    box.go(i);
  }));
}
