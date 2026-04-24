from __future__ import annotations

import sqlite3
from pathlib import Path

from audit.models import AuditLogRecord


PHASE2_COLUMNS = [
    ("holder_did", "TEXT"),
    ("vc_hash", "TEXT"),
    ("presentation_verified", "TEXT"),
]


class SQLiteAuditRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    action TEXT NOT NULL,
                    subject_did TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    message_hash TEXT NOT NULL,
                    raw_topic TEXT NOT NULL
                )
                """
            )
            existing = {row["name"] for row in conn.execute("PRAGMA table_info(audit_log)")}
            for col, sqltype in PHASE2_COLUMNS:
                if col not in existing:
                    conn.execute(f"ALTER TABLE audit_log ADD COLUMN {col} {sqltype}")
            conn.commit()

    def write(self, record: AuditLogRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (
                    ts, action, subject_did, dataset_id, purpose,
                    reason, message_hash, raw_topic,
                    holder_did, vc_hash, presentation_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.ts,
                    record.action,
                    record.subject_did,
                    record.dataset_id,
                    record.purpose,
                    record.reason,
                    record.message_hash,
                    record.raw_topic,
                    record.holder_did,
                    record.vc_hash,
                    record.presentation_verified,
                ),
            )
            conn.commit()

    def list_recent(self, limit: int = 100) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, ts, action, subject_did, dataset_id, purpose,
                       reason, message_hash, raw_topic,
                       holder_did, vc_hash, presentation_verified
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(r) for r in rows]
