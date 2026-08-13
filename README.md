# SubTrack — трекер подписок

Простой сайт для отслеживания подписок. Бесплатно до 3 подписок, Premium (безлимит + Telegram-уведомления о списаниях) — 15 ₽/мес.

## Архитектура

- `frontend/index.html` — статический сайт (один файл, без сборки). Размещается на GitHub Pages.
- `backend/` — API на FastAPI. Размещается на Render.
  - Авторизация (email + пароль, PBKDF2, токены-сессии)
  - CRUD подписок, лимит 3 для бесплатного тарифа
  - Платежи: ЮMoney (личный кошелёк, без ИНН), Crypto Pay или ручной режим
  - Telegram-уведомления о списаниях за 3 дня
  - Экспорт данных в JSON
  - БД: PostgreSQL (`DATABASE_URL`), локально по умолчанию SQLite

## Запуск локально

```bash
# Бэкенд
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn main:app --port 8000

# Фронтенд (в другом терминале)
cd frontend
python -m http.server 8080
```

Открыть http://localhost:8080 — фронтенд сам найдёт API на localhost:8000.

## Переменные окружения бэкенда

| Переменная | Значение по умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | — | Строка подключения к PostgreSQL (обязательна на сервере). Локально без неё — SQLite |
| `PAYMENT_MODE` | `manual` | `manual` \| `yoomoney` \| `cryptopay` |
| `PRICE_RUB` | `15` | Цена Premium за месяц |
| `YOOMONEY_WALLET` | — | Номер кошелька ЮMoney (для yoomoney-режима) |
| `YOOMONEY_TOKEN` | — | Токен ЮMoney (автопроверка оплаты, без него проверка вручную) |
| `YOOMONEY_NOTIFY_SECRET` | — | Пароль уведомлений ЮMoney (для проверки подписи вебхука) |
| `CRYPTOPAY_TOKEN` | — | Токен Crypto Pay (для cryptopay-режима) |
| `TG_BOT_TOKEN` | — | Токен Telegram-бота для уведомлений |
| `FRONTEND_ORIGIN` | `http://localhost:8080,...` | Домены фронтенда через запятую (CORS) |

## База данных: Neon (бесплатно, данные не пропадают)

Бесплатная БД Render удаляется через 30 дней, поэтому используется Neon:

1. Зарегистрируйтесь на https://neon.tech (работает вход через GitHub).
2. Create Project → Database name: `subtrack`, регион `Frankfurt (eu-central-1)`.
3. Скопируйте **connection string** вида `postgresql://user:password@ep-....eu-central-1.aws.neon.tech/subtrack?sslmode=require` (замените `<password>` на настоящий пароль).
4. Вставьте её в `DATABASE_URL` на Render.

Схема создаётся автоматически при первом запуске API.

## Режимы оплаты

- **`manual`** — платежей нет, Premium активирует владелец после перевода. Для запуска/теста.
- **`yoomoney`** — форма оплаты ЮMoney (личный кошелёк, регистрация ИНН не нужна).
  - `YOOMONEY_WALLET` — ваш номер кошелька, на который придёт перевод.
  - `YOOMONEY_TOKEN` — токен API кошелька с доступом к истории операций: тогда оплата подтверждается автоматически (поллингом из фронтенда). Без токена пользователь нажимает «Я оплатил» и проверку делает владелец.
  - `YOOMONEY_NOTIFY_SECRET` — пароль уведомлений. Настройка в ЮMoney: Кошелёк → **Настройки → Уведомления → HTTP-уведомления** → включить, ввести URL вебхука `https://<ваш-API>.onrender.com/api/payments/yoomoney/notify` и установить пароль. Этот же пароль впишите в `YOOMONEY_NOTIFY_SECRET` на Render. Тогда Premium активируется мгновенно по вебхуку.
- **`cryptopay`** — приём в крипте через Crypto Pay (Send). Полностью автоматический. Ключ даёт @CryptoBot / @sendpayoutbot.

## Деплой

### Бэкенд → Render
1. Запушьте репозиторий на GitHub.
2. В Render Dashboard → **New → Blueprint** → выберите этот репозиторий. `backend/render.yaml` создаст сервис.
3. В настройках сервиса задайте переменные (обязательные): `DATABASE_URL` (из Neon), `TG_BOT_TOKEN`, `FRONTEND_ORIGIN` = адрес вашего GitHub Pages, при желании `PAYMENT_MODE`, `YOOMONEY_WALLET`, `YOOMONEY_TOKEN`.
4. Проверьте `/health` — должен вернуть `{"ok": true}`.

### Фронтенд → GitHub Pages
1. GitHub → репозиторий → **Settings → Pages**.
2. Source: **Deploy from a branch**, ветка `main`, папка `/frontend`.
3. Сайт будет на `https://<username>.github.io/subtrack/`.
4. Этот адрес впишите в `FRONTEND_ORIGIN` на Render, иначе браузер заблокирует запросы (CORS).

### Telegram-уведомления
1. Создайте бота через @BotFather, получите токен → `TG_BOT_TOKEN`.
2. Пользователь в настройках сайта указывает свой числовой ID (узнаёт у @userinfobot) и должен открыть чат с вашим ботом (нажать /start), иначе бот не сможет ему писать.
3. Планировщик проверяет подписки раз в час и шлёт напоминание за 3 дня до списания (только Premium).
