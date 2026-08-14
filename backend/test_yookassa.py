"""E2E-тест оплаты ЮKassa (самозанятый): создание платежа, receipt, вебхук, Premium.

API ЮKassa мокается (monkeypatch requests) — реальных денег не требуется.

Запуск (SQLite, без внешней БД):
    python test_yookassa.py
"""
import os
import random
import tempfile

os.environ["PAYMENT_MODE"] = "yookassa"
os.environ["YOOKASSA_SHOP_ID"] = "123456"
os.environ["YOOKASSA_SECRET_KEY"] = "test_secret_key"
os.environ["FRONTEND_ORIGIN"] = "https://gan4ik13.github.io"
if "DATABASE_URL" not in os.environ:
    os.environ["SUBTRAK_DB"] = os.path.join(tempfile.gettempdir(), "subtrack_test_yookassa.db")

import payments as pay
from db import db as db_ctx
from fastapi.testclient import TestClient
import main as app_module

client = TestClient(app_module.app)


class FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    @property
    def text(self):
        return str(self._payload)


_real_post = pay.requests.post
_real_get = pay.requests.get
CAPTURED_CREATE_BODY = {}
FAKE_EXTERNAL = "yk_2b18f3b4-0000-0000-0000-000000000001"


def fake_post(url, headers=None, json=None, timeout=None, **kw):
    if url == "https://api.yookassa.ru/v3/payments":
        CAPTURED_CREATE_BODY["body"] = json
        CAPTURED_CREATE_BODY["headers"] = headers or {}
        return FakeResp(201, {
            "id": FAKE_EXTERNAL,
            "status": "succeeded",
            "confirmation": {"confirmation_url": "https://yookassa.ru/pay/" + FAKE_EXTERNAL},
            "payment_method": {"type": "bank_card"},
            "amount": {"value": "15.00", "currency": "RUB"},
        })
    return _real_post(url, headers=headers, json=json, timeout=timeout, **kw)


def fake_get(url, headers=None, timeout=None, **kw):
    if url.endswith("/payments/" + FAKE_EXTERNAL):
        return FakeResp(200, {
            "id": FAKE_EXTERNAL,
            "status": "succeeded",
            "payment_method": {"type": "bank_card"},
            "amount": {"value": "15.00", "currency": "RUB"},
        })
    return _real_get(url, headers=headers, timeout=timeout, **kw)


pay.requests.post = fake_post
pay.requests.get = fake_get

# 1) build_payment_url возвращает confirmation_url и проставляет external_id
payment = {"id": "payyyyy", "comment": "subtrack-1-payyyyy", "amount": 15.0}
url = pay.build_payment_url(payment, base_url="http://testserver", customer_email="buyer@example.com")
print("pay_url:", url)
assert url == "https://yookassa.ru/pay/" + FAKE_EXTERNAL
assert payment["external_id"] == FAKE_EXTERNAL

body = CAPTURED_CREATE_BODY["body"]
assert body["amount"] == {"value": "15.00", "currency": "RUB"}
assert body["capture"] is True
assert body["confirmation"]["type"] == "redirect"
assert body["receipt"]["customer"]["email"] == "buyer@example.com"
assert body["receipt"]["items"][0]["description"] == "SubTrack Premium (1 месяц)"
assert body["receipt"]["items"][0]["vat_code"] == "1"
hdr = CAPTURED_CREATE_BODY["headers"]
assert hdr["Authorization"].startswith("Basic ")
assert hdr.get("Idempotency-Key")
print("create payment + receipt ok")

# 2) check_payment по external_id
assert pay.check_payment(payment) is True
payment_not_paid = {"id": "payzzzz", "comment": "x", "amount": 15.0, "external_id": "not_found"}
assert pay.check_payment(payment_not_paid) is False
print("check ok")

# 3) полный флоу: register -> create -> webhook -> premium
email = "ykpaytest%d@example.com" % random.randint(10000, 99999)
reg = client.post("/api/auth/register", json={"email": email, "password": "pass123"}).json()
token = reg["token"]
auth = {"Authorization": "Bearer " + token}

res = client.post("/api/payment/create", headers=auth, json={}).json()
assert res["pay_url"] == "https://yookassa.ru/pay/" + FAKE_EXTERNAL
pid = res["payment_id"]
print("payment created:", pid, "->", res["pay_url"])

r = client.post("/api/payments/yookassa/notify", json={
    "event": "payment.succeeded",
    "object": {
        "id": FAKE_EXTERNAL,
        "payment_method": {"type": "bank_card"},
        "amount": {"value": "15.00", "currency": "RUB"},
    },
})
print("webhook status:", r.status_code, r.json())
assert r.status_code == 200

me = client.get("/api/me", headers=auth).json()
assert me["premium"] is True
print("premium after webhook:", me["premium"])

st = client.get("/api/payment/status/" + pid, headers=auth).json()
assert st["premium"] is True
print("payment status:", st)

with db_ctx() as conn:
    row = conn.execute("SELECT operation_id, sender FROM payments WHERE id = ?", (pid,)).fetchone()
assert row["operation_id"] == FAKE_EXTERNAL
assert row["sender"] == "bank_card"
print("webhook meta stored ok")

# 4) нерелевантное событие не активирует premium
email2 = "ykpaytest%d@example.com" % random.randint(10000, 99999)
reg2 = client.post("/api/auth/register", json={"email": email2, "password": "pass123"}).json()
tok2 = {"Authorization": "Bearer " + reg2["token"]}
res2 = client.post("/api/payment/create", headers=tok2, json={}).json()
r = client.post("/api/payments/yookassa/notify", json={"event": "payment.canceled", "object": {"id": FAKE_EXTERNAL}})
assert r.status_code == 200
me2 = client.get("/api/me", headers=tok2).json()
assert me2["premium"] is False
print("irrelevant event ignored ok")

pay.requests.post = _real_post
pay.requests.get = _real_get

print("\nYOOKASSA TESTS PASSED")
