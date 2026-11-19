// invest-live — invest-reports 미니 앱에 실시간 값(프리장·정규장 값, 애프터장 값, 판단 배치 진척률)을 건네는 Cloudflare Worker.
//
// claude-svr의 live.py가 1분마다 `premarket`·`afterhours`를, build.py `--progress`가 `progress`를
// SQLite Durable Object `Live`에 `POST /write/{이름}`으로 쓰고, `GET /`가 세 값을 한 응답으로 돌려준다. 다른 경로는 404다.
// 값은 공개 리포트가 그리는 체결가와 진척 단계라 누구에게나 돌려준다. 쓰기는 비밀 헤더 `X-Live-Secret`이 비밀 값 `LIVE_SECRET`과 같을 때만 받는다.

import { DurableObject } from "cloudflare:workers";

const NAMES = new Set(["premarket", "afterhours", "progress"]);
const HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET",
  "Access-Control-Allow-Headers": "If-None-Match",
  "Access-Control-Expose-Headers": "ETag",
};

// 값 이름마다 행 하나에 값 JSON 원문과 쓴 시각(밀리초)을 둔다.
export class Live extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    ctx.storage.sql.exec("CREATE TABLE IF NOT EXISTS live (name TEXT PRIMARY KEY, value TEXT NOT NULL, stamp INTEGER NOT NULL)");
  }

  write(name, value) {
    this.ctx.storage.sql.exec(
      "INSERT INTO live (name, value, stamp) VALUES (?, ?, ?) ON CONFLICT(name) DO UPDATE SET value = excluded.value, stamp = excluded.stamp",
      name, value, Date.now());
  }

  read() {
    return this.ctx.storage.sql.exec("SELECT name, value, stamp FROM live ORDER BY name").toArray();
  }
}

// DO에서 읽은 `GET /` 응답 본문과 ETag. 읽은 분이 지나면 다시 읽는다.
let cached = null;

const minute = (now) => Math.floor(now / 60000);

async function shared(env) {
  const now = Date.now();
  if (cached && cached.minute === minute(now)) return cached;
  const rows = await env.LIVE_DO.get(env.LIVE_DO.idFromName("live")).read();
  const body = `{${rows.map((row) => `${JSON.stringify(row.name)}:${row.value}`).join(",")}}`;
  cached = { minute: minute(now), body, etag: `"${rows.map((row) => `${row.name}-${row.stamp}`).join(".")}"` };
  return cached;
}

function same(given, secret) {
  const [left, right] = [new TextEncoder().encode(given || ""), new TextEncoder().encode(secret || "")];
  return right.byteLength > 0 && left.byteLength === right.byteLength && crypto.subtle.timingSafeEqual(left, right);
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname.slice(1);
    if (request.method === "POST" && path.startsWith("write/")) {
      const name = path.slice("write/".length);
      if (!NAMES.has(name)) return new Response(null, { status: 404 });
      if (!(same(request.headers.get("X-Live-Secret"), env.LIVE_SECRET))) return new Response(null, { status: 403 });
      const value = await request.text();
      try {
        JSON.parse(value);
      } catch {
        return new Response(null, { status: 400 });
      }
      await env.LIVE_DO.get(env.LIVE_DO.idFromName("live")).write(name, value);
      cached = null;
      return new Response(null, { status: 204 });
    }
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: HEADERS });
    if (request.method !== "GET") return new Response(null, { status: 405, headers: HEADERS });
    if (path !== "") return new Response(null, { status: 404, headers: HEADERS });
    const { body, etag } = await shared(env);
    const age = 60 - Math.floor((Date.now() % 60000) / 1000) + 5;
    const headers = { ...HEADERS, ETag: etag, "Cache-Control": `public, max-age=${age}` };
    if (request.headers.get("If-None-Match") === etag) return new Response(null, { status: 304, headers });
    return new Response(body, { headers: { ...headers, "Content-Type": "application/json" } });
  },
};
