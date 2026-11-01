"""Регистрация чеков самозанятого в «Мой налог» через API lknpd.nalog.ru.

Зачем: ЮKassa с 29.12.2025 прекратила сервисы для самозанятых, включая чеки
по платежам (официальный ченджлог developers/using-api/changelog): блок receipt
в платеже по-прежнему принимается, но игнорируется — чек не формируется.

Авторизация — по ИНН и паролю личного кабинета ФНС (lknpd.nalog.ru).
Чек создаётся один раз на каждый успешный платёж; ссылка на чек уходит
покупателю (Telegram) и владельцу (уведомление об оплате).
"""

import datetime
import os

import requests

MYNALOG_INN = os.environ.get("MYNALOG_INN", "").strip()
MYNALOG_PASSWORD = os.environ.get("MYNALOG_PASSWORD", "")
MYNALOG_PAYMENT_TYPE = os.environ.get("MYNALOG_PAYMENT_TYPE", "TRANSFER_OF_FUNDS")

AUTH_URL = "https://lknpd.nalog.ru/api/v1/auth/lkfl"
INCOME_URL = "https://lknpd.nalog.ru/api/v1/income"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


class MyNalogError(RuntimeError):
    pass


def configured() -> bool:
    return bool(MYNALOG_INN and MYNALOG_PASSWORD)


def _auth() -> str:
    r = requests.post(
        AUTH_URL,
        json={"username": MYNALOG_INN, "password": MYNALOG_PASSWORD},
        headers={"User-Agent": UA},
        timeout=30,
    )
    if r.status_code != 200:
        raise MyNalogError(f"auth HTTP {r.status_code}: {r.text[:200]}")
    token = (r.json() or {}).get("token")
    if not token:
        raise MyNalogError("auth: в ответе нет токена")
    return token


def create_income_receipt(*, name: str, amount: float, customer_email: str = "", quantity: int = 1) -> dict:
    """Регистрирует доход (чек). Возвращает dict чека (approvedReceiptUuid, url и т.д.)."""
    if not configured():
        raise MyNalogError("MYNALOG_INN / MYNALOG_PASSWORD не заданы")
    token = _auth()
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    payload = {
        "paymentType": MYNALOG_PAYMENT_TYPE,
        "ignoreMaxTotalIncomeRestriction": False,
        "requestTime": now.isoformat(),
        "operationTime": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "services": [
            {
                "name": (name or "Услуга")[:128],
                "amount": round(float(amount), 2),
                "quantity": quantity,
            }
        ],
        "totalAmount": round(float(amount), 2),
        "client": {
            "displayName": (customer_email or "Покупатель")[:128],
            "incomeType": "FROM_INDIVIDUAL",
        },
        "incomeType": "FROM_INDIVIDUAL",
    }
    r = requests.post(
        INCOME_URL,
        json=payload,
        headers={"Authorization": "Bearer " + token, "User-Agent": UA},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise MyNalogError(f"income HTTP {r.status_code}: {r.text[:300]}")
    data = (r.json() or {}).get("data") or {}
    if not data.get("approvedReceiptUuid"):
        raise MyNalogError("income: чек не подтверждён: " + r.text[:300])
    return data
