import hashlib
import hmac
import os
import secrets
import urllib.parse

import requests

WALLET_ID = os.environ.get("YOOMONEY_WALLET", "")
YOOMONEY_TOKEN = os.environ.get("YOOMONEY_TOKEN", "")
YOOMONEY_NOTIFY_SECRET = os.environ.get("YOOMONEY_NOTIFY_SECRET", "")
CRYPTOPAY_TOKEN = os.environ.get("CRYPTOPAY_TOKEN", "")
CRYPTOPAY_ASSET = os.environ.get("CRYPTOPAY_ASSET", "USDT")
CRYPTOPAY_FIAT = os.environ.get("CRYPTOPAY_FIAT", "RUB")

PRICE_RUB = float(os.environ.get("PRICE_RUB", "15"))
PAYMENT_MODE = os.environ.get("PAYMENT_MODE", "manual")


def build_payment_url(payment) -> str:
    """Возвращает URL, на который уводим пользователя для оплаты."""
    if PAYMENT_MODE == "yoomoney":
        success = os.environ.get("FRONTEND_ORIGIN", "https://gan4ik13.github.io").split(",")[0].strip()
        label = payment["comment"][:64]
        return (
            f"https://yoomoney.ru/quick-pay-form"
            f"?receiver={urllib.parse.quote(WALLET_ID)}"
            f"&quickpay-form=small"
            f"&targets={urllib.parse.quote(payment['comment'])}"
            f"&sum={payment['amount']:.2f}"
            f"&label={urllib.parse.quote(label)}"
            f"&successURL={urllib.parse.quote(success.rstrip('/') + '/', safe='')}"
            f"&need-fio=false&need-email=false&need-phone=false&need-address=false"
        )
    if PAYMENT_MODE == "cryptopay":
        invoice = _cryptopay_create_invoice(payment)
        payment["external_id"] = invoice["invoice_id"]
        return invoice["pay_url"]
    # manual mode: no real gateway
    return None


def _cryptopay_create_invoice(payment):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOPAY_TOKEN, "Content-Type": "application/json"}
    payload = {
        "asset": CRYPTOPAY_ASSET,
        "amount": payment["amount"],
        "currency_type": "fiat",
        "fiat": CRYPTOPAY_FIAT,
        "description": payment["comment"],
        "paid_btn_name": "openButton",
        "paid_btn_url": os.environ.get("FRONTEND_ORIGIN", "https://subtrack.github.io"),
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"CryptoPay error: {data}")
    return data["result"]


def check_payment(payment) -> bool:
    """Проверяет, оплачен ли платёж. Возвращает True если оплачен."""
    if PAYMENT_MODE == "yoomoney":
        return _yoomoney_check(payment)
    if PAYMENT_MODE == "cryptopay":
        return _cryptopay_check(payment)
    return False


def verify_notification(params: dict) -> bool:
    """Проверяет подпись HTTP-уведомления ЮMoney.

    ЮMoney шлёт form-encoded POST с полем sha1_hash:
      sha1_hash = sha1(notification_type&operation_id&amount&currency&datetime
                       &sender&codepro&notification_secret&label)
    Значения берутся как есть (без URL-кодирования), склеиваются через '&'.
    """
    secret = YOOMONEY_NOTIFY_SECRET
    if not secret:
        return False
    sign = (params.get("sha1_hash") or "").lower()
    if not sign:
        return False
    raw = "&".join(
        [
            params.get("notification_type", ""),
            params.get("operation_id", ""),
            params.get("amount", ""),
            params.get("currency", ""),
            params.get("datetime", ""),
            params.get("sender", ""),
            params.get("codepro", ""),
            secret,
            params.get("label", ""),
        ]
    )
    expected = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, sign)


def _yoomoney_check(payment) -> bool:
    # Требуется токен личного кошелька ЮMoney с доступом к истории операций.
    # Ищем операцию по уникальному комментарию (label) и сумме.
    if not YOOMONEY_TOKEN:
        return False
    resp = requests.post(
        "https://yoomoney.ru/api/operation-history",
        headers={"Authorization": f"Bearer {YOOMONEY_TOKEN}"},
        data={
            "type": "deposition",
            "label": payment["comment"],
            "records": 50,
            "details": "true",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        return False
    data = resp.json()
    for op in data.get("operations", []):
        if (
            op.get("status") == "success"
            and op.get("label") == payment["comment"]
            and abs(op.get("amount", 0) - payment["amount"]) < 0.01
        ):
            return True
    return False


def _cryptopay_check(payment) -> bool:
    if not payment.get("external_id"):
        return False
    resp = requests.post(
        "https://pay.crypt.bot/api/getInvoices",
        headers={"Crypto-Pay-API-Token": CRYPTOPAY_TOKEN, "Content-Type": "application/json"},
        json={"invoice_ids": [payment["external_id"]]},
        timeout=30,
    )
    data = resp.json()
    if not data.get("ok"):
        return False
    for inv in data.get("result", []):
        if inv.get("status") == "paid":
            return True
    return False


def new_payment_id() -> str:
    return "pay_" + secrets.token_hex(6)
