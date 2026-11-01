# Деплой и эксплуатация SubPing

## Архитектура

- **Фронт** — статика на GitHub Pages, `subping.ru` (CNAME → GitHub Pages).
- **Бэкенд** — FastAPI на Render Free: `https://subtrack-api-jszq.onrender.com` (SQLite/Postgres, Telegram-бот, планировщик, платежи).
- **Прокси для РФ** — Cloudflare Worker (`scripts/cf-worker.js`): `onrender.com` и `*.vercel.app` недоступны из РФ без VPN, сеть Cloudflare доступна. Worker проксирует запросы клиентов → Render.
- Бэкенд находится в США: `api.telegram.org` и `api.yookassa.ru` с него доступны (из РФ api.telegram.org заблокирован — **VPS в РФ не использовать**, умрут Telegram-напоминания).

## 1. Cloudflare Worker (прокси)

Вариант А — через дашборд (5 минут):
1. https://workers.cloudflare.com → **Create a Worker** → Deploy.
2. **Edit code** → вставить содержимое `scripts/cf-worker.js` → Deploy.
3. Скопировать URL вида `https://subping-api.<your-name>.workers.dev` и передать разработчику — он пропишет его в `frontend/app.html` (API_BASES) и опубликует.

Вариант Б — через API (если есть токен Cloudflare):
```bash
export CF_API_TOKEN=...   # токен с правами "Cloudflare Workers:Edit"
export CF_ACCOUNT_ID=...  # из обзора аккаунта в дашборде
# упаковать worker и задеплоить: проще через wrangler
npx wrangler deploy scripts/cf-worker.js --name subping-api --compatibility-date 2026-10-31
```

Проверка после деплоя:
```bash
curl -i https://<worker-url>/health        # ожидается {"ok":true} через ~2-5 c (cold start Render)
curl -i https://<worker-url>/api/me        # ожидается 401
```

## 2. Render (бэкенд)

Env-переменные (Dashboard → subtrack-api → Environment):

| Переменная | Значение |
|---|---|
| `PAYMENT_MODE` | `yookassa` |
| `YOOKASSA_SHOP_ID` | shopId из кабинета ЮKassa |
| `YOOKASSA_SECRET_KEY` | секретный ключ API ЮKassa |
| `YOOKASSA_VAT_CODE` | `1` (НДС не облагается, самозанятый) |
| `MYNALOG_INN` | ваш ИНН (772623564429) — чеки самозанятого |
| `MYNALOG_PASSWORD` | пароль из lknpd.nalog.ru (включается в профиле ФНС) |
| `MYNALOG_PAYMENT_TYPE` | `TRANSFER_OF_FUNDS` (безнал) |
| `FRONTEND_ORIGIN` | `https://subping.ru` |
| `TG_BOT_TOKEN` | токен бота (уже задан) |
| `OWNER_TG_CHAT_ID` | chat ID для уведомлений об оплатах |
| `OWNER_EMAIL` | email владельца (доступ к `/api/admin/payments`) |
| `DATABASE_URL` | БД (уже задана; пусто = SQLite) |

После изменения env — **Manual Deploy → Deploy latest commit** (переменные применяются при перезапуске).

## 3. ЮKassa (кабинет kassa.yandex.ru)

1. **Интеграция → Ключи API** — там shopId и секретный ключ; то же прописывается в env Render.
2. **Интеграция → Уведомления (webhooks)** — URL:
   `https://<worker-url>/api/payments/yookassa/notify`
   Событие: `payment.succeeded`. (Можно и напрямую на Render, но worker-URL работает и для РФ-контура.)
3. Return URL берётся из `FRONTEND_ORIGIN` — покупатель возвращается на `https://subping.ru/`.

## 4. Локальная проверка оплаты (без списаний)

```bash
cd backend
cp .env.example .env   # вписать реальные YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY
set -a && source .env && set +a
python test_yookassa.py            # юнит-флоу с моком API
# живая проверка ключей (только чтение, без платежей):
python - <<'PY'
import os, requests, base64
auth = base64.b64encode(f"{os.environ['YOOKASSA_SHOP_ID']}:{os.environ['YOOKASSA_SECRET_KEY']}".encode()).decode()
r = requests.get("https://api.yookassa.ru/v3/payments?limit=1", headers={"Authorization": "Basic " + auth}, timeout=20)
print("status:", r.status_code)  # 200 — ключи живы; 401/403 — ключи неверные/отключены
PY
```
Ключи никуда не коммитятся: `backend/.env` в `.gitignore`, в Render — через dashboard.

## 5. Проверка end-to-end после деплоя

1. Без VPN с телефона/ПК: открыть `https://subping.ru/app.html` → зарегистрироваться → «Подключить Premium» → выбрать тариф → открывается `yookassa.ru` (не Render).
2. Оплатить тестовой картой ЮKassa (`4111 1111 1111 1111`, любая дата/CVC) — в кабинете должен быть включён тестовый режим для тестовых карт.
3. Вернуться на сайт → «Проверить оплату» → Premium активен; уведомление приходит в Telegram владельцу и покупателю (если бот подключён).
