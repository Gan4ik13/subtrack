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


def build_payment_url(payment, base_url: str = "") -> str:
    """Возвращает URL, на который уводим пользователя для оплаты."""
    if PAYMENT_MODE == "yoomoney":
        # Открываем внутреннюю страницу с POST-формой на yoomoney.ru/quickpay/confirm
        # (старый GET-линк quick-pay-form?quickpay-form=small удалён ЮMoney).
        return f"{base_url.rstrip('/')}/api/payment/pay/{payment['id']}"
    if PAYMENT_MODE == "cryptopay":
        invoice = _cryptopay_create_invoice(payment)
        payment["external_id"] = invoice["invoice_id"]
        return invoice["pay_url"]
    # manual mode: no real gateway
    return None


def build_payment_form_html(payment) -> str:
    """HTML-страница с формой перевода на кошелёк ЮMoney.

    По актуальным правилам ЮMoney форма отправляется POST-ом на
    https://yoomoney.ru/quickpay/confirm с полем quickpay-form=button.
    """
    label = payment["comment"][:64]
    amount = f"{payment['amount']:.2f}"
    success = os.environ.get("FRONTEND_ORIGIN", "https://gan4ik13.github.io").split(",")[0].strip()
    success = success.rstrip("/") + "/"

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")

    def hidden(name: str, value: str) -> str:
        return f'<input type="hidden" name="{name}" value="{esc(value)}"/>'

    fields = [
        ("receiver", WALLET_ID),
        ("quickpay-form", "button"),
        ("paymentType", "PC"),
        ("sum", amount),
        ("label", label),
        ("successURL", success),
    ]
    inputs = "".join(hidden(n, v) for n, v in fields)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Оплата подписки</title>
<style>
  body {{ margin:0; display:flex; align-items:center; justify-content:center;
        min-height:100vh; background:#0b1020; color:#e5e7eb;
        font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }}
  .card {{ background:#141a2e; border:1px solid #2a3352; border-radius:16px;
        padding:32px; max-width:360px; width:calc(100% - 32px); text-align:center; }}
  h1 {{ font-size:18px; margin:0 0 8px; }}
  p {{ font-size:13px; color:#9ca3af; margin:0 0 20px; }}
  .price {{ font-size:28px; font-weight:700; color:#818cf8; margin-bottom:20px; }}
  form button {{ width:100%; background:#818cf8; border:0; border-radius:10px;
        color:#fff; font-size:15px; font-weight:600; padding:13px; cursor:pointer; }}
  form button:hover {{ background:#6d7bf7; }}
</style>
</head>
<body>
  <div class="card">
    <h1>Оплата подписки SubTrack</h1>
    <div class="price">{amount} &#8381;</div>
    <p>Сейчас вы перейдёте на страницу ЮMoney для подтверждения перевода.</p>
    <form id="payform" method="POST" action="https://yoomoney.ru/quickpay/confirm">
      {inputs}
      <button type="submit">Перейти к оплате</button>
    </form>
  </div>
  <script>
    document.addEventListener('DOMContentLoaded', function () {{
      document.getElementById('payform').submit();
    }});
  </script>
</body>
</html>"""


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
