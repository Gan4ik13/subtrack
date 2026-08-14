import datetime
import threading
import time

from db import db, now_iso, _is_schema_not_ready
from notify import send_charge_reminder

REMINDER_DAYS_DEFAULT = 3
_CHECK_INTERVAL = 3600  # раз в час


def _run_cycle():
    today = datetime.date.today().isoformat()
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.user_id, s.name, s.amount, s.currency, s.category,
                   s.next_date, s.last_notify, u.telegram_chat_id, u.premium, u.reminder_days
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.next_date IS NOT NULL AND s.next_date != ''
            """
        ).fetchall()

        notified_ids = []
        for r in rows:
            if not r["premium"] or not r["telegram_chat_id"]:
                continue
            days_ahead = r["reminder_days"] or REMINDER_DAYS_DEFAULT
            try:
                delta = (datetime.date.fromisoformat(r["next_date"]) - datetime.date.today()).days
            except ValueError:
                continue
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
