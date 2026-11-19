#!/bin/bash
# deploy.sh — invest-live Worker(live.js)를 Cloudflare에 올린다.
# Cloudflare API 토큰·계정 ID와 실시간 값 KV namespace ID(CLOUDFLARE_LIVE_NAMESPACE), 쓰기 비밀 값(LIVE_SECRET)은 ~/.cloudflare_env에서 읽는다.
# SQLite Durable Object `Live`는 첫 배포의 이전 단계(migration `v1`)가 만들고, 그 뒤 배포는 이전 단계 없이 올린다.
set -euo pipefail
source "$HOME/.cloudflare_env"
NAME="invest-live"
SCRIPTS="https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts"
API="$SCRIPTS/$NAME"
MIGRATION="v1"
cd "$(dirname "$0")"

# 토큰은 헤더 파일로, 비밀 값은 0600 임시 파일로 넘겨 curl 명령줄에 남기지 않는다.
cf() { curl -s -H @<(printf 'Authorization: Bearer %s\n' "$CLOUDFLARE_API_TOKEN") "$@"; }
check() {
    local answer; answer=$(cat)
    jq -e '.success' <<< "$answer" > /dev/null 2>&1 || { echo "deploy.sh: $1 실패 $(jq -c '.errors' <<< "$answer" 2>/dev/null)" >&2; exit 1; }
}

tag=$(cf "$SCRIPTS" | jq -r --arg name "$NAME" '.result[] | select(.id == $name) | .migration_tag // ""')
umask 077
metadata=$(mktemp)
trap 'rm -f "$metadata"' EXIT
jq -nc --arg ns "$CLOUDFLARE_LIVE_NAMESPACE" --arg secret "$LIVE_SECRET" --arg tag "$tag" --arg migration "$MIGRATION" \
    '{main_module: "live.js", compatibility_date: "2026-11-01",
      bindings: [{type: "kv_namespace", name: "LIVE", namespace_id: $ns},
                 {type: "durable_object_namespace", name: "LIVE_DO", class_name: "Live"},
                 {type: "secret_text", name: "LIVE_SECRET", text: $secret}]}
     + (if $tag == $migration then {} else {migrations: {new_tag: $migration, new_sqlite_classes: ["Live"]}} end)' > "$metadata"
cf -X PUT "$API" -F "metadata=<$metadata;type=application/json" \
    -F "live.js=@live.js;type=application/javascript+module" | check "Worker 올리기"
cf -X POST "$API/subdomain" -H "Content-Type: application/json" --data '{"enabled":true}' | check "workers.dev 주소 열기"
echo "deployed https://$NAME.wonwooshik.workers.dev"
