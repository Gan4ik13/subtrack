#!/usr/bin/env bash
# Деплой Netlify-прокси одной командой:
#   export NETLIFY_TOKEN=nfp_...   (User settings → Applications → New access token)
#   bash scripts/netlify-proxy/deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

TOKEN="${NETLIFY_TOKEN:?Задайте NETLIFY_TOKEN (User settings → Applications → New access token)}"
SITE_NAME="${SITE_NAME:-subping-proxy}"
API="https://api.netlify.com/api/v1"

echo "== сайт =="
RESP=$(curl -s -X POST "$API/sites" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d "{\"name\":\"$SITE_NAME\"}")
SITE_ID=$(echo "$RESP" | python -c "import sys,json;d=json.load(sys.stdin);print(d.get('id') or '')" 2>/dev/null || true)
if [ -z "$SITE_ID" ]; then
  SITE_ID=$(curl -s "$API/sites?name=$SITE_NAME" -H "Authorization: Bearer $TOKEN" \
    | python -c "import sys,json;d=json.load(sys.stdin);print(d[0]['id'] if d else '')")
fi
[ -n "$SITE_ID" ] || { echo "Не удалось создать или найти сайт '$SITE_NAME'"; exit 1; }
URL=$(curl -s "$API/sites/$SITE_ID" -H "Authorization: Bearer $TOKEN" \
  | python -c "import sys,json;print(json.load(sys.stdin)['url'])")
echo "site: $SITE_ID -> $URL"

echo "== упаковка =="
ZIP_PATH="${TEMP:-/tmp}/subping-proxy-deploy.zip"
rm -f "$ZIP_PATH"
python - "$ZIP_PATH" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1], 'w', zipfile.ZIP_DEFLATED) as z:
    z.write('netlify.toml')
    z.write('netlify/functions/proxy.js')
print('zip ok:', sys.argv[1])
PY

echo "== деплой =="
DEPLOY=$(curl -s -X POST "$API/sites/$SITE_ID/deploys" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/zip" --data-binary "@$ZIP_PATH")
DEPLOY_ID=$(echo "$DEPLOY" | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
for i in $(seq 1 30); do
  STATE=$(curl -s "$API/deploys/$DEPLOY_ID" -H "Authorization: Bearer $TOKEN" \
    | python -c "import sys,json;print(json.load(sys.stdin)['state'])")
  echo "  deploy $DEPLOY_ID: $STATE"
  [ "$STATE" = "ready" ] && break
  [ "$STATE" = "error" ] && { echo "Ошибка деплоя"; exit 1; }
  sleep 3
done

echo ""
echo "=============================================="
echo "PROXY_URL=$URL"
echo "=============================================="
echo "Проверка:"
echo "  curl -s $URL/health   (ожидается {\"ok\": true}, первый запрос — прогрев Render до ~60 с)"
