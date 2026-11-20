// invest-news — invest-reports 미니 앱에 종목 뉴스 기사와 그림을 건네는 Cloudflare Worker.
//
// 종목 뉴스 배치는 회차를 마치면 `PUT /images/{이름}`으로 그림을, `POST /articles`로 기사를 올린다.
// 기사와 목록 정보는 SQLite Durable Object `News`의 객체 하나(`news`)에 둔다. 그림은 `Images`에 두고, 그림을 올린 달(서울 시각)마다 객체 하나(`images-{YYYY-MM}`)를 쓴다.
// `News`는 그림 이름마다 올린 달을 적어 두고, `GET /images/{이름}`은 그 달의 객체에서 그림을 읽는다.
//
// 공개 읽기는 네 경로다. 목록은 회차 시작 시각(`{날짜}-06`은 그날 06:00 KST)이 늦은 기사부터 돌려준다.
// - `GET /list?index={nasdaq|biotech}&days={1~7}`: 회차 시작 시각이 지금부터 그 일수 안인 지수의 기사
// - `GET /list?ticker={티커}&limit={1~10}`: 그 종목을 단 최신 기사
// - `GET /articles/{ID}`: 기사 한 편. 소제목 줄(`subheads`)이 없이 올린 기사는 빈 목록을 돌려준다
// - `GET /images/{이름}`: 그림
// 쓰기와 관리 요청은 비밀 헤더 `X-News-Secret`이 비밀 값 `NEWS_SECRET`과 같을 때만 받고, 다르면 401이다.
// - `POST /articles`: 기사 한 편을 올린다. 같은 ID를 다시 올리면 덮어쓴다
// - `PUT /images/{이름}`: 그림을 그달 객체에 올린다
// - `GET /admin/articles?round={회차}`: 회차의 기사 목록
// - `DELETE /articles/{ID}`: 기사 한 편을 지운다
// - `DELETE /images?month={YYYY-MM}`: 그달 객체의 그림을 모두 지우고, 기사에서 그달 그림을 뺀다

import { DurableObject } from "cloudflare:workers";

const ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/;
const NAME = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const ROUND = /^(\d{4}-\d{2}-\d{2})-(06|18)$/;
const TICKER = /^[A-Z0-9][A-Z0-9.-]{0,11}$/;
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
const TYPE = /^image\/[a-z0-9.+-]+$/;
const INDICES = new Set(["nasdaq", "biotech"]);
// 기사 제목 아래 소제목 줄 수의 상한.
const SUBHEADS = 3;
// SQLite Durable Object는 값 하나와 행 하나를 2MB까지 받는다. 기사 요청 본문과 그림 본문을 이 크기로 막는다.
const LIMIT = 2_000_000;
const DAY = 86400000;
const HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET",
  "Access-Control-Allow-Headers": "If-None-Match",
  "Access-Control-Expose-Headers": "ETag",
};

// 회차 이름의 시작 시각. `2026-11-20-18`은 `2026-11-20T18:00:00+09:00`이다. 회차 이름이 아니면 null이다.
function started(round) {
  const match = typeof round === "string" && round.match(ROUND);
  if (!match) return null;
  const time = `${match[1]}T${match[2]}:00:00+09:00`;
  const start = Date.parse(time);
  return Number.isNaN(start) || new Date(start + 9 * 3600000).toISOString().slice(0, 10) !== match[1] ? null : { time, start };
}

const text = (value) => typeof value === "string";

// `POST /articles` 본문을 저장할 기사로 고른다. 항목이 하나라도 형식에 맞지 않으면 null이다.
function article(value) {
  if (!value || typeof value !== "object") return null;
  const { id, round, indices, tickers, title, subheads, headline, html, images = [], charts = [], terms = [], sources, previous = null } = value;
  const when = started(round);
  const valid = text(id) && ID.test(id) && when
    && Array.isArray(indices) && indices.length && indices.every((name) => INDICES.has(name))
    && Array.isArray(tickers) && tickers.length && tickers.every((ticker) => text(ticker) && TICKER.test(ticker))
    && text(title) && title.trim() && text(headline) && text(html)
    && Array.isArray(subheads) && subheads.length >= 1 && subheads.length <= SUBHEADS && subheads.every((line) => text(line) && line.trim())
    && Array.isArray(images) && images.every((image) => image && text(image.name) && NAME.test(image.name) && (image.caption === undefined || text(image.caption)))
    && Array.isArray(sources) && sources.every((source) => source && text(source.url) && /^https?:\/\//.test(source.url) && text(source.time))
    && (previous === null || (text(previous) && ID.test(previous)));
  if (!valid) return null;
  return {
    id, round, start: when.start, title, headline,
    indices: [...new Set(indices)], tickers: [...new Set(tickers)],
    images: images.map(({ name, caption = "" }) => ({ name, caption })),
    body: { subheads, html, charts, terms, sources: sources.map(({ url, time }) => ({ url, time })), previous },
  };
}

// 기사와 목록 정보. 목록과 관리 요청에 쓰는 제목·머리 줄·종목·지수는 열로, 소제목 줄·본문 HTML·이슈 그래프 카드·단어표 용어·근거 기사·앞 기사는 `body` JSON으로 둔다.
// 지수와 종목으로 기사를 찾는 표, 기사에 단 그림의 순서와 사진 설명을 적는 표, 그림 이름마다 올린 달을 적는 표를 따로 둔다.
export class News extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    const sql = ctx.storage.sql;
    sql.exec(`CREATE TABLE IF NOT EXISTS articles (id TEXT PRIMARY KEY, round TEXT NOT NULL, start INTEGER NOT NULL,
      title TEXT NOT NULL, headline TEXT NOT NULL, tickers TEXT NOT NULL, indices TEXT NOT NULL, body TEXT NOT NULL)`);
    sql.exec("CREATE INDEX IF NOT EXISTS articles_start ON articles (start)");
    sql.exec("CREATE INDEX IF NOT EXISTS articles_round ON articles (round)");
    sql.exec("CREATE TABLE IF NOT EXISTS article_indices (name TEXT NOT NULL, article TEXT NOT NULL, PRIMARY KEY (name, article))");
    sql.exec("CREATE TABLE IF NOT EXISTS article_tickers (ticker TEXT NOT NULL, article TEXT NOT NULL, PRIMARY KEY (ticker, article))");
    sql.exec(`CREATE TABLE IF NOT EXISTS article_images (article TEXT NOT NULL, position INTEGER NOT NULL, name TEXT NOT NULL,
      caption TEXT NOT NULL, PRIMARY KEY (article, position))`);
    sql.exec("CREATE INDEX IF NOT EXISTS article_images_name ON article_images (name)");
    sql.exec("CREATE TABLE IF NOT EXISTS images (name TEXT PRIMARY KEY, month TEXT NOT NULL)");
  }

  // 기사 한 편의 행을 모두 지운다. 지울 기사가 있었으면 true다.
  #drop(id) {
    const sql = this.ctx.storage.sql;
    const found = sql.exec("SELECT id FROM articles WHERE id = ?", id).toArray().length > 0;
    for (const table of ["article_indices", "article_tickers", "article_images"]) sql.exec(`DELETE FROM ${table} WHERE article = ?`, id);
    sql.exec("DELETE FROM articles WHERE id = ?", id);
    return found;
  }

  // 기사 한 편을 쓴다. 같은 ID가 있으면 그 기사의 행을 모두 지우고 다시 쓴다. 덮어썼으면 true다.
  save(item) {
    const sql = this.ctx.storage.sql;
    return this.ctx.storage.transactionSync(() => {
      const replaced = this.#drop(item.id);
      sql.exec("INSERT INTO articles (id, round, start, title, headline, tickers, indices, body) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        item.id, item.round, item.start, item.title, item.headline, JSON.stringify(item.tickers), JSON.stringify(item.indices), JSON.stringify(item.body));
      for (const name of item.indices) sql.exec("INSERT INTO article_indices (name, article) VALUES (?, ?)", name, item.id);
      for (const ticker of item.tickers) sql.exec("INSERT INTO article_tickers (ticker, article) VALUES (?, ?)", ticker, item.id);
      item.images.forEach(({ name, caption }, position) =>
        sql.exec("INSERT INTO article_images (article, position, name, caption) VALUES (?, ?, ?, ?)", item.id, position, name, caption));
      return replaced;
    });
  }

  remove(id) {
    return this.ctx.storage.transactionSync(() => this.#drop(id));
  }

  #rows(where, ...bindings) {
    return this.ctx.storage.sql.exec(`SELECT a.id, a.round, a.title, a.headline, a.tickers,
        (SELECT name FROM article_images WHERE article = a.id ORDER BY position LIMIT 1) AS image
      FROM articles a ${where}`, ...bindings).toArray();
  }

  byIndex(name, since) {
    return this.#rows("JOIN article_indices i ON i.article = a.id WHERE i.name = ? AND a.start >= ? ORDER BY a.start DESC, a.id", name, since);
  }

  byTicker(ticker, limit) {
    return this.#rows("JOIN article_tickers t ON t.article = a.id WHERE t.ticker = ? ORDER BY a.start DESC, a.id LIMIT ?", ticker, limit);
  }

  byRound(round) {
    return this.ctx.storage.sql.exec(`SELECT a.id, a.title, a.tickers, a.indices,
        (SELECT json_group_array(name) FROM (SELECT name FROM article_images WHERE article = a.id ORDER BY position)) AS images
      FROM articles a WHERE a.round = ? ORDER BY a.id`, round).toArray();
  }

  read(id) {
    const sql = this.ctx.storage.sql;
    const [row] = sql.exec("SELECT id, round, title, headline, tickers, indices, body FROM articles WHERE id = ?", id).toArray();
    if (!row) return null;
    return { ...row, images: sql.exec("SELECT name, caption FROM article_images WHERE article = ? ORDER BY position", id).toArray() };
  }

  // 그림 이름의 달을 `month`로 적고, 앞서 다른 달에 올린 같은 이름이 있으면 그 달을 돌려준다.
  place(name, month) {
    const sql = this.ctx.storage.sql;
    const [row] = sql.exec("SELECT month FROM images WHERE name = ?", name).toArray();
    sql.exec("INSERT INTO images (name, month) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET month = excluded.month", name, month);
    return row && row.month !== month ? row.month : null;
  }

  month(name) {
    const [row] = this.ctx.storage.sql.exec("SELECT month FROM images WHERE name = ?", name).toArray();
    return row ? row.month : null;
  }

  // 그달 그림을 기사에서 빼고 그림의 달 기록을 지운다. 지운 그림 수와 그림을 뺀 기사 수를 돌려준다.
  forget(month) {
    const sql = this.ctx.storage.sql;
    return this.ctx.storage.transactionSync(() => {
      const gone = "SELECT name FROM images WHERE month = ?";
      const [{ images }] = sql.exec(`SELECT COUNT(*) AS images FROM (${gone})`, month).toArray();
      const [{ articles }] = sql.exec(`SELECT COUNT(DISTINCT article) AS articles FROM article_images WHERE name IN (${gone})`, month).toArray();
      sql.exec(`DELETE FROM article_images WHERE name IN (${gone})`, month);
      sql.exec("DELETE FROM images WHERE month = ?", month);
      return { images, articles };
    });
  }
}

// 한 달 동안 올린 그림. 그림 이름마다 행 하나에 형식, 본문, 올린 시각(밀리초)을 둔다.
export class Images extends DurableObject {
  #table() {
    this.ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS images (name TEXT PRIMARY KEY, type TEXT NOT NULL, body BLOB NOT NULL, stamp INTEGER NOT NULL)");
  }

  put(name, type, body) {
    this.#table();
    this.ctx.storage.sql.exec(
      "INSERT INTO images (name, type, body, stamp) VALUES (?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET type = excluded.type, body = excluded.body, stamp = excluded.stamp",
      name, type, body, Date.now());
  }

  read(name) {
    this.#table();
    const [row] = this.ctx.storage.sql.exec("SELECT type, body, stamp FROM images WHERE name = ?", name).toArray();
    return row ?? null;
  }

  remove(name) {
    this.#table();
    this.ctx.storage.sql.exec("DELETE FROM images WHERE name = ?", name);
  }

  // 객체의 저장소를 모두 지운다.
  async clear() {
    await this.ctx.storage.deleteAll();
  }
}

function same(given, secret) {
  const [left, right] = [new TextEncoder().encode(given || ""), new TextEncoder().encode(secret || "")];
  return right.byteLength > 0 && left.byteLength === right.byteLength && crypto.subtle.timingSafeEqual(left, right);
}

const newsStore = (env) => env.NEWS_DO.get(env.NEWS_DO.idFromName("news"));
const imageStore = (env, month) => env.IMAGES_DO.get(env.IMAGES_DO.idFromName(`images-${month}`));
// 서울 시각의 지금 달(YYYY-MM).
const thisMonth = () => new Date(Date.now() + 9 * 3600000).toISOString().slice(0, 7);
const reply = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), { status, headers: { ...headers, "Content-Type": "application/json" } });
const status = (code, headers = {}) => new Response(null, { status: code, headers });
// 경로에서 `prefix` 뒤의 이름. 풀 수 없는 퍼센트 표기면 빈 글이다.
function tail(path, prefix) {
  try {
    return decodeURIComponent(path.slice(prefix.length));
  } catch {
    return "";
  }
}
const address = (origin, name) => `${origin}/images/${encodeURIComponent(name)}`;
// 목록 블록에 쓰는 값. 그림은 첫 그림의 주소다.
const entry = (origin, row) => ({
  id: row.id, round: row.round, time: started(row.round).time, tickers: JSON.parse(row.tickers),
  title: row.title, headline: row.headline, image: row.image === null ? null : address(origin, row.image),
});

// 비밀 헤더가 맞는 쓰기와 관리 요청.
async function guarded(request, env, url, path) {
  const { method } = request;
  if (method === "POST" && path === "articles") {
    const body = await request.text();
    if (new TextEncoder().encode(body).byteLength > LIMIT) return status(413);
    let item = null;
    try {
      item = article(JSON.parse(body));
    } catch {}
    if (!item) return status(400);
    return reply({ id: item.id, replaced: await newsStore(env).save(item) });
  }
  if (method === "PUT" && path.startsWith("images/")) {
    const name = tail(path, "images/");
    const type = (request.headers.get("Content-Type") || "").toLowerCase();
    if (!NAME.test(name) || !TYPE.test(type)) return status(400);
    const body = await request.arrayBuffer();
    if (!body.byteLength) return status(400);
    if (body.byteLength > LIMIT) return status(413);
    const month = thisMonth();
    await imageStore(env, month).put(name, type, body);
    const before = await newsStore(env).place(name, month);
    if (before) await imageStore(env, before).remove(name);
    return reply({ name, month, url: address(url.origin, name) });
  }
  if (method === "DELETE" && path === "images") {
    const month = url.searchParams.get("month") || "";
    if (!MONTH.test(month)) return status(400);
    const counts = await newsStore(env).forget(month);
    await imageStore(env, month).clear();
    return reply({ month, ...counts });
  }
  if (method === "DELETE" && path.startsWith("articles/")) {
    const id = tail(path, "articles/");
    if (!ID.test(id)) return status(404);
    return status((await newsStore(env).remove(id)) ? 204 : 404);
  }
  if (method === "GET" && path === "admin/articles") {
    const round = url.searchParams.get("round") || "";
    if (!started(round)) return status(400);
    const rows = await newsStore(env).byRound(round);
    return reply({ round, articles: rows.map((row) => ({
      id: row.id, title: row.title, tickers: JSON.parse(row.tickers), indices: JSON.parse(row.indices), images: JSON.parse(row.images),
    })) }, 200, { "Cache-Control": "no-store" });
  }
  return status(404);
}

// 공개 읽기 요청.
async function open(request, env, url, path) {
  const fresh = { ...HEADERS, "Cache-Control": "public, max-age=60" };
  const query = url.searchParams;
  if (path === "list") {
    const index = query.get("index"), ticker = query.get("ticker");
    if (index !== null && ticker === null) {
      const days = Number(query.get("days"));
      if (!INDICES.has(index) || !Number.isInteger(days) || days < 1 || days > 7) return status(400, HEADERS);
      const rows = await newsStore(env).byIndex(index, Date.now() - days * DAY);
      return reply({ articles: rows.map((row) => entry(url.origin, row)) }, 200, fresh);
    }
    if (ticker !== null && index === null) {
      const limit = Number(query.get("limit"));
      if (!TICKER.test(ticker) || !Number.isInteger(limit) || limit < 1 || limit > 10) return status(400, HEADERS);
      const rows = await newsStore(env).byTicker(ticker, limit);
      return reply({ articles: rows.map((row) => entry(url.origin, row)) }, 200, fresh);
    }
    return status(400, HEADERS);
  }
  if (path.startsWith("articles/")) {
    const id = tail(path, "articles/");
    const row = ID.test(id) ? await newsStore(env).read(id) : null;
    if (!row) return status(404, HEADERS);
    const body = JSON.parse(row.body);
    return reply({
      id: row.id, round: row.round, time: started(row.round).time, indices: JSON.parse(row.indices), tickers: JSON.parse(row.tickers),
      title: row.title, subheads: body.subheads ?? [], headline: row.headline, html: body.html,
      images: row.images.map(({ name, caption }) => ({ url: address(url.origin, name), caption })),
      charts: body.charts, terms: body.terms, sources: body.sources, previous: body.previous,
    }, 200, fresh);
  }
  if (path.startsWith("images/")) {
    const name = tail(path, "images/");
    const month = NAME.test(name) ? await newsStore(env).month(name) : null;
    const image = month ? await imageStore(env, month).read(name) : null;
    if (!image) return status(404, HEADERS);
    const etag = `"${image.stamp}"`;
    const headers = { ...HEADERS, ETag: etag, "Cache-Control": "public, max-age=86400" };
    if (request.headers.get("If-None-Match") === etag) return status(304, headers);
    return new Response(image.body, { headers: { ...headers, "Content-Type": image.type } });
  }
  return status(404, HEADERS);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.slice(1);
    if (request.method === "OPTIONS") return status(204, HEADERS);
    if (request.method === "GET" && !path.startsWith("admin/")) return open(request, env, url, path);
    if (!["GET", "POST", "PUT", "DELETE"].includes(request.method)) return status(405, HEADERS);
    if (!same(request.headers.get("X-News-Secret"), env.NEWS_SECRET)) return status(401);
    return guarded(request, env, url, path);
  },
};
