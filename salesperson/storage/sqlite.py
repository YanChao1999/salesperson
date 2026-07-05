from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from salesperson.errors import PlatformNotFoundError
from salesperson.models import (
    DealRecord,
    LLMConfig,
    SalesBehavior,
    UsageRecord,
    Website,
    WebsiteUser,
)


class SqliteRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS websites (
                    website_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    plan TEXT NOT NULL DEFAULT 'free',
                    llm_json TEXT NOT NULL,
                    plugin_json TEXT NOT NULL,
                    behavior_json TEXT NOT NULL,
                    api_key_hash TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS website_meta (
                    website_id TEXT PRIMARY KEY,
                    user_sequence INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (website_id) REFERENCES websites(website_id)
                );
                CREATE TABLE IF NOT EXISTS users (
                    website_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    external_user_id TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (website_id, user_id),
                    FOREIGN KEY (website_id) REFERENCES websites(website_id)
                );
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    messages INTEGER NOT NULL,
                    tokens INTEGER NOT NULL,
                    outcome TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS deal_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    value REAL NOT NULL,
                    currency TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(websites)").fetchall()
            }
            if "plan" not in columns:
                conn.execute(
                    "ALTER TABLE websites ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'"
                )

    def save_website(self, website: Website) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO websites (
                    website_id, name, domain, plan, llm_json, plugin_json, behavior_json, api_key_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(website_id) DO UPDATE SET
                    name = excluded.name,
                    domain = excluded.domain,
                    plan = excluded.plan,
                    llm_json = excluded.llm_json,
                    plugin_json = excluded.plugin_json,
                    behavior_json = excluded.behavior_json,
                    api_key_hash = excluded.api_key_hash
                """,
                (
                    website.website_id,
                    website.name,
                    website.domain,
                    website.plan,
                    json.dumps(asdict(website.llm)),
                    json.dumps(website.plugin),
                    json.dumps(asdict(website.behavior)),
                    website.api_key_hash,
                ),
            )
            conn.execute(
                """
                INSERT INTO website_meta (website_id, user_sequence)
                VALUES (?, 0)
                ON CONFLICT(website_id) DO NOTHING
                """,
                (website.website_id,),
            )

    def _row_to_website(self, row: sqlite3.Row) -> Website:
        return Website(
            website_id=row["website_id"],
            name=row["name"],
            domain=row["domain"],
            llm=LLMConfig(**json.loads(row["llm_json"])),
            plugin=json.loads(row["plugin_json"]),
            behavior=SalesBehavior(**json.loads(row["behavior_json"])),
            api_key_hash=row["api_key_hash"],
            plan=row["plan"] if "plan" in row.keys() else "free",
        )

    def get_website(self, website_id: str) -> Website:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM websites WHERE website_id = ?",
                (website_id,),
            ).fetchone()
        if row is None:
            raise PlatformNotFoundError(f"Unknown website '{website_id}'.")
        return self._row_to_website(row)

    def list_api_key_hashes(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT website_id, api_key_hash FROM websites WHERE api_key_hash != ''"
            ).fetchall()
        return {row["website_id"]: row["api_key_hash"] for row in rows}

    def save_user(self, user: WebsiteUser) -> None:
        self.get_website(user.website_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, website_id, external_user_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user.user_id,
                    user.website_id,
                    user.external_user_id,
                    json.dumps(user.metadata),
                    user.created_at,
                ),
            )

    def get_user(self, website_id: str, user_id: str) -> WebsiteUser:
        self.get_website(website_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE website_id = ? AND user_id = ?",
                (website_id, user_id),
            ).fetchone()
        if row is None:
            raise PlatformNotFoundError(
                f"Unknown user '{user_id}' for website '{website_id}'."
            )
        return WebsiteUser(
            user_id=row["user_id"],
            website_id=row["website_id"],
            external_user_id=row["external_user_id"],
            metadata=json.loads(row["metadata_json"]),
            created_at=row["created_at"],
        )

    def next_user_number(self, website_id: str) -> int:
        self.get_website(website_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO website_meta (website_id, user_sequence)
                VALUES (?, 0)
                ON CONFLICT(website_id) DO NOTHING
                """,
                (website_id,),
            )
            conn.execute(
                """
                UPDATE website_meta
                SET user_sequence = user_sequence + 1
                WHERE website_id = ?
                """,
                (website_id,),
            )
            row = conn.execute(
                "SELECT user_sequence FROM website_meta WHERE website_id = ?",
                (website_id,),
            ).fetchone()
        return int(row["user_sequence"])

    def update_behavior(self, website_id: str, behavior: SalesBehavior) -> SalesBehavior:
        website = self.get_website(website_id)
        website.behavior = behavior
        self.save_website(website)
        return behavior

    def append_usage(self, usage: UsageRecord) -> UsageRecord:
        self.get_website(usage.website_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO usage_records (
                    website_id, user_id, channel, messages, tokens, outcome, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usage.website_id,
                    usage.user_id,
                    usage.channel,
                    usage.messages,
                    usage.tokens,
                    usage.outcome,
                    usage.created_at,
                ),
            )
        return usage

    def append_deal(self, deal: DealRecord) -> DealRecord:
        self.get_website(deal.website_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO deal_records (
                    website_id, user_id, stage, value, currency, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deal.website_id,
                    deal.user_id,
                    deal.stage,
                    deal.value,
                    deal.currency,
                    deal.note,
                    deal.created_at,
                ),
            )
        return deal

    def list_usage(self, website_id: str) -> list[UsageRecord]:
        self.get_website(website_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT website_id, user_id, channel, messages, tokens, outcome, created_at
                FROM usage_records
                WHERE website_id = ?
                ORDER BY id
                """,
                (website_id,),
            ).fetchall()
        return [
            UsageRecord(
                website_id=row["website_id"],
                user_id=row["user_id"],
                channel=row["channel"],
                messages=row["messages"],
                tokens=row["tokens"],
                outcome=row["outcome"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def list_deals(self, website_id: str) -> list[DealRecord]:
        self.get_website(website_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT website_id, user_id, stage, value, currency, note, created_at
                FROM deal_records
                WHERE website_id = ?
                ORDER BY id
                """,
                (website_id,),
            ).fetchall()
        return [
            DealRecord(
                website_id=row["website_id"],
                user_id=row["user_id"],
                stage=row["stage"],
                value=row["value"],
                currency=row["currency"],
                note=row["note"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def count_users(self, website_id: str) -> int:
        self.get_website(website_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM users WHERE website_id = ?",
                (website_id,),
            ).fetchone()
        return int(row["total"])

    def website_exists(self, website_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM websites WHERE website_id = ?",
                (website_id,),
            ).fetchone()
        return row is not None

    def next_website_id(self, base: str) -> str:
        if not self.website_exists(base):
            return base
        suffix = 2
        while self.website_exists(f"{base}-{suffix}"):
            suffix += 1
        return f"{base}-{suffix}"
