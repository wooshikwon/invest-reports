#!/bin/bash
# deploy.sh — invest-reports 미니 앱의 Worker 하나를 Cloudflare에 올린다. `deploy.sh live`는 invest-live(live.js)를, `deploy.sh news`는 invest-news(news.js)를 올린다.
# Cloudflare API 토큰·계정 ID와 Worker의 쓰기 비밀 값(invest-live는 LIVE_SECRET, invest-news는 NEWS_SECRET)은 ~/.cloudflare_env에서 읽는다.
# SQLite Durable Object 클래스(invest-live는 `Live`, invest-news는 `News`·`Images`)는 첫 배포의 이전 단계(migration `v1`)가 만들고, 그 뒤 배포는 이전 단계 없이 올린다.
set -euo pipefail
case "${1:-}" in
    live) NAME="invest-live"; MODULE="live.js"; SECRET="LIVE_SECRET"
          OBJECTS='[{"name": "LIVE_DO", "class_name": "Live"}]' ;;
    news) NAME="invest-news"; MODULE="news.js"; SECRET="NEWS_SECRET"
          OBJECTS='[{"name": "NEWS_DO", "class_name": "News"}, {"name": "IMAGES_DO", "class_name": "Images"}]' ;;
    *) echo "사용법: deploy.sh {live|news}" >&2; exit 2 ;;
esac
source "$HOME/.cloudflare_env"
[[ -n "${!SECRET:-}" ]] || { echo "deploy.sh: ~/.cloudflare_env에 $SECRET이 없다" >&2; exit 1; }
SCRIPTS="https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts"
API="$SCRIPTS/$NAME"
MIGRATION="v1"
cd "$(dirname "$0")"

# 토큰은 헤더 파일로, 비밀 값은 환경 변수로 jq에 넘긴 뒤 0600 임시 파일로 curl에 넘겨 명령줄에 남기지 않는다.
cf() { curl -s -H @<(printf 'Authorization: Bearer %s\n' "$CLOUDFLARE_API_TOKEN") "$@"; }
check() {
    local answer; answer=$(cat)
    jq -e '.success' <<< "$answer" > /dev/null 2>&1 || { echo "deploy.sh: $1 실패 $(jq -c '.errors' <<< "$answer" 2>/dev/null)" >&2; exit 1; }
}

tag=$(cf "$SCRIPTS" | jq -r --arg name "$NAME" '.result[] | select(.id == $name) | .migration_tag // ""')
umask 077
metadata=$(mktemp)
trap 'rm -f "$metadata"' EXIT
VALUE="${!SECRET}" jq -nc --arg module "$MODULE" --arg secret "$SECRET" --argjson objects "$OBJECTS" --arg tag "$tag" --arg migration "$MIGRATION" \
    '{main_module: $module, compatibility_date: "2026-11-01",
      bindings: ([$objects[] | {type: "durable_object_namespace"} + .] + [{type: "secret_text", name: $secret, text: env.VALUE}])}
     + (if $tag == $migration then {} else {migrations: {new_tag: $migration, new_sqlite_classes: [$objects[].class_name]}} end)' > "$metadata"
cf -X PUT "$API" -F "metadata=<$metadata;type=application/json" \
    -F "$MODULE=@$MODULE;type=application/javascript+module" | check "Worker 올리기"
cf -X POST "$API/subdomain" -H "Content-Type: application/json" --data '{"enabled":true}' | check "workers.dev 주소 열기"
echo "deployed https://$NAME.wonwooshik.workers.dev"
