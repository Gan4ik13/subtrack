import json
import os
import time
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(method, path, body=None, token=None, expect=200):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data=data) as resp:
            assert resp.status == expect, f"{method} {path}: status {resp.status} != {expect}"
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        assert e.code == expect, f"{method} {path}: status {e.code} != {expect}, body={e.read().decode()}"
        return {}


print("health:", call("GET", "/health"))

t1 = call("POST", "/api/auth/register", {"email": "test@example.com", "password": "pass123"})
token = t1["token"]
print("register ok")

call("POST", "/api/auth/register", {"email": "test@example.com", "password": "pass123"}, expect=409)
print("duplicate rejected ok")

call("POST", "/api/auth/login", {"email": "test@example.com", "password": "wrong"}, expect=401)
print("bad login rejected ok")

t2 = call("POST", "/api/auth/login", {"email": "test@example.com", "password": "pass123"})
token2 = t2["token"]
print("login ok")

me = call("GET", "/api/me", token=token)
assert me["premium"] is False and me["subscriptions"] == []
print("me ok")

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
assert p["pay_url"] is None  # manual mode
st = call("GET", f"/api/payment/status/{p['payment_id']}", token=token)
assert st["premium"] is False
call("POST", f"/api/payment/{p['payment_id']}/confirm", token=token)
me = call("GET", "/api/me", token=token)
assert me["premium"] is True
call("POST", "/api/subscriptions", {"name": "D", "amount": 1, "period": "monthly", "next_date": "2026-09-01"}, token=token)
print("premium + unlimited ok")

call("PUT", "/api/settings/telegram", {"telegram_chat_id": "123456"}, token=token)
me = call("GET", "/api/me", token=token)
assert me["telegram_chat_id"] == "123456"
print("telegram set ok")

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
