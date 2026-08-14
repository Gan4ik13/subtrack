import asyncio
import datetime
import json
import os
import urllib.parse
import uuid

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, EmailStr

import auth as auth_util
import payments as pay
from db import db, init_db, insert_get_id, now_iso, retry_db
from scheduler import start_scheduler

app = FastAPI(title="SubTrack API")

FRONTEND_ORIGINS = [
    o.strip()
    for o in os.environ.get("FRONTEND_ORIGIN", "http://localhost:8080,http://localhost:5500,https://gan4ik13.github.io").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class SubIn(BaseModel):
    name: str
    amount: float
    currency: str = "RUB"
    period: str = "monthly"
    category: str = "Другое"
    next_date: str


class TelegramIn(BaseModel):
    telegram_chat_id: str


class ReminderIn(BaseModel):
    reminder_days: int


def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Не авторизован")
    token = authorization[7:]
    with db() as conn:
        row = conn.execute(
            "SELECT u.* FROM users u JOIN auth_sessions s ON s.user_id = u.id WHERE s.token = ?",
            (token,),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Сессия недействительна")
    return dict(row)


def activate_premium(conn, user_id: int, months: int = 1) -> None:
    row = conn.execute("SELECT premium_until FROM users WHERE id = ?", (user_id,)).fetchone()
    base = datetime.date.today()
    if row and row["premium_until"]:
        try:
            existing = datetime.date.fromisoformat(row["premium_until"])
            if existing > base:
                base = existing
        except ValueError:
            pass
    new_until = base + datetime.timedelta(days=31 * months)
    conn.execute(
        "UPDATE users SET premium = 1, premium_until = ? WHERE id = ?",
        (new_until.isoformat(), user_id),
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/auth/register")
@retry_db
def register(body: RegisterIn):
    email = body.email.lower().strip()
    if len(body.password) < 4:
        raise HTTPException(400, "Пароль минимум 4 символа")
    token = auth_util.new_token()
    with db() as conn:
        exists = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            if auth_util.verify_password(body.password, exists["salt"], exists["password_hash"]):
                conn.execute(
                    "INSERT INTO auth_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                    (token, exists["id"], now_iso()),
                )
                return {"token": token, "email": email}
            raise HTTPException(409, "Пользователь с таким email уже существует")
        salt, h = auth_util.create_user_password(body.password)
        user_id = insert_get_id(
            conn,
            "INSERT INTO users (email, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (email, h, salt, now_iso()),
        )
        conn.execute(
            "INSERT INTO auth_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now_iso()),
        )
    return {"token": token, "email": email}


@app.post("/api/auth/login")
@retry_db
def login(body: LoginIn):
    email = body.email.lower().strip()
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        raise HTTPException(401, "Неверный email или пароль")
    if not auth_util.verify_password(body.password, user["salt"], user["password_hash"]):
        raise HTTPException(401, "Неверный email или пароль")
    token = auth_util.new_token()
    with db() as conn:
        conn.execute(
            "INSERT INTO auth_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user["id"], now_iso()),
        )
    return {"token": token, "email": email}


@app.post("/api/auth/logout")
@retry_db
def logout(user: dict = Depends(current_user), authorization: str = Header(default="")):
    token = authorization[7:]
    with db() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
    return {"ok": True}


@app.get("/api/me")
@retry_db
def me(user: dict = Depends(current_user)):
    with db() as conn:
        subs = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY next_date", (user["id"],)
        ).fetchall()
    return {
        "email": user["email"],
        "premium": bool(user["premium"]),
        "premium_until": user["premium_until"],
        "telegram_chat_id": user["telegram_chat_id"],
        "reminder_days": user.get("reminder_days", 3),
        "subscriptions": [dict(s) for s in subs],
    }


def _sub_payload(user, body: SubIn):
    name = body.name.strip()[:40]
    if not name or not body.amount or body.amount <= 0 or not body.next_date:
        raise HTTPException(400, "Заполните поля корректно")
    return {
        "name": name,
        "amount": round(body.amount, 2),
        "currency": body.currency,
        "period": body.period if body.period in ("monthly", "yearly") else "monthly",
        "category": body.category,
        "next_date": body.next_date,
    }


@app.post("/api/subscriptions")
@retry_db
def create_sub(body: SubIn, user: dict = Depends(current_user)):
    with db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) c FROM subscriptions WHERE user_id = ?", (user["id"],)
        ).fetchone()["c"]
    if not user["premium"] and count >= 3:
        raise HTTPException(403, "Лимит бесплатного тарифа — 3 подписки")
    data = _sub_payload(user, body)
    sid = "sub_" + uuid.uuid4().hex[:8]
    with db() as conn:
        conn.execute(
            "INSERT INTO subscriptions (id, user_id, name, amount, currency, period, category, next_date)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, user["id"], data["name"], data["amount"], data["currency"],
             data["period"], data["category"], data["next_date"]),
        )
    return {"id": sid}


@app.put("/api/subscriptions/{sid}")
@retry_db
def update_sub(sid: str, body: SubIn, user: dict = Depends(current_user)):
    data = _sub_payload(user, body)
    with db() as conn:
        cur = conn.execute(
            "UPDATE subscriptions SET name=?, amount=?, currency=?, period=?, category=?, next_date=?, last_notify=NULL"
            " WHERE id=? AND user_id=?",
            (data["name"], data["amount"], data["currency"], data["period"],
             data["category"], data["next_date"], sid, user["id"]),
        )
    if cur.rowcount == 0:
        raise HTTPException(404, "Подписка не найдена")
    return {"ok": True}


@app.delete("/api/subscriptions/{sid}")
@retry_db
def delete_sub(sid: str, user: dict = Depends(current_user)):
    with db() as conn:
        cur = conn.execute("DELETE FROM subscriptions WHERE id=? AND user_id=?", (sid, user["id"]))
    if cur.rowcount == 0:
        raise HTTPException(404, "Подписка не найдена")
    return {"ok": True}


@app.post("/api/payment/create")
@retry_db
def create_payment(user: dict = Depends(current_user), request: Request = None):
    if user["premium"]:
        raise HTTPException(400, "Premium уже активен")
    pid = pay.new_payment_id()
    comment = f"subtrack-{user['id']}-{pid[-6:]}"
    with db() as conn:
        conn.execute(
            "INSERT INTO payments (id, user_id, provider, amount, comment, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, user["id"], pay.PAYMENT_MODE, pay.PRICE_RUB, comment, now_iso()),
        )
    payment = {"id": pid, "comment": comment, "amount": pay.PRICE_RUB}
    try:
        pay_url = pay.build_payment_url(payment, base_url=str(request.base_url))
    except Exception as e:
        raise HTTPException(502, f"Не удалось создать платёж: {e}")
    with db() as conn:
        conn.execute(
            "UPDATE payments SET status='created', external_id=? WHERE id=?",
            (payment.get("external_id"), pid),
        )
    return {"payment_id": pid, "pay_url": pay_url}


@app.get("/api/payment/pay/{pid}")
@retry_db
def payment_pay_page(pid: str):
    """Страница с POST-формой перевода в ЮMoney (открывается в новой вкладке)."""
    with db() as conn:
        p = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
    if not p:
        raise HTTPException(404, "Платёж не найден")
    if p["status"] == "paid":
        raise HTTPException(400, "Платёж уже оплачен")
    return HTMLResponse(
        pay.build_payment_form_html({"comment": p["comment"], "amount": p["amount"]})
    )


@app.get("/api/payment/status/{pid}")
@retry_db
def payment_status(pid: str, user: dict = Depends(current_user)):
    with db() as conn:
        p = conn.execute("SELECT * FROM payments WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    if not p:
        raise HTTPException(404, "Платёж не найден")
    if p["status"] == "paid":
        return {"status": "paid", "premium": True}
    paid = False
    if p["status"] == "created":
        try:
            paid = pay.check_payment(p)
        except Exception:
            paid = False
    if paid:
        with db() as conn:
            activate_premium(conn, user["id"])
            conn.execute(
                "UPDATE payments SET status='paid', verified_at=? WHERE id=?",
                (now_iso(), pid),
            )
    return {"status": "paid" if paid else p["status"], "premium": paid}


@app.post("/api/payment/{pid}/confirm")
@retry_db
def confirm_payment(pid: str, user: dict = Depends(current_user)):
    # Ручное подтверждение доступно только в режиме manual.
    if pay.PAYMENT_MODE != "manual":
        raise HTTPException(403, "Автоподтверждение недоступно в этом режиме оплаты")
    with db() as conn:
        p = conn.execute("SELECT * FROM payments WHERE id=? AND user_id=?", (pid, user["id"])).fetchone()
    if not p:
        raise HTTPException(404, "Платёж не найден")
    with db() as conn:
        activate_premium(conn, user["id"])
        conn.execute("UPDATE payments SET status='paid', verified_at=? WHERE id=?", (now_iso(), pid))
    return {"ok": True, "premium": True}


@retry_db
def _activate_premium_by_label(label: str) -> None:
    with db() as conn:
        p = conn.execute(
            "SELECT * FROM payments WHERE comment = ? AND status != 'paid'", (label,)
        ).fetchone()
        if p:
            activate_premium(conn, p["user_id"])
            conn.execute(
                "UPDATE payments SET status='paid', verified_at=? WHERE id=?",
                (now_iso(), p["id"]),
            )


@app.post("/api/payments/yoomoney/notify")
async def yoomoney_notify(request: Request):
    """HTTP-уведомление ЮMoney о зачислении. Активирует Premium по label."""
    raw = (await request.body()).decode("utf-8")
    params = dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))
    if not pay.verify_notification(params):
        raise HTTPException(403, "Bad signature")
    if params.get("notification_type") != "p2p-incoming" or params.get("test_notification") in ("true", "1"):
        return {"ok": True}
    label = params.get("label", "")
    if label:
        await asyncio.to_thread(_activate_premium_by_label, label)
    return {"ok": True}


@app.put("/api/settings/telegram")
@retry_db
def set_telegram(body: TelegramIn, user: dict = Depends(current_user)):
    chat_id = body.telegram_chat_id.strip()
    with db() as conn:
        conn.execute("UPDATE users SET telegram_chat_id=? WHERE id=?", (chat_id or None, user["id"]))
    return {"ok": True}


@app.put("/api/settings/reminder")
@retry_db
def set_reminder(body: ReminderIn, user: dict = Depends(current_user)):
    if not user["premium"]:
        raise HTTPException(403, "Доступно только для Premium")
    if body.reminder_days not in (1, 3, 7):
        raise HTTPException(400, "Допустимо: 1, 3 или 7 дней")
    with db() as conn:
        conn.execute("UPDATE users SET reminder_days=? WHERE id=?", (body.reminder_days, user["id"]))
    return {"ok": True}


@app.get("/api/export")
@retry_db
def export(format: str = "json", user: dict = Depends(current_user)):
    with db() as conn:
        subs = conn.execute(
            "SELECT name, amount, currency, period, category, next_date FROM subscriptions WHERE user_id=?",
            (user["id"],),
        ).fetchall()
    if format == "csv":
        import csv
        import io

        buf = io.StringIO()
        buf.write("\ufeff")
        w = csv.writer(buf, delimiter=";")
        w.writerow(["Название", "Сумма", "Валюта", "Периодичность", "Категория", "Следующее списание"])
        for s in subs:
            period = "Ежемесячно" if s["period"] == "monthly" else "Ежегодно"
            w.writerow([
                s["name"],
                f"{float(s['amount']):.2f}".replace(".", ","),
                s["currency"],
                period,
                s["category"],
                s["next_date"],
            ])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="subtrack-export-{datetime.date.today().isoformat()}.csv"'
            },
        )
    payload = {
        "email": user["email"],
        "premium": bool(user["premium"]),
        "premium_until": user["premium_until"],
        "exportedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "subscriptions": [dict(s) for s in subs],
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="subtrack-export-{datetime.date.today().isoformat()}.json"'},
    )


def _init_db_background():
    import threading
    import time

    def worker():
        for attempt in range(1, 121):
            try:
                init_db()
                print("[startup] DB schema ready")
                return
            except Exception as exc:
                print(f"[startup] init_db attempt {attempt} failed: {exc}")
                time.sleep(10)

    threading.Thread(target=worker, daemon=True, name="init-db").start()


_init_db_background()
start_scheduler()
