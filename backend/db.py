import functools
import os
import threading
import time
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith("postgres") or DATABASE_URL.startswith("postgresql")

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    DB_ERRORS = (psycopg2.OperationalError, psycopg2.InterfaceError)
else:
    import sqlite3
    DB_ERRORS = (sqlite3.OperationalError,)

DB_PATH = os.environ.get("SUBTRAK_DB", os.path.join(os.path.dirname(__file__), "subtrack.db"))
_lock = threading.Lock()


def _schema():
    id_col = "id SERIAL PRIMARY KEY" if USE_POSTGRES else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    return f"""
CREATE TABLE IF NOT EXISTS users (
    {id_col},
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    premium INTEGER NOT NULL DEFAULT 0,
    premium_until TEXT,
    telegram_chat_id TEXT,
    reminder_days INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'RUB',
    period TEXT NOT NULL DEFAULT 'monthly',
    category TEXT NOT NULL DEFAULT 'Другое',
    next_date TEXT NOT NULL,
    last_notify TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    amount REAL NOT NULL,
    comment TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    external_id TEXT,
    created_at TEXT NOT NULL,
    verified_at TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


def get_conn():
    if USE_POSTGRES:
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=20,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=5,
            keepalives_count=5,
            options="-c statement_timeout=45000 -c idle_in_transaction_session_timeout=30000",
        )
        conn.set_session(autocommit=False)
        return Conn(conn, pg=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return Conn(conn, pg=False)


def init_db():
    with _lock:
        for stmt in _schema_statements():
            _exec_until_ok(stmt)
        _migrate_users_columns()


def _schema_statements():
    stmts = [s.strip() for s in _schema().split(";") if s.strip()]
    if USE_POSTGRES:
        stmts.append(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS reminder_days INTEGER NOT NULL DEFAULT 3"
        )
    return stmts


def _migrate_users_columns():
    """SQLite: ALTER TABLE не поддерживает IF NOT EXISTS — проверяем PRAGMA."""
    if USE_POSTGRES:
        return
    last = None
    for attempt in range(5):
        conn = get_conn()
        try:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "reminder_days" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN reminder_days INTEGER NOT NULL DEFAULT 3")
            conn.commit()
            return
        except DB_ERRORS as e:
            last = e
            time.sleep(1 + attempt)
        finally:
            conn.close()
    raise last


def _exec_until_ok(stmt, attempts=5):
    last = None
    for attempt in range(attempts):
        conn = get_conn()
        try:
            conn.execute(stmt)
            conn.commit()
            return
        except DB_ERRORS as e:
            last = e
            time.sleep(1 + attempt)
        finally:
            conn.close()
    raise last


def _is_schema_not_ready(exc):
    msg = str(getattr(exc, "pgerror", "") or exc).lower()
    return ("does not exist" in msg and ("relation" in msg or "table" in msg)) or "no such table" in msg


def retry_db(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last = None
        for attempt in range(6):
            try:
                return func(*args, **kwargs)
            except DB_ERRORS as e:
                last = e
                time.sleep((1 + attempt) if attempt < 4 else 6 + 2 * attempt)
            except Exception as e:
                if _is_schema_not_ready(e):
                    last = e
                    time.sleep((1 + attempt) if attempt < 4 else 6 + 2 * attempt)
                else:
                    raise
        raise last
    return wrapper


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now_iso():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Cursor:
    def __init__(self, raw, pg):
        self._raw = raw
        self._pg = pg
        self.rowcount = getattr(raw, "rowcount", -1) or -1

    def fetchone(self):
        row = self._raw.fetchone()
        if row is None:
            return None
        return dict(row) if not isinstance(row, dict) else row

    def fetchall(self):
        rows = self._raw.fetchall()
        return [dict(r) if not isinstance(r, dict) else r for r in rows]


class Conn:
    def __init__(self, raw, pg):
        self._raw = raw
        self.pg = pg
        self.lastrowid = None

    def _sql(self, sql, params):
        if self.pg:
            return sql.replace("?", "%s"), tuple(params or ())
        return sql, tuple(params or ())

    def _raw_cursor(self):
        if self.pg:
            return self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return self._raw.cursor()

    def execute(self, sql, params=()):
        s, p = self._sql(sql, params)
        cur = self._raw_cursor()
        cur.execute(s, p)
        c = Cursor(cur, self.pg)
        if self.pg:
            self.lastrowid = None
        else:
            self.lastrowid = cur.lastrowid
        return c

    def executescript(self, sql):
        if self.pg:
            cur = self._raw_cursor()
            for stmt in [x.strip() for x in sql.split(";") if x.strip()]:
                cur.execute(stmt)
        else:
            self._raw.executescript(sql)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        try:
            self._raw.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._raw.close()
        except Exception:
            pass


def insert_get_id(conn, sql, params=()):
    """Вставляет строку и возвращает id. Работает в PostgreSQL и SQLite."""
    if conn.pg:
        s, p = conn._sql(sql + " RETURNING id", params)
        cur = conn._raw_cursor()
        cur.execute(s, p)
        row = cur.fetchone()
        if row is None:
            return None
        return list(row.values())[0] if isinstance(row, dict) else row[0]
    s, p = conn._sql(sql, params)
    cur = conn._raw_cursor()
    cur.execute(s, p)
    return cur.lastrowid
