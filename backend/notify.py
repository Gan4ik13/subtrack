import os
import time

import requests

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
OWNER_TG_CHAT_ID = os.environ.get("OWNER_TG_CHAT_ID", "")
NOTIFY_TG_ENABLED = bool(BOT_TOKEN)


def send_telegram(chat_id: str, text: str) -> bool:
    if not BOT_TOKEN or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=20,
        )
        return resp.status_code == 200 and resp.json().get("ok", False)
    except Exception:
        return False


def send_charge_reminder(chat_id: str, sub) -> None:
    date_str = sub["next_date"]
    text = (
        f"📅 <b>SubTrack: скоро списание</b>\n\n"
        f"<b>{sub['name']}</b> — {sub['amount']:.2f} {sub['currency']}\n"
        f"Категория: {sub['category']}\n"
        f"Списание: {date_str}\n\n"
        f"Проверьте, что оплатите вовремя или отмените подписку."
    )
    send_telegram(chat_id, text)


def send_premium_confirmation(chat_id: str, until: str) -> None:
    text = (
        f"🎉 <b>SubTrack Premium активирован!</b>\n\n"
        f"Открыты все функции: безлимит подписок, аналитика расходов, "
        f"ближайшие списания и напоминания о платежах.\n"
        f"Premium активен до {until or 'бессрочно'}."
    )
    send_telegram(chat_id, text)


def send_owner_payment_notice(user_email: str, amount: float, until: str, sender: str = "") -> None:
    text = (
        f"💰 <b>Оплата SubTrack Premium</b>\n\n"
        f"Пользователь: {user_email}\n"
        f"Сумма: {amount:.2f} ₽\n"
        f"Premium до: {until or 'бессрочно'}\n"
        f"{('Отправитель: ' + sender) if sender else ''}"
        f"\nНе забудьте проверить, что чек по самозанятости сформирован."
    )
    send_telegram(OWNER_TG_CHAT_ID, text)


def send_payment_confirmation(chat_id: str, text: str) -> None:
    send_telegram(chat_id, text)


def _format_ts(ts):
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(ts))
