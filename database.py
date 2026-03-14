from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SubscriptionInfo:
    plan: str
    expire_date: str
    marzban_username: str


class Database:
    """SQLite gateway with explicit helper methods for bot domain operations."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    trial_used INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    marzban_username TEXT UNIQUE NOT NULL,
                    plan TEXT NOT NULL,
                    expire_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    invoice_id INTEGER UNIQUE NOT NULL,
                    plan TEXT NOT NULL DEFAULT '',
                    amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    is_processed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
                """
            )

            # Мягкая миграция для старой схемы без новых колонок.
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(payments)").fetchall()
            }
            if "plan" not in columns:
                conn.execute("ALTER TABLE payments ADD COLUMN plan TEXT NOT NULL DEFAULT ''")
            if "is_processed" not in columns:
                conn.execute("ALTER TABLE payments ADD COLUMN is_processed INTEGER NOT NULL DEFAULT 0")

    def ensure_user(self, telegram_id: int, username: str | None) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE users SET username = ? WHERE telegram_id = ?",
                    (username, telegram_id),
                )
                return int(row["id"])

            cursor = conn.execute(
                "INSERT INTO users (telegram_id, username, trial_used, created_at) VALUES (?, ?, 0, ?)",
                (telegram_id, username, utc_now_iso()),
            )
            return int(cursor.lastrowid)

    def get_user_by_tg(self, telegram_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()

    def set_trial_used(self, user_id: int) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE users SET trial_used = 1 WHERE id = ?", (user_id,))

    def get_latest_subscription(self, user_id: int) -> SubscriptionInfo | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT plan, expire_date, marzban_username
                FROM subscriptions
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return SubscriptionInfo(
                plan=str(row["plan"]),
                expire_date=str(row["expire_date"]),
                marzban_username=str(row["marzban_username"]),
            )

    def upsert_subscription(
        self,
        user_id: int,
        marzban_username: str,
        plan: str,
        expire_date: str,
    ) -> None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM subscriptions WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE subscriptions
                    SET marzban_username = ?, plan = ?, expire_date = ?
                    WHERE user_id = ?
                    """,
                    (marzban_username, plan, expire_date, user_id),
                )
                return

            conn.execute(
                """
                INSERT INTO subscriptions (user_id, marzban_username, plan, expire_date, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, marzban_username, plan, expire_date, utc_now_iso()),
            )

    def create_payment(
        self,
        user_id: int,
        invoice_id: int,
        plan: str,
        amount: float,
        status: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO payments (user_id, invoice_id, plan, amount, status, is_processed, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (user_id, invoice_id, plan, amount, status, utc_now_iso()),
            )

    def update_payment_status(self, invoice_id: int, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE payments SET status = ? WHERE invoice_id = ?", (status, invoice_id)
            )

    def mark_payment_processed(self, invoice_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE payments SET is_processed = 1 WHERE invoice_id = ?", (invoice_id,)
            )

    def get_payment(self, invoice_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM payments WHERE invoice_id = ?", (invoice_id,)
            ).fetchone()

    def get_user_count(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
            return int(row["cnt"])

    def get_trial_count(self) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM users WHERE trial_used = 1"
            ).fetchone()
            return int(row["cnt"])

    def get_active_subscriptions_count(self) -> int:
        now = utc_now_iso()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM subscriptions WHERE expire_date > ?", (now,)
            ).fetchone()
            return int(row["cnt"])

    def get_total_income(self) -> float:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'paid'"
            ).fetchone()
            return float(row["total"])

    def list_user_telegram_ids(self) -> list[int]:
        with self.connect() as conn:
            rows = conn.execute("SELECT telegram_id FROM users").fetchall()
            return [int(r["telegram_id"]) for r in rows]
