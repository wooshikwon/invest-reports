// news.js의 공개 읽기, 비밀 헤더 쓰기, 관리 요청, 달 그림 지우기를 Node 내장 시험기로 확인한다. `node --test worker/news.test.mjs`
//
// news.js가 import하는 `cloudflare:workers`는 Workers 런타임에만 있어, 모듈 해석 훅으로 DurableObject 자리를 채운 뒤 불러온다.
// Durable Object의 `ctx.storage`는 Node 내장 SQLite(`node:sqlite`)의 메모리 데이터베이스로 흉내 낸다. `sql.exec`는 결과 행을 `toArray()`로 돌려주고 BLOB은 ArrayBuffer로 오간다.
// Workers가 더한 `crypto.subtle.timingSafeEqual`은 Node의 `crypto.timingSafeEqual`로 채운다. 시각은 `Date.now`를 바꿔 고정한다. 자료와 비밀 값은 모두 지어낸 값이다.

import assert from "node:assert/strict";
import { timingSafeEqual } from "node:crypto";
import { register } from "node:module";
import { DatabaseSync } from "node:sqlite";
import { beforeEach, test } from "node:test";

const stub = "export class DurableObject { constructor(ctx, env) { this.ctx = ctx; this.env = env; } }";
const hook = `export async function resolve(specifier, context, next) {
  if (specifier === "cloudflare:workers") return { url: ${JSON.stringify("data:text/javascript," + encodeURIComponent(stub))}, shortCircuit: true };
  return next(specifier, context);
}`;
register("data:text/javascript," + encodeURIComponent(hook));
crypto.subtle.timingSafeEqual ??= (left, right) => timingSafeEqual(left, right);
const { default: worker, News, Images } = await import("./news.js");

const SECRET = "sample-news-secret";
const ORIGIN = "https://invest-news.example";
const HOUR = 3600000, DAY = 24 * HOUR;

// SQLite Durable Object 하나의 `ctx.storage`.
function storage() {
  let db = new DatabaseSync(":memory:");
  const bind = (value) => (value instanceof ArrayBuffer ? new Uint8Array(value) : value);
  const unbind = (row) => Object.fromEntries(Object.entries(row).map(([key, value]) =>
    [key, value instanceof Uint8Array ? value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength) : value]));
  return {
    sql: {
      exec(query, ...bindings) {
        const rows = db.prepare(query).all(...bindings.map(bind)).map(unbind);
        return { toArray: () => rows };
      },
    },
    transactionSync(fn) {
      db.exec("BEGIN");
      try {
        const value = fn();
        db.exec("COMMIT");
        return value;
      } catch (error) {
        db.exec("ROLLBACK");
        throw error;
      }
    },
    async deleteAll() {
      db.close();
      db = new DatabaseSync(":memory:");
    },
  };
}

// 이름마다 객체 하나를 두는 Durable Object 이름공간. `objects`로 만든 객체 이름을 확인한다.
function namespace(Class, env) {
  const objects = new Map();
  return {
    objects,
    idFromName: (name) => name,
    get: (name) => objects.get(name) ?? objects.set(name, new Class({ storage: storage() }, env)).get(name),
  };
}

let env, now;
const at = (time) => { now = Date.parse(time); };
Date.now = () => now;

beforeEach(() => {
  env = { NEWS_SECRET: SECRET };
  env.NEWS_DO = namespace(News, env);
  env.IMAGES_DO = namespace(Images, env);
  at("2026-11-20T09:00:00+09:00");
});

const call = (method, path, { body, headers = {} } = {}) => worker.fetch(new Request(`${ORIGIN}${path}`, { method, body, headers }), env);
const secret = { "X-News-Secret": SECRET };
const get = async (path) => {
  const response = await call("GET", path);
  assert.equal(response.status, 200, path);
  return response.json();
};

function sample(id, round, overrides = {}) {
  return {
    id, round, indices: ["nasdaq"], tickers: ["SAMPA"], title: `SAMPLE 제목 ${id}`,
    subheads: ["SAMPLE 첫 소제목이다", "SAMPLE 둘째 소제목이다", "SAMPLE 셋째 소제목이다"], headline: "SAMPLE 첫 소제목이다",
    html: "<p>SAMPLE 본문</p><h5>SAMPLE 소제목</h5><p>SAMPLE 문단</p>", images: [],
    charts: [{ kind: "line", title: "SAMPLE 카드" }], terms: [{ term: "SAMPLE 용어" }],
    sources: [{ url: "https://news.example/sample", time: "2026-11-20T05:10:00+09:00" }], previous: null, ...overrides,
  };
}

const post = (item, headers = secret) => call("POST", "/articles", { body: JSON.stringify(item), headers });
const put = (name, bytes = new Uint8Array([1, 2, 3]), headers = secret) =>
  call("PUT", `/images/${name}`, { body: bytes, headers: { "Content-Type": "image/webp", ...headers } });
const ids = (listed) => listed.articles.map((article) => article.id);

test("비밀 헤더가 없거나 다른 쓰기와 관리 요청은 401이고 아무것도 쓰지 않는다", async () => {
  const requests = [
    ["POST", "/articles", JSON.stringify(sample("a1", "2026-11-20-06"))],
    ["PUT", "/images/a1-1.webp", new Uint8Array([1])],
    ["DELETE", "/images?month=2026-11"],
    ["DELETE", "/articles/a1"],
    ["GET", "/admin/articles?round=2026-11-20-06"],
  ];
  for (const headers of [{}, { "X-News-Secret": "sample-news-secreu" }, { "X-News-Secret": "" }]) {
    for (const [method, path, body] of requests) {
      const response = await call(method, path, { body, headers: { "Content-Type": "image/webp", ...headers } });
      assert.equal(response.status, 401, `${method} ${path}`);
    }
  }
  const unset = await worker.fetch(new Request(`${ORIGIN}/articles`, { method: "POST", body: JSON.stringify(sample("a1", "2026-11-20-06")), headers: secret }), { ...env, NEWS_SECRET: undefined });
  assert.equal(unset.status, 401);
  assert.equal((await call("GET", "/articles/a1")).status, 404);
  assert.deepEqual(await get("/list?index=nasdaq&days=7"), { articles: [] });
  assert.equal((await call("GET", "/images/a1-1.webp")).status, 404);
});

test("올린 기사는 지수 목록, 종목 목록, 기사 읽기에 보인다", async () => {
  const item = sample("a1", "2026-11-20-06", { tickers: ["SAMPA"], previous: "a0" });
  const posted = await post(item);
  assert.equal(posted.status, 200);
  assert.deepEqual(await posted.json(), { id: "a1", replaced: false });
  const listed = await get("/list?index=nasdaq&days=3");
  assert.deepEqual(listed, { articles: [{
    id: "a1", round: "2026-11-20-06", time: "2026-11-20T06:00:00+09:00", tickers: ["SAMPA"],
    title: item.title, headline: item.headline, image: null,
  }] });
  assert.deepEqual(ids(await get("/list?ticker=SAMPA&limit=3")), ["a1"]);
  assert.deepEqual(await get("/articles/a1"), {
    id: "a1", round: "2026-11-20-06", time: "2026-11-20T06:00:00+09:00", indices: ["nasdaq"], tickers: ["SAMPA"],
    title: item.title, subheads: item.subheads, headline: item.headline, html: item.html, images: [],
    charts: item.charts, terms: item.terms, sources: item.sources, previous: "a0",
  });
  assert.deepEqual(await get("/list?index=biotech&days=7"), { articles: [] });
  assert.deepEqual(await get("/list?ticker=SAMPB&limit=10"), { articles: [] });
  assert.equal((await post(sample("a2", "2026-11-20-06", { subheads: ["SAMPLE 소제목 한 줄이다"] }))).status, 200);
  assert.deepEqual((await get("/articles/a2")).subheads, ["SAMPLE 소제목 한 줄이다"]);
});

test("소제목 줄 없이 저장된 기사는 기사 읽기에서 빈 소제목 줄을 돌려준다", async () => {
  const { subheads, html, charts, terms, sources, previous, ...item } = sample("old", "2026-11-20-06");
  env.NEWS_DO.get("news").save({ ...item, start: Date.parse("2026-11-20T06:00:00+09:00"), images: [], body: { html, charts, terms, sources, previous } });
  const read = await get("/articles/old");
  assert.deepEqual([read.subheads, read.headline, read.html], [[], item.headline, html]);
});

test("3일 목록에 4일 전 회차 기사가 없고 7일 목록에는 있으며, 목록은 늦은 회차부터 나온다", async () => {
  await post(sample("old", "2026-11-16-06"));
  await post(sample("mid", "2026-11-18-18"));
  await post(sample("new", "2026-11-20-06"));
  await post(sample("gone", "2026-11-12-18"));
  assert.deepEqual(ids(await get("/list?index=nasdaq&days=3")), ["new", "mid"]);
  assert.deepEqual(ids(await get("/list?index=nasdaq&days=7")), ["new", "mid", "old"]);
});

test("여러 종목을 단 기사는 각 종목 목록에 보이고, 종목 목록은 최신 기사부터 그 수만큼 나온다", async () => {
  await post(sample("pair", "2026-11-19-18", { indices: ["nasdaq", "biotech"], tickers: ["SAMPA", "SAMPB"] }));
  for (let day = 1; day <= 11; day += 1) await post(sample(`b${day}`, `2026-10-${String(day).padStart(2, "0")}-06`, { indices: ["biotech"], tickers: ["SAMPB"] }));
  assert.deepEqual(ids(await get("/list?ticker=SAMPA&limit=3")), ["pair"]);
  assert.deepEqual(ids(await get("/list?ticker=SAMPB&limit=3")), ["pair", "b11", "b10"]);
  assert.equal((await get("/list?ticker=SAMPB&limit=10")).articles.length, 10);
  assert.deepEqual((await get("/list?ticker=SAMPA&limit=3")).articles[0].tickers, ["SAMPA", "SAMPB"]);
  assert.deepEqual(ids(await get("/list?index=nasdaq&days=3")), ["pair"]);
  assert.deepEqual(ids(await get("/list?index=biotech&days=3")), ["pair"]);
});

test("같은 ID를 다시 올리면 기사가 하나이고 종목과 그림도 새 기사의 것이다", async () => {
  await post(sample("a1", "2026-11-20-06", { tickers: ["SAMPA", "SAMPB"], images: [{ name: "a1-1.webp", caption: "SAMPLE 설명" }] }));
  const again = await post(sample("a1", "2026-11-20-06", { title: "SAMPLE 고친 제목", tickers: ["SAMPA"] }));
  assert.deepEqual(await again.json(), { id: "a1", replaced: true });
  const listed = await get("/list?index=nasdaq&days=7");
  assert.deepEqual(ids(listed), ["a1"]);
  assert.equal(listed.articles[0].title, "SAMPLE 고친 제목");
  assert.deepEqual(await get("/list?ticker=SAMPB&limit=10"), { articles: [] });
  assert.deepEqual((await get("/articles/a1")).images, []);
  const admin = await (await call("GET", "/admin/articles?round=2026-11-20-06", { headers: secret })).json();
  assert.deepEqual(admin, { round: "2026-11-20-06", articles: [{ id: "a1", title: "SAMPLE 고친 제목", tickers: ["SAMPA"], indices: ["nasdaq"], images: [] }] });
});

test("올린 그림은 공개로 읽히고 기사에는 그림 주소와 사진 설명이 붙는다", async () => {
  const bytes = new Uint8Array([82, 73, 70, 70, 9, 8, 7]);
  const uploaded = await put("a1-1.webp", bytes);
  assert.equal(uploaded.status, 200);
  assert.deepEqual(await uploaded.json(), { name: "a1-1.webp", month: "2026-11", url: `${ORIGIN}/images/a1-1.webp` });
  assert.deepEqual([...env.IMAGES_DO.objects.keys()], ["images-2026-11"]);
  await post(sample("a1", "2026-11-20-06", { images: [{ name: "a1-1.webp", caption: "SAMPLE 설명" }, { name: "a1-2.webp" }] }));
  const image = await call("GET", "/images/a1-1.webp");
  assert.equal(image.status, 200);
  assert.equal(image.headers.get("Content-Type"), "image/webp");
  assert.match(image.headers.get("Cache-Control"), /^public, max-age=\d+$/);
  assert.deepEqual(new Uint8Array(await image.arrayBuffer()), bytes);
  const cached = await call("GET", "/images/a1-1.webp", { headers: { "If-None-Match": image.headers.get("ETag") } });
  assert.equal(cached.status, 304);
  assert.deepEqual((await get("/articles/a1")).images, [
    { url: `${ORIGIN}/images/a1-1.webp`, caption: "SAMPLE 설명" }, { url: `${ORIGIN}/images/a1-2.webp`, caption: "" },
  ]);
  assert.equal((await get("/list?index=nasdaq&days=3")).articles[0].image, `${ORIGIN}/images/a1-1.webp`);
});

test("달의 그림을 지우면 그달 그림의 공개 읽기가 404이고 그달 기사의 그림 주소가 비며 다른 달의 그림은 남는다", async () => {
  at("2026-10-31T23:30:00+09:00");
  await put("oct-1.webp");
  await post(sample("oct", "2026-10-31-18", { images: [{ name: "oct-1.webp" }] }));
  at("2026-11-01T00:30:00+09:00");
  await put("nov-1.webp");
  await post(sample("nov", "2026-11-01-06", { images: [{ name: "nov-1.webp" }] }));
  assert.deepEqual([...env.IMAGES_DO.objects.keys()], ["images-2026-10", "images-2026-11"]);
  const deleted = await call("DELETE", "/images?month=2026-10", { headers: secret });
  assert.equal(deleted.status, 200);
  assert.deepEqual(await deleted.json(), { month: "2026-10", images: 1, articles: 1 });
  assert.equal((await call("GET", "/images/oct-1.webp")).status, 404);
  assert.deepEqual((await get("/articles/oct")).images, []);
  assert.equal((await get("/list?ticker=SAMPA&limit=10")).articles.find((article) => article.id === "oct").image, null);
  assert.equal((await call("GET", "/images/nov-1.webp")).status, 200);
  assert.deepEqual((await get("/articles/nov")).images, [{ url: `${ORIGIN}/images/nov-1.webp`, caption: "" }]);
  assert.equal(env.IMAGES_DO.get("images-2026-10").read("oct-1.webp"), null);
});

test("같은 이름의 그림을 다음 달에 다시 올리면 새 달의 객체로 옮기고 앞 달을 지워도 남는다", async () => {
  at("2026-10-31T23:30:00+09:00");
  await put("a1-1.webp", new Uint8Array([1]));
  at("2026-11-01T00:30:00+09:00");
  await put("a1-1.webp", new Uint8Array([2]));
  assert.equal(env.IMAGES_DO.get("images-2026-10").read("a1-1.webp"), null);
  await call("DELETE", "/images?month=2026-10", { headers: secret });
  assert.deepEqual(new Uint8Array(await (await call("GET", "/images/a1-1.webp")).arrayBuffer()), new Uint8Array([2]));
});

test("관리 요청은 회차의 기사 목록을 돌려주고 기사 한 편을 지운다", async () => {
  await post(sample("r1", "2026-11-20-06", { images: [{ name: "r1-1.webp" }] }));
  await post(sample("r2", "2026-11-20-06", { tickers: ["SAMPB"] }));
  await post(sample("other", "2026-11-19-18"));
  const listed = await call("GET", "/admin/articles?round=2026-11-20-06", { headers: secret });
  assert.equal(listed.status, 200);
  assert.equal(listed.headers.get("Cache-Control"), "no-store");
  assert.deepEqual(await listed.json(), { round: "2026-11-20-06", articles: [
    { id: "r1", title: "SAMPLE 제목 r1", tickers: ["SAMPA"], indices: ["nasdaq"], images: ["r1-1.webp"] },
    { id: "r2", title: "SAMPLE 제목 r2", tickers: ["SAMPB"], indices: ["nasdaq"], images: [] },
  ] });
  assert.equal((await call("DELETE", "/articles/r1", { headers: secret })).status, 204);
  assert.equal((await call("DELETE", "/articles/r1", { headers: secret })).status, 404);
  assert.equal((await call("GET", "/articles/r1")).status, 404);
  assert.deepEqual(ids(await get("/list?index=nasdaq&days=3")), ["r2", "other"]);
  assert.deepEqual(ids(await get("/list?ticker=SAMPA&limit=10")), ["other"]);
  assert.equal((await call("GET", "/admin/articles?round=2026-11-20", { headers: secret })).status, 400);
});

test("형식에 맞지 않는 기사, 그림, 목록 요청은 400이고 너무 큰 본문은 413이다", async () => {
  const bad = [
    "{", JSON.stringify(null),
    JSON.stringify(sample("a b", "2026-11-20-06")),
    JSON.stringify(sample("a1", "2026-11-20-12")),
    JSON.stringify(sample("a1", "2026-02-30-06")),
    JSON.stringify(sample("a1", "2026-11-20-06", { indices: ["kospi"] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { indices: [] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { tickers: [] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { title: " " })),
    JSON.stringify(sample("a1", "2026-11-20-06", { html: null })),
    JSON.stringify(sample("a1", "2026-11-20-06", { images: [{ name: "../x" }] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { sources: [{ url: "file:///etc/passwd", time: "x" }] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { previous: 3 })),
    JSON.stringify(sample("a1", "2026-11-20-06", { subheads: undefined })),
    JSON.stringify(sample("a1", "2026-11-20-06", { subheads: [] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { subheads: ["가다", "나다", "다다", "라다"] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { subheads: ["가다", " "] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { subheads: ["가다", 3] })),
    JSON.stringify(sample("a1", "2026-11-20-06", { subheads: "가다" })),
  ];
  for (const body of bad) assert.equal((await call("POST", "/articles", { body, headers: secret })).status, 400, body.slice(0, 80));
  assert.equal((await post(sample("a1", "2026-11-20-06", { html: "x".repeat(2_000_001) }))).status, 413);
  assert.equal((await put("a1-1.webp", new Uint8Array(0))).status, 400);
  assert.equal((await put("a1-1.webp", new Uint8Array(2_000_001))).status, 413);
  assert.equal((await call("PUT", "/images/a1-1.webp", { body: new Uint8Array([1]), headers: { ...secret, "Content-Type": "text/html" } })).status, 400);
  assert.equal((await call("DELETE", "/images?month=2026-13", { headers: secret })).status, 400);
  for (const path of ["/list", "/list?index=nasdaq&days=8", "/list?index=nasdaq&days=0", "/list?index=kospi&days=3",
    "/list?ticker=SAMPA&limit=11", "/list?ticker=SAMPA", "/list?index=nasdaq&days=3&ticker=SAMPA&limit=3"]) {
    assert.equal((await call("GET", path)).status, 400, path);
  }
  assert.deepEqual(await get("/list?index=nasdaq&days=7"), { articles: [] });
});

test("공개 응답에는 CORS 헤더가 있고, 없는 경로는 404다", async () => {
  const listed = await call("GET", "/list?index=nasdaq&days=3");
  assert.equal(listed.headers.get("Access-Control-Allow-Origin"), "*");
  assert.equal(listed.headers.get("Access-Control-Allow-Methods"), "GET");
  assert.equal((await call("OPTIONS", "/list")).status, 204);
  for (const path of ["/", "/articles", "/articles/%E0%A4%A", "/images/nothing.webp", "/x"]) assert.equal((await call("GET", path)).status, 404, path);
  assert.equal((await call("PATCH", "/articles/a1", { headers: secret })).status, 405);
});
