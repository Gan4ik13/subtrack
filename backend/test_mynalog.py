"""Тест модуля «Мой налог» (mynalog): авторизация, создание чека, обработка ошибок.

HTTP к lknpd.nalog.ru мокается (monkeypatch requests) — реальных чеков не создаёт.

Запуск:
    python test_mynalog.py
"""
import os

os.environ["MYNALOG_INN"] = "123456789012"
os.environ["MYNALOG_PASSWORD"] = "test_password"
os.environ["SUBTRAK_DB"] = os.path.join(os.environ.get("TEMP", "/tmp"), "subtrack_test_mynalog.db")

import mynalog

CAPTURED = {}


class FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


_real_post = mynalog.requests.post


def fake_post(url, headers=None, json=None, timeout=None, **kw):
    CAPTURED[url] = {"headers": headers or {}, "json": json}
    if url == mynalog.AUTH_URL:
        return FakeResp(200, {"token": "fake_lknpd_token", "profile": {}})
    if url == mynalog.INCOME_URL:
        return FakeResp(200, {"data": {"approvedReceiptUuid": "rcpt-1", "url": "https://lknpd.nalog.ru/api/v1/receipt/1/print"}})
    return FakeResp(404, {"error": "unknown"})


mynalog.requests.post = fake_post

# 1) создание чека: токен, заголовки, тело
receipt = mynalog.create_income_receipt(name="SubPing Premium (1 месяц)", amount=99.0, customer_email="buyer@example.com")
assert receipt["approvedReceiptUuid"] == "rcpt-1"
auth_req = CAPTURED[mynalog.AUTH_URL]
assert auth_req["json"]["username"] == "123456789012"
assert auth_req["json"]["password"] == "test_password"
income_req = CAPTURED[mynalog.INCOME_URL]
h = income_req["headers"]
assert h["Authorization"] == "Bearer fake_lknpd_token"
assert "Mozilla" in h["User-Agent"]
body = income_req["json"]
assert body["totalAmount"] == 99.0
assert body["services"][0]["name"] == "SubPing Premium (1 месяц)"
assert body["client"]["displayName"] == "buyer@example.com"
assert body["client"]["incomeType"] == "FROM_INDIVIDUAL"
print("create receipt ok")

# 2) ошибка API — читаемое исключение
mynalog.requests.post = lambda url, **kw: FakeResp(401, {"message": "Неверный логин или пароль"})
try:
    mynalog.create_income_receipt(name="X", amount=1.0)
    raise SystemExit("должно было бросить MyNalogError")
except mynalog.MyNalogError as e:
    assert "401" in str(e)
print("api error handling ok")

# 3) без настройки — исключение
mynalog.MYNALOG_INN = ""
try:
    mynalog.create_income_receipt(name="X", amount=1.0)
    raise SystemExit("должно было бросить MyNalogError")
except mynalog.MyNalogError:
    pass
mynalog.MYNALOG_INN = "123456789012"
print("not-configured guard ok")

# 4) интеграция: _issue_self_employed_receipt не падает и возвращает url
import main as app_module

mynalog.requests.post = fake_post
user = {"email": "buyer@example.com"}
payment = {"id": "pay_x", "amount": 99.0, "comment": "subtrack-1-xxxxxx|SubPing Premium (1 месяц)"}
res = app_module._issue_self_employed_receipt(user, payment)
assert res and res.get("url"), res
payment_bad = dict(payment, id="pay_y")
mynalog.requests.post = lambda url, **kw: FakeResp(500, {"error": "boom"})
res_bad = app_module._issue_self_employed_receipt(user, payment_bad)
assert res_bad and "error" in res_bad
print("main integration ok")

mynalog.requests.post = _real_post
print("\nMYNALOG TESTS PASSED")
