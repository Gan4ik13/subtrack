import datetime
import threading
import time

from db import db, now_iso, _is_schema_not_ready
from notify import send_charge_reminder

REMINDER_DAYS_DEFAULT = 3
_CHECK_INTERVAL = 3600  # раз в час


def _advance_date(next_date: datetime.date, period: str, today: datetime.date) -> datetime.date:
    anchor_day = next_date.day
    while next_date < today:
        if period == "yearly":
            year = next_date.year + 1
            try:
                next_date = next_date.replace(year=year, day=anchor_day)
            except ValueError:
                next_date = next_date.replace(year=year, day=anchor_day - 1)
        else:
            year = next_date.year + (next_date.month // 12)
            month = next_date.month % 12 + 1
            day = min(anchor_day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                                   31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            next_date = next_date.replace(year=year, month=month, day=day)
    return next_date


def _run_cycle():
    current_date = datetime.date.today()
    today = current_date.isoformat()
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.user_id, s.name, s.amount, s.currency, s.category,
                   s.next_date, s.last_notify, s.period, u.telegram_chat_id, u.premium, u.reminder_days
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.next_date IS NOT NULL AND s.next_date != ''
            """
        ).fetchall()

        notified_ids = []
        for r in rows:
            try:
                stored_date = datetime.date.fromisoformat(r["next_date"])
            except ValueError:
                continue
            next_date = _advance_date(stored_date, r["period"], current_date)
            if next_date != stored_date:
                r["next_date"] = next_date.isoformat()
                r["last_notify"] = None
                conn.execute(
                    "UPDATE subscriptions SET next_date = ?, last_notify = NULL WHERE id = ?",
                    (r["next_date"], r["id"]),
                )
            if not r["premium"] or not r["telegram_chat_id"]:
                continue
            days_ahead = r["reminder_days"] or REMINDER_DAYS_DEFAULT
            delta = (next_date - current_date).days
            if not (0 <= delta <= days_ahead):
                continue
            if r["last_notify"] == today:
                continue
            send_charge_reminder(r["telegram_chat_id"], r)
            notified_ids.append((r["id"], today))

        for sid, day in notified_ids:
            conn.execute("UPDATE subscriptions SET last_notify = ? WHERE id = ?", (day, sid))


def _loop():
    while True:
        try:
            _run_cycle()
            time.sleep(_CHECK_INTERVAL)
        except Exception as e:
            if _is_schema_not_ready(e):
                time.sleep(30)
            else:
                print(f"[scheduler] error: {e}")
                time.sleep(_CHECK_INTERVAL)


def start_scheduler():
    t = threading.Thread(target=_loop, daemon=True, name="subtrack-scheduler")
    t.start()
    return t
