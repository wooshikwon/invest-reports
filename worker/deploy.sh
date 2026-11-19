#!/bin/bash
# deploy.sh — invest-live Worker(live.js)를 Cloudflare에 올린다.
# Cloudflare API 토큰·계정 ID와 실시간 값 KV namespace ID(CLOUDFLARE_LIVE_NAMESPACE)는 ~/.cloudflare_env에서 읽는다.
set -euo pipefail
source "$HOME/.cloudflare_env"
NAME="invest-live"
API="https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts/$NAME"
cd "$(dirname "$0")"

# 토큰은 헤더 파일로 넘겨 curl 명령줄에 남기지 않는다.
cf() { curl -s -H @<(printf 'Authorization: Bearer %s\n' "$CLOUDFLARE_API_TOKEN") "$@"; }
check() {
    local answer; answer=$(cat)
    jq -e '.success' <<< "$answer" > /dev/null 2>&1 || { echo "deploy.sh: $1 실패 $(jq -c '.errors' <<< "$answer" 2>/dev/null)" >&2; exit 1; }
}

metadata=$(jq -nc --arg ns "$CLOUDFLARE_LIVE_NAMESPACE" \
    '{main_module: "live.js", compatibility_date: "2026-11-01",
      bindings: [{type: "kv_namespace", name: "LIVE", namespace_id: $ns}]}')
cf -X PUT "$API" -F "metadata=$metadata;type=application/json" \
    -F "live.js=@live.js;type=application/javascript+module" | check "Worker 올리기"
cf -X POST "$API/subdomain" -H "Content-Type: application/json" --data '{"enabled":true}' | check "workers.dev 주소 열기"
echo "deployed https://$NAME.wonwooshik.workers.dev"
