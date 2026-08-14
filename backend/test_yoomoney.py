"""E2E-тест оплаты ЮMoney: форма, подпись, вебхук, активация Premium.

Запуск (SQLite, без внешней БД):
    python test_yoomoney.py
"""
import hashlib
import os
import random
import tempfile

os.environ["PAYMENT_MODE"] = "yoomoney"
os.environ["YOOMONEY_WALLET"] = "4100112345678901"
os.environ["YOOMONEY_NOTIFY_SECRET"] = "secret123"
os.environ["FRONTEND_ORIGIN"] = "https://gan4ik13.github.io"
if "DATABASE_URL" not in os.environ:
    os.environ["SUBTRAK_DB"] = os.path.join(tempfile.gettempdir(), f"subtrack_test_yoomoney_{os.getpid()}.db")

import payments as pay
from db import db as db_ctx
from fastapi.testclient import TestClient
import main as app_module

client = TestClient(app_module.app)


def yoomoney_sign(params: dict) -> str:
    """Подпись как у ЮMoney: sha1 значений полей через '&', без URL-кодирования."""
    raw = "&".join(
        [
            params["notification_type"],
            params["operation_id"],
            params["amount"],
            params["currency"],
            params["datetime"],
            params["sender"],
            params["codepro"],
            os.environ["YOOMONEY_NOTIFY_SECRET"],
            params["label"],
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def payment_comment(pid):
    with db_ctx() as conn:
        return conn.execute("SELECT comment FROM payments WHERE id = ?", (pid,)).fetchone()["comment"]


# 1) build_payment_url -> внутренняя страница с POST-формой на quickpay/confirm
payment = {"id": "pay123456", "comment": "subtrack-1-pay123456", "amount": 15.0}
url = pay.build_payment_url(payment, base_url="http://testserver")
print("pay_url:", url)
assert url == "http://testserver/api/payment/pay/pay123456"
html = pay.build_payment_form_html(payment)
assert "https://yoomoney.ru/quickpay/confirm" in html
assert 'method="GET"' in html
assert 'name="receiver" value="4100112345678901"' in html
assert 'name="quickpay-form" value="button"' in html
assert 'name="paymentType" value="PC"' in html
assert 'name="sum" value="15.00"' in html
assert 'name="label" value="subtrack-1-pay123456"' in html
print("pay form ok")

# 2) verify_notification (реальный формат ЮMoney)
p = {
    "notification_type": "p2p-incoming",
    "operation_id": "904035776918098009",
    "amount": "15.00",
    "withdraw_amount": "15.00",
    "currency": "643",
    "datetime": "2026-08-13T10:00:00+03:00",
    "sender": "41003188981230",
    "codepro": "false",
    "label": "subtrack-1-pay123456",
    "unaccepted": "false",
}
p["sha1_hash"] = yoomoney_sign(p)
print("signature valid:", pay.verify_notification(dict(p)))
assert pay.verify_notification(dict(p))
p_bad = dict(p)
p_bad["amount"] = "999.00"
assert not pay.verify_notification(p_bad)
assert not pay.verify_notification({"label": "x"})  # нет sha1_hash
print("signature checks ok")

# 3) полный флоу: register -> create -> webhook -> premium
email = "paytest%d@example.com" % random.randint(10000, 99999)
reg = client.post("/api/auth/register", json={"email": email, "password": "pass123"}).json()
token = reg["token"]
auth = {"Authorization": "Bearer " + token}

res = client.post("/api/payment/create", headers=auth, json={}).json()
assert res["pay_url"] is not None
pid = res["payment_id"]
comment = payment_comment(pid)
print("payment created:", pid, comment)
print("pay_url:", res["pay_url"])

# страница оплаты открывается и содержит POST-форму с label этого платежа
page = client.get(res["pay_url"])
print("pay page status:", page.status_code)
assert page.status_code == 200
assert "https://yoomoney.ru/quickpay/confirm" in page.text
assert 'name="quickpay-form" value="button"' in page.text
assert 'name="label" value="' + comment + '"' in page.text

notify = dict(p)
notify["label"] = comment
notify["sha1_hash"] = yoomoney_sign(notify)
r = client.post("/api/payments/yoomoney/notify", data=notify)
print("webhook status:", r.status_code, r.json())
assert r.status_code == 200

me = client.get("/api/me", headers=auth).json()
print("premium after webhook:", me["premium"])
assert me["premium"] is True

st = client.get("/api/payment/status/" + pid, headers=auth).json()
print("payment status:", st)
assert st["premium"] is True

# 4) неверная подпись отклоняется
bad = dict(notify)
bad["sha1_hash"] = "0" * 40
r = client.post("/api/payments/yoomoney/notify", data=bad)
assert r.status_code == 403
print("bad signature rejected ok")

# 5) уведомление не про p2p-incoming не активирует премиум
email2 = "paytest%d@example.com" % random.randint(10000, 99999)
reg2 = client.post("/api/auth/register", json={"email": email2, "password": "pass123"}).json()
tok2 = {"Authorization": "Bearer " + reg2["token"]}
res2 = client.post("/api/payment/create", headers=tok2, json={}).json()
t = dict(notify)
t["label"] = payment_comment(res2["payment_id"])
t["notification_type"] = "p2p-other"
t["sha1_hash"] = yoomoney_sign(t)
r = client.post("/api/payments/yoomoney/notify", data=t)
assert r.status_code == 200
me2 = client.get("/api/me", headers=tok2).json()
assert me2["premium"] is False
print("non-p2p notification ignored ok")

print("\nYOOMONEY TESTS PASSED")
