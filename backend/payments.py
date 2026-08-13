import os
import secrets

import requests

WALLET_ID = os.environ.get("YOOMONEY_WALLET", "")
YOOMONEY_TOKEN = os.environ.get("YOOMONEY_TOKEN", "")
CRYPTOPAY_TOKEN = os.environ.get("CRYPTOPAY_TOKEN", "")
CRYPTOPAY_ASSET = os.environ.get("CRYPTOPAY_ASSET", "USDT")
CRYPTOPAY_FIAT = os.environ.get("CRYPTOPAY_FIAT", "RUB")

PRICE_RUB = float(os.environ.get("PRICE_RUB", "15"))
PAYMENT_MODE = os.environ.get("PAYMENT_MODE", "manual")


def build_payment_url(payment) -> str:
    """Возвращает URL, на который уводим пользователя для оплаты."""
    if PAYMENT_MODE == "yoomoney":
        return (
            f"https://yoomoney.ru/quick-pay-form"
            f"?receiver={WALLET_ID}"
            f"&quickpay-form=small"
            f"&targets={payment['comment']}"
            f"&sum={payment['amount']:.2f}"
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
