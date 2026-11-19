// invest-live — invest-reports 미니 앱에 실시간 값(프리장·정규장 값, 애프터장 값, 판단 배치 진척률)을 건네는 Cloudflare Worker.
//
// claude-svr의 build.py `--premarket`·`--afterhours`·`--progress`가 KV(LIVE)의 `premarket`·`afterhours`·`progress` 키에 값을 쓰고,
// 미니 앱은 `GET /{키}`로 받는다. 값은 공개 리포트가 그리는 체결가와 진척 단계라 누구에게나 돌려준다. 키에 값이 없으면 404다.

const NAMES = new Set(["premarket", "afterhours", "progress"]);

export default {
  async fetch(request, env) {
    const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET", "Cache-Control": "no-cache" };
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (request.method !== "GET") return new Response(null, { status: 405, headers });
    const name = new URL(request.url).pathname.slice(1);
    const value = NAMES.has(name) && (await env.LIVE.get(name));
    if (!value) return new Response(null, { status: 404, headers });
    return new Response(value, { headers: { ...headers, "Content-Type": "application/json" } });
  },
};
