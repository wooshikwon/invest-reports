// @ts-nocheck
import { backward } from "../shared/back";
import { issueChart } from "../shared/gauge";
import { EASE, GLIDE, glide, motion } from "../shared/motion";
import { key, life, report, visit } from "../shared/route";
import { toneTags, trail } from "../shared/sections";
import { feelPress } from "../shared/telegram";
import { gallery, viewer } from "../shared/viewer";
// 상세 이슈 해설을 이슈 목록으로 바꾼다. 이슈는 `###` 제목부터 다음 `###`·`##` 앞까지다.
// 템플릿이 검토했지만 비중을 낮춘 이슈를 번호 이슈 뒤에 두므로, 그 항목은 목록 끝의 "비중이 낮은 이슈 N건" 항목이 된다.
// 목록은 종목 뉴스 목록과 같은 모양이다. 이슈마다 제목, 첫 그림, 이슈 해설(이전 리포트는 현재 상태)의 소제목, NEW·N일 전과 이벤트 결과 스티커를 위에서 아래로 쓰고,
// 순위 번호와 방향 표식은 쓰지 않는다. 그림이 없는 이슈와 "비중이 낮은 이슈" 항목은 그림 자리를 두지 않는다.
// 상자를 누르면 주소의 `issue`에 그 이슈 번호를 적어 이슈 화면을 새 페이지로 연다. 이슈 번호는 소제목 앞 번호이고, 번호가 없는 상자는 목록 순서다.
// `focus`가 있으면 이슈 화면이다. 그 번호의 이슈 내용과 절 제목만 남기고 리포트의 다른 절은 지운다. 그 번호의 이슈가 없으면 리포트 화면을 다시 연다.
// 왼쪽 아래의 뒤로가기 단추를 누르면 앞 페이지로 돌아가고, 앞 페이지가 없으면 같은 리포트의 리포트 화면을 연다.
// `at`이 있으면 히스토리에서 그 날짜 항목을 고른 채로 연다.
// 이슈 화면의 절 제목은 보고 있는 이슈의 번호로 "이슈 N위"라고 쓰고, 검토했지만 비중을 낮춘 이슈를 보는 동안에는 "검토했지만 비중을 낮춘 이슈"로 쓴다.
// `analyzed`가 있으면 리포트 화면의 절 제목과 이슈 목록 사이에 "11/17 11:43 KST"처럼 그 시각을 쓴다. 값은 `r/index.json`의 `written`과 같은 서울 시각이다.
// `pasts`는 `r/{키}/history.json`의 값이나 그 값을 줄 약속이다. 이슈 `id`마다 앞 날짜 이슈 조각과 오늘 항목을 날짜(`day`), 이슈 해설 소제목(`title`), 조각(`html`)으로 담는다.
// 값이면 이슈 문단을 만들 때 `issue-history` 템플릿으로 바꿔 넣고, 약속이면 받은 뒤 이슈 문단 끝의 이웃 이슈 칸 앞에 넣는다. 템플릿이 이미 든 지난 리포트의 이슈는 그 템플릿을 쓴다.
export function section(title, focus = 0, at = null, analyzed = "", pasts = null) {
  const { signal } = life;
  const head = [...report.querySelectorAll("h2")].find((h) => h.textContent.trim() === title);
  if (!head) return;
  // 절 제목 글자만 바꾸도록 글자를 따로 감싼다.
  const label = Object.assign(document.createElement("span"), { textContent: head.textContent.trim() });
  head.replaceChildren(label);
  const items = [];
  for (let node = head.nextElementSibling; node && node.tagName !== "H2"; node = node.nextElementSibling) {
    if (node.tagName === "H3") {
      items.push([node]);
    } else if (items.length) {
      items[items.length - 1].push(node);
    }
  }
  if (!items.length) return;
  // 이슈 제목 앞의 번호를 지운다.
  const unnumber = (h3) => {
    const text = [...h3.childNodes].find((node) => node.nodeType === 3 && node.textContent.trim());
    if (text) text.textContent = text.textContent.replace(/^\s*\d+\.\s*/, "");
  };
  const numbers = items.map(([h3], i) => +h3.textContent.match(/^\s*(\d+)\./)?.[1] || i + 1);
  items.forEach(([h3]) => unnumber(h3));
  const other = "검토했지만 비중을 낮춘 이슈", reviewed = items[items.length - 1][0].textContent.trim() === other;
  if (reviewed) items[items.length - 1].shift().remove();
  // `step`은 이슈 화면에서 이웃 이슈로 넘기는 함수이고, `busy`는 넘기는 동안 켠다.
  let busy = false, step = null;
  const box = document.createElement("div");
  box.className = "issue-box";
  const list = box.appendChild(document.createElement("div"));
  list.className = "issue-list";
  const pages = items.map((nodes, i) => {
    const image = nodes.find((node) => node.matches?.("figure.issue-image"));
    const pick = list.appendChild(document.createElement("div"));
    const text = document.createElement("div");
    text.className = "text";
    let lead = null;
    if (reviewed && i === items.length - 1) {
      pick.className = "pick more";
      const names = [...(nodes[0]?.querySelectorAll("li") ?? [])].map((li) => (li.querySelector("strong") ?? li).textContent.trim());
      text.append(Object.assign(document.createElement("h3"), { textContent: `비중이 낮은 이슈 ${names.length}건` }));
      text.append(Object.assign(document.createElement("p"), { textContent: names.slice(0, 3).join(", ") + (names.length > 3 ? "\u00a0등" : "") }));
      pick.append(Object.assign(document.createElement("div"), { className: "lead" }));
      pick.lastChild.append(text);
    } else {
      pick.className = "pick";
      const title = nodes[0].cloneNode(true);
      title.removeAttribute("id");
      title.querySelectorAll("code").forEach((code) => code.remove());
      text.append(title);
      const src = image?.querySelector("img")?.getAttribute("src");
      if (src) text.append(Object.assign(document.createElement("img"), { className: "cover", src, alt: "", loading: "lazy" }));
      const now = nodes.map((node) => (node.tagName === "H4" ? node : node.querySelector?.("h4"))).find((h4) => ["이슈 해설", "현재 상태"].includes(h4?.querySelector("mark")?.textContent.trim()));
      if (now) text.append(Object.assign(document.createElement("p"), { textContent: [...now.childNodes].filter((n) => n.nodeName !== "MARK").map((n) => n.textContent).join("").trim() }));
      // 이슈 해설의 소제목은 목록 상자에만 쓰고, 이슈 문단에서는 말머리만 남긴다. 현재 상태 소제목은 접는 문단의 제목이므로 그대로 둔다.
      if (now?.querySelector("mark").textContent.trim() === "이슈 해설") [...now.childNodes].filter((n) => n.nodeName !== "MARK").forEach((n) => n.remove());
      if (now?.querySelector("mark").textContent.trim() === "이슈 해설") lead = now;
      // NEW·N일 전 줄 오른쪽에, 바로 앞 리포트의 이벤트 캘린더가 적은 이벤트의 결과를 다룬 이슈는 "10월 CPI 결과" 같은 스티커를 붙인다.
      const age = "new" in nodes[0].dataset ? "NEW" : nodes[0].dataset.age ? `${nodes[0].dataset.age}일 전` : "";
      const { event, eventLevel } = nodes[0].dataset;
      if (age || event) {
        const row = text.appendChild(Object.assign(document.createElement("div"), { className: "age" }));
        if (age) row.append(Object.assign(document.createElement("span"), { className: age === "NEW" ? "new" : "", textContent: age }));
        if (event) row.append(Object.assign(document.createElement("span"), { className: eventLevel === "low" ? "event low" : "event", textContent: `${event} 결과` }));
      }
      pick.append(Object.assign(document.createElement("div"), { className: "lead" }));
      pick.lastChild.append(text);
    }
    // 이슈 상자를 누르면 진동을 내고 그 이슈를 연다.
    pick.addEventListener("click", () => {
      feelPress();
      visit(key, { issue: numbers[i] });
    });
    const page = box.appendChild(document.createElement("div"));
    page.className = "issue-page";
    const shelved = pasts && !pasts.then && !nodes.some((node) => node.matches?.("template.issue-history")) && shelve(pasts[nodes[0]?.dataset.issue]);
    if (shelved) nodes.push(shelved);
    page.append(...nodes);
    if (lead) written(lead, nodes[0].dataset.written);
    if (image) gallery(image);
    const past = nodes.find((node) => node.matches?.("template.issue-history"));
    if (past) Object.assign(page, chronicle(page, past));
    return page;
  });
  // 이슈 문단마다 끝에 앞 이슈와 다음 이슈로 가는 칸을 붙인다. 검토했지만 비중을 낮춘 이슈 묶음은 이어 읽는 이슈에 넣지 않는다.
  // 칸에는 그 이슈의 그림과 목록 상자의 제목을 쓰고, 그림이 없는 이슈는 같은 크기의 빈 띠를 두고, 그림이 하나도 없는 리포트는 꼬리표와 제목만 쓴다. 칸을 누르면 진동을 내고 그 이슈로 넘긴다.
  const chain = reviewed ? pages.length - 1 : pages.length;
  const framed = pages.slice(0, chain).some((page) => page.querySelector(":scope > figure.issue-image img"));
  const pass = (i, k, side) => {
    if (k < 0 || k >= chain) return document.createElement("span");
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = side;
    const tag = Object.assign(document.createElement("span"), { className: "tag", textContent: side === "prev" ? "‹ 이전" : "다음 ›" });
    const src = pages[k].querySelector(":scope > figure.issue-image img")?.getAttribute("src");
    if (framed) {
      const shot = cell.appendChild(Object.assign(document.createElement("div"), { className: "shot" }));
      if (src) shot.append(Object.assign(document.createElement("img"), { className: "thumb", src, alt: "", loading: "lazy" }));
      shot.append(tag);
    } else {
      cell.append(tag);
    }
    cell.append(Object.assign(document.createElement("span"), { className: "title", textContent: list.children[k].querySelector("h3").textContent.trim() }));
    cell.addEventListener("click", () => {
      if (busy) return;
      feelPress();
      step(i, k);
    });
    return cell;
  };
  pages.slice(0, chain).forEach((page, i) => {
    const nav = page.appendChild(document.createElement("nav"));
    nav.className = "step";
    nav.append(pass(i, i - 1, "prev"), pass(i, i + 1, "next"));
  });
  pasts?.then?.((found) => {
    if (!found || signal.aborted) return;
    pages.forEach((page, i) => {
      if (page.querySelector(":scope > template.issue-history")) return;
      const shelved = shelve(found[items[i][0]?.dataset.issue]);
      if (!shelved) return;
      const nav = page.querySelector(":scope > nav.step");
      if (nav) nav.before(shelved); else page.append(shelved);
      Object.assign(page, chronicle(page, shelved));
    });
  });
  // 이슈 해설 말머리 앞에 히스토리 상자를 넣는다. `issue-history` 템플릿(`shelve`가 `history.json`으로 만들거나 지난 리포트의 `report.html`에 든 것)에는 같은 이슈를 다룬 앞 날짜 리포트의 이슈 조각과
  // 날짜마다 이슈 해설 소제목이 날짜 순으로 들고, 마지막 항목이 오늘이다. 상자에는 날짜와 소제목을 오늘부터 앞 날짜 순으로 한 줄씩 쓰고 보고 있는 날짜의 줄을 굵게 쓴다.
  // 최근 세 줄 아래의 앞선 줄은 접어 두고, 상자 아래 끝의 펼침 단추를 누르면 다섯 줄까지 펼친 뒤 나머지 줄은 목록 안에서 스크롤하게 한다.
  // 펼친 뒤 같은 단추(`이전 해설 숨기기`)나 최근 세 줄을 누르면 앞선 줄을 다시 접고, 앞선 줄을 누르면 펼친 채 둔다.
  // 줄을 누르면 진동을 내고, 상자 위의 제목·그림과 상자 아래의 해설·그래프를 그날 내용으로 바꿔 서서히 보이며 화면을 맨 위로 옮긴다.
  // 돌려준 `restore`는 이슈 문단을 오늘 내용으로 돌리고 앞선 줄을 다시 접으며, 이슈를 열 때마다 부른다.
  // 돌려준 `recall`은 `day` 날짜 항목을 고른다. 그 줄이 접힌 앞선 줄이면 목록을 펼치고 목록 안에서 그 줄이 보이게 스크롤한다.
  // 이슈 해설 말머리 바로 뒤에 해설을 쓴 날짜(YYYY-MM-DD)를 "2026.11.14"처럼 쓴 줄을 넣는다.
  function written(lead, date) {
    if (!date) return;
    const line = Object.assign(document.createElement("p"), { className: "written", textContent: date.replaceAll("-", ".") });
    lead.after(line);
  }
  // `history.json`의 한 이슈 항목을 `build.py`가 지난 리포트에 넣던 것과 같은 `issue-history` 템플릿으로 만든다. 항목이 없으면 `null`을 돌려준다.
  // 조각은 템플릿의 문서에서 읽어 그림을 받지 않는다.
  function shelve(days) {
    if (!days?.length) return null;
    const template = Object.assign(document.createElement("template"), { className: "issue-history" });
    for (const { day, title, html } of days) {
      const part = template.content.ownerDocument.createElement("section");
      part.dataset.day = day;
      part.dataset.title = title;
      part.innerHTML = html;
      template.content.append(part);
    }
    return template;
  }
  function chronicle(page, template) {
    const entries = [...template.content.children], today = entries.length - 1;
    const isLead = (node) => node.tagName === "H4" && node.querySelector("mark")?.textContent.trim() === "이슈 해설";
    // 날짜마다 내용을 상자 위에 둘 노드와 상자 아래에 둘 노드로 나눈다. 이슈 해설 말머리부터 상자 아래에 둔다.
    const split = (nodes) => {
      const cut = nodes.findIndex(isLead);
      return cut < 0 ? [nodes, []] : [nodes.slice(0, cut), nodes.slice(cut)];
    };
    const contents = entries.map((_, k) => (k === today ? split([...page.children].filter((node) => node !== template && !node.matches("nav.step"))) : null));
    const day = (k) => `${+entries[k].dataset.day.slice(5, 7)}/${+entries[k].dataset.day.slice(8)}`;
    const prepare = (k) => {
      const part = document.importNode(entries[k], true);
      toneTags(part);
      const h3 = part.querySelector("h3");
      if (h3) { unnumber(h3); trail(h3); }
      const lead = [...part.children].find(isLead);
      if (lead) { [...lead.childNodes].filter((n) => n.nodeName !== "MARK").forEach((n) => n.remove()); written(lead, entries[k].dataset.day); }
      part.querySelectorAll("figure.issue-chart[data-card]").forEach(issueChart);
      part.querySelectorAll("figure.issue-image").forEach(gallery);
      part.querySelectorAll("img").forEach((img) => img.addEventListener("click", () => viewer(img)));
      return split([...part.children]);
    };
    const heading = document.createElement("h4");
    heading.className = "history";
    heading.append(Object.assign(document.createElement("mark"), { textContent: "히스토리" }));
    const shelf = document.createElement("div");
    shelf.className = "history";
    const list = shelf.appendChild(Object.assign(document.createElement("div"), { className: entries.length > 3 ? "rows shut" : "rows" }));
    let current = today;
    // 펼친 목록의 높이. 다섯 줄이 넘으면 다섯째 줄의 아래 끝까지만 보인다.
    const reach = () => (list.children.length > 5 ? list.children[5].offsetTop : list.scrollHeight);
    // 앞선 줄을 다시 접고 펼침 단추의 글을 펼치기로 돌린다. 펼쳐 둔 상태에서 최근 세 줄을 누르면 목록을 맨 위로 돌리고 높이를 서서히 줄인 뒤 앞선 줄을 감춘다.
    const fold = (move) => {
      if (!list.classList.contains("open")) return;
      const from = list.offsetHeight;
      list.scrollTop = 0;
      list.classList.remove("open");
      list.style.height = "";
      label(false);
      if (!move || motion.matches) return list.classList.add("shut");
      list.animate([{ height: `${from}px` }, { height: `${list.children[3].offsetTop}px` }], { duration: GLIDE, easing: EASE })
        .finished.then(() => list.classList.contains("open") || list.classList.add("shut"));
    };
    const show = (k, move) => {
      contents[k] ??= prepare(k);
      contents[current].flat().forEach((node) => node.remove());
      heading.before(...contents[k][0]);
      shelf.after(...contents[k][1]);
      rows[current].classList.remove("on");
      rows[k].classList.add("on");
      current = k;
      if (!move) return;
      const options = { duration: motion.matches ? 0 : GLIDE, easing: EASE };
      contents[k].flat().forEach((node) => node.animate([{ opacity: 0 }, { opacity: 1 }], options));
      const cancel = () => { stop(); removeEventListener("touchstart", cancel); removeEventListener("wheel", cancel); };
      const stop = glide(scrollY, 0, (top) => scrollTo(0, top), cancel);
      addEventListener("touchstart", cancel, { passive: true });
      addEventListener("wheel", cancel, { passive: true });
    };
    const rows = entries.map((entry, k) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = k === today ? "entry on" : "entry";
      row.append(Object.assign(document.createElement("span"), { className: "day", textContent: day(k) }),
                 Object.assign(document.createElement("span"), { className: "title", textContent: entry.dataset.title }));
      row.addEventListener("click", () => {
        if (busy || k === current) return;
        feelPress();
        if (k > today - 3) fold(true);
        show(k, true);
      });
      return row;
    });
    // 오늘부터 앞 날짜 순으로 줄을 쌓는다. 접어 둔 목록은 넷째 줄부터 감춘다.
    list.append(...[...rows].reverse());
    const unfold = entries.length > 3 && shelf.appendChild(document.createElement("button"));
    // 펼침 단추의 글과 화살표. 펼친 목록에서는 같은 단추가 앞선 줄을 다시 접는다.
    const label = (opened) => {
      unfold.innerHTML = `${opened ? "이전 해설 숨기기" : `이전 해설 ${today - 2}개 펼치기`}<svg width="10" height="6" viewBox="0 0 10 6" aria-hidden="true"><path d="${opened ? "M1 5l4-4 4 4" : "M1 1l4 4 4-4"}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    };
    if (unfold) {
      unfold.type = "button";
      unfold.className = "unfold";
      label(false);
      unfold.addEventListener("click", () => {
        feelPress();
        if (list.classList.contains("open")) return fold(true);
        const from = list.offsetHeight;
        open();
        list.animate([{ height: `${from}px` }, { height: `${reach()}px` }], { duration: motion.matches ? 0 : GLIDE, easing: EASE });
      });
    }
    // 앞선 줄을 펼치고 목록 높이를 펼친 높이로 둔다.
    const open = () => {
      list.classList.remove("shut");
      list.classList.add("open");
      list.classList.toggle("long", list.children.length > 5);
      label(true);
      list.style.height = `${reach()}px`;
    };
    contents[today][0].at(-1).after(heading, shelf);
    return {
      restore: () => {
        if (current !== today) show(today, false);
        fold(false);
      },
      recall: (day) => {
        const k = entries.findIndex((entry) => entry.dataset.day === day);
        if (k < 0) return;
        if (k <= today - 3) {
          open();
          list.scrollTop += rows[k].getBoundingClientRect().top - list.getBoundingClientRect().top - (list.clientHeight - rows[k].offsetHeight) / 2;
        }
        if (k !== current) show(k, false);
      },
    };
  }
  head.classList.add("issues");
  head.after(box);
  if (analyzed) box.before(Object.assign(document.createElement("p"), { className: "issue-asof",
    textContent: `마지막 업데이트 ${analyzed.slice(5, 7)}/${analyzed.slice(8, 10)} ${analyzed.slice(11, 16)} KST` }));
  if (!focus) return;
  const shown = numbers.indexOf(focus);
  if (shown < 0) {
    const params = new URLSearchParams(location.search);
    params.delete("issue");
    params.delete("at");
    location.replace(`?${params}`);
    return;
  }
  [...report.children].forEach((node) => node === head || node === box || node.remove());
  backward(["issue", "at"], "이슈");
  const bar = document.getElementById("issue-bar");
  const rename = (next) => {
    if (label.textContent === next) return;
    label.textContent = next;
    label.animate([{ opacity: 0 }, { opacity: 1 }], { duration: motion.matches ? 0 : GLIDE });
  };
  // `i`번째 이슈 문단을 보이고, 히스토리를 오늘 내용으로 돌리고 접기 상자를 모두 닫는다.
  const enter = (i) => {
    pages.forEach((page, j) => page.classList.toggle("on", i === j));
    pages[i].restore?.();
    pages[i].querySelectorAll("details.fold").forEach((fold) => {
      fold.anim?.cancel();
      fold.want = undefined;
      fold.open = false;
      fold.lastElementChild.style.overflow = "";
    });
    rename(reviewed && i === pages.length - 1 ? other : `이슈 ${numbers[i]}위`);
    // 위쪽 한 줄 띠에는 이슈 제목만 쓰고 방향 표식은 뺀다. 비중을 낮춘 이슈 묶음은 묶음 이름을 쓴다.
    const title = reviewed && i === pages.length - 1 ? other : (() => {
      const copy = items[i][0].cloneNode(true);
      copy.querySelectorAll("code, .tags").forEach((node) => node.remove());
      return copy.textContent.trim();
    })();
    if (bar.textContent !== title) {
      bar.textContent = title;
      bar.animate([{ opacity: 0 }, { opacity: 1 }], { duration: motion.matches ? 0 : GLIDE });
    }
    return pages[i];
  };
  box.classList.add("inside");
  head.classList.add("inside");
  enter(shown);
  if (at) pages[shown].recall?.(at);
  // 보고 있는 `i`번째 이슈에서 `k`번째 이슈로 넘기고 주소의 이슈 번호를 바꾼다. 다음 이슈는 오른쪽에서, 앞 이슈는 왼쪽에서 들어온다.
  // 나가는 이슈와 들어오는 이슈를 화면 좌우 끝까지 채운 그림 사이에 10px을 두고 나란히 옮기며, 동시에 화면을 맨 위로 옮긴다. 옮기는 동안 묶음 높이를 지금 높이 아래로 줄이지 않아 화면이 튀지 않는다.
  step = (i, k) => {
    if (busy) return;
    busy = true;
    const dir = k > i ? 1 : -1, out = pages[i];
    const params = new URLSearchParams(location.search);
    params.set("issue", numbers[k]);
    params.delete("at");
    history.replaceState(history.state, "", `?${params}`);
    box.style.minHeight = `${box.offsetHeight}px`;
    box.classList.add("moving");
    out.classList.add("leaving");
    const shown = enter(k);
    const options = { duration: motion.matches ? 0 : GLIDE, easing: EASE };
    out.animate([{ transform: "none" }, { transform: `translateX(calc(${-dir} * (100vw + 10px)))` }], options);
    shown.animate([{ transform: `translateX(calc(${dir} * (100vw + 10px)))` }, { transform: "none" }], options);
    const cancel = () => { stop(); removeEventListener("touchstart", cancel); removeEventListener("wheel", cancel); };
    const stop = glide(scrollY, 0, (top) => scrollTo(0, top));
    addEventListener("touchstart", cancel, { passive: true });
    addEventListener("wheel", cancel, { passive: true });
    setTimeout(() => {
      out.classList.remove("leaving");
      box.classList.remove("moving");
      box.style.minHeight = "";
      removeEventListener("touchstart", cancel);
      removeEventListener("wheel", cancel);
      busy = false;
    }, options.duration);
  };
}

// 상세 이슈 해설의 이슈 그래프 자리에 카드를 그린다.
export function issueCharts() {
  report.querySelectorAll("figure.issue-chart[data-card]").forEach(issueChart);
}
