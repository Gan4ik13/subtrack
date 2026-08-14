import os
import sys

if "DATABASE_URL" in os.environ:
    import db
    db.init_db()

os.environ.setdefault("OWNER_EMAIL", "pgtest@example.com")

from fastapi.testclient import TestClient
import main as app_module

client = TestClient(app_module.app)


def call(method, path, body=None, token=None, expect=200):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    resp = client.request(method, path, json=body, headers=headers)
    assert resp.status_code == expect, f"{method} {path}: status {resp.status_code} != {expect}, body={resp.text}"
    try:
        return resp.json()
    except Exception:
        return {}


print("health:", call("GET", "/health"))

t1 = call("POST", "/api/auth/register", {"email": "pgtest@example.com", "password": "pass123"})
token = t1["token"]
print("register ok")

call("POST", "/api/auth/register", {"email": "pgtest@example.com", "password": "pass123"})
print("duplicate register logs in ok")
call("POST", "/api/auth/register", {"email": "pgtest@example.com", "password": "different"}, expect=409)
print("wrong-password register rejected ok")

call("POST", "/api/auth/login", {"email": "pgtest@example.com", "password": "wrong"}, expect=401)
print("bad login rejected ok")

t2 = call("POST", "/api/auth/login", {"email": "pgtest@example.com", "password": "pass123"})
token2 = t2["token"]
print("login ok")

me = call("GET", "/api/me", token=token)
assert me["premium"] is False and me["subscriptions"] == []
assert me["is_owner"] is True
call("PUT", "/api/settings/reminder", {"reminder_days": 7}, token=token, expect=403)
print("me ok")

call("GET", "/api/admin/payments", token=token, expect=200)
print("owner payments ok")

t3 = call("POST", "/api/auth/register", {"email": "other@example.com", "password": "pass123"})
tok3 = t3["token"]
me3 = call("GET", "/api/me", token=tok3)
assert me3["is_owner"] is False
call("GET", "/api/admin/payments", token=tok3, expect=403)
print("non-owner blocked ok")

s1 = call("POST", "/api/subscriptions", {"name": "Netflix", "amount": 599, "currency": "RUB", "period": "monthly", "category": "Развлечения", "next_date": "2026-08-16"}, token=token)
print("sub created:", s1)
call("POST", "/api/subscriptions", {"name": "A", "amount": 1, "period": "monthly", "next_date": "2026-09-01"}, token=token)
call("POST", "/api/subscriptions", {"name": "B", "amount": 1, "period": "monthly", "next_date": "2026-09-01"}, token=token)
call("POST", "/api/subscriptions", {"name": "C", "amount": 1, "period": "monthly", "next_date": "2026-09-01"}, token=token, expect=403)
print("free limit enforced ok")

call("PUT", f"/api/subscriptions/{s1['id']}", {"name": "Netflix HD", "amount": 699, "currency": "RUB", "period": "monthly", "category": "Развлечения", "next_date": "2026-08-20"}, token=token)
me = call("GET", "/api/me", token=token)
assert me["subscriptions"][0]["amount"] == 699
print("update ok")

p = call("POST", "/api/payment/create", token=token)
print("payment created:", p)
call("GET", f"/api/payment/status/{p['payment_id']}", token=token)
call("POST", f"/api/payment/{p['payment_id']}/confirm", token=token)
me = call("GET", "/api/me", token=token)
assert me["premium"] is True
call("POST", "/api/subscriptions", {"name": "D", "amount": 1, "period": "monthly", "next_date": "2026-09-01"}, token=token)
admin = call("GET", "/api/admin/payments", token=token)
assert any(x["email"] == "pgtest@example.com" and x["status"] == "paid" for x in admin["payments"]), admin["payments"]
print("premium + unlimited ok")

call("PUT", "/api/settings/telegram", {"telegram_chat_id": "123456"}, token=token)
me = call("GET", "/api/me", token=token)
assert me["telegram_chat_id"] == "123456"
print("telegram set ok")

me = call("GET", "/api/me", token=token)
assert me.get("reminder_days") == 3
call("PUT", "/api/settings/reminder", {"reminder_days": 7}, token=token)
me = call("GET", "/api/me", token=token)
assert me["reminder_days"] == 7
call("PUT", "/api/settings/reminder", {"reminder_days": 5}, token=token, expect=400)
print("reminder settings ok")

call("GET", "/api/export?format=csv", token=token, expect=200)
csv_resp = client.get("/api/export?format=csv", headers={"Authorization": "Bearer " + token})
assert "text/csv" in csv_resp.headers.get("content-type", ""), csv_resp.headers.get("content-type")
assert "Название" in csv_resp.text and "Netflix HD" in csv_resp.text and ";" in csv_resp.text
print("csv export ok")

export = call("GET", "/api/export", token=token)
assert len(export["subscriptions"]) == 4
print("export ok")

call("DELETE", f"/api/subscriptions/{s1['id']}", token=token)
me = call("GET", "/api/me", token=token)
assert len(me["subscriptions"]) == 3
print("delete ok")

call("POST", "/api/auth/logout", token=token)
call("GET", "/api/me", token=token, expect=401)
print("logout ok")

print("\nALL TESTS PASSED")
