import os
import threading
import time

import requests

from db import db

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
POLLING_ENABLED = os.environ.get("TG_POLLING_ENABLED", "1") == "1"
_user_cache = {"username": None, "at": 0.0}


def get_bot_username():
    """Возвращает @username бота (getMe, кэш 1 час)."""
    if not BOT_TOKEN:
        return None
    if _user_cache["username"] and time.time() - _user_cache["at"] < 3600:
        return _user_cache["username"]
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=15)
        data = r.json()
        if data.get("ok"):
            _user_cache["username"] = data["result"].get("username")
            _user_cache["at"] = time.time()
            return _user_cache["username"]
    except Exception:
        pass
    return None


def _send(chat_id, text):
    if not BOT_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=20,
        )
    except Exception:
        pass


def _handle_update(update):
    msg = update.get("message") or {}
    text = (msg.get("text") or "").strip()
    chat = msg.get("chat") or {}
    chat_id = str(chat.get("id", ""))
    if not text or not chat_id or not text.startswith("/start"):
        return
    parts = text.split()
    payload = parts[1] if len(parts) > 1 else ""
    if payload.startswith("connect_"):
        uid = payload[len("connect_"):]
        try:
            uid = int(uid)
        except ValueError:
            _send(chat_id, "Не удалось распознать ссылку. Откройте бота из раздела «Подключить через бота» на сайте.")
            return
        with db() as conn:
            user = conn.execute("SELECT id FROM users WHERE id = ?", (uid,)).fetchone()
            if not user:
                _send(chat_id, "Аккаунт не найден. Проверьте ссылку или зарегистрируйтесь на сайте.")
                return
            conn.execute("UPDATE users SET telegram_chat_id = ? WHERE id = ?", (chat_id, uid))
        _send(chat_id, "✅ Подключено! Напоминания о списаниях будут приходить сюда.\n\nСменить аккаунт можно в настройках SubPing.")
    else:
        _send(chat_id, "Привет! Я бот SubPing.\n\nЧтобы получать напоминания о списаниях:\n1. Зайдите на сайт\n2. В настройках нажмите «Подключить через бота»\n3. Я привяжу ваш Telegram к аккаунту.")


def _poll_once(offset):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            json={"offset": offset, "timeout": 25, "allowed_updates": ["message"]},
            timeout=35,
        )
        data = r.json()
    except Exception:
        return offset, None
    if not data.get("ok"):
        return offset, data.get("error_code")
    last = offset
    for u in data.get("result", []):
        last = u["update_id"] + 1
        try:
            _handle_update(u)
        except Exception as e:
            print(f"[bot] handle error: {e}")
    return last, None


def _loop():
    offset = 0
    while True:
        if not BOT_TOKEN:
            time.sleep(60)
            continue
        try:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", timeout=15)
        except Exception:
            pass
        while True:
            try:
                offset, err = _poll_once(offset)
                if err == 409:
                    time.sleep(30)
                elif err is not None:
                    time.sleep(5)
            except Exception:
                time.sleep(10)


def start_polling():
    if not POLLING_ENABLED or not BOT_TOKEN:
        return None
    t = threading.Thread(target=_loop, daemon=True, name="subping-bot")
    t.start()
    return t
