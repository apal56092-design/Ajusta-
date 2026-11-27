"""Durable SQLite queue primitives for bounded background task workers.

This module stores task payloads and leases only. It never executes payloads or code.
A trusted application worker must validate and dispatch claimed work.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4


@dataclass(frozen=True)
class QueueItem:
    task_id: str
    owner_id: str
    payload: dict
    status: str
    attempts: int
    lease_token: str | None
    lease_until: float | None


class SQLiteTaskQueue:
    """File-backed, owner-scoped queue with atomic claims and expiring leases."""

    def __init__(self, database_path: str | Path, *, max_attempts: int = 3) -> None:
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("a file-backed database is required for durable queue storage")
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self.max_attempts = max_attempts
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS task_queue (
                task_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
                attempts INTEGER NOT NULL DEFAULT 0,
                lease_token TEXT,
                lease_until REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                error TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS task_queue_claim_idx ON task_queue(status, created_at)")

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _item(row) -> QueueItem:
        payload = json.loads(row["payload_json"])
        if not isinstance(payload, dict):
            raise ValueError("queued payload must be an object")
        return QueueItem(row["task_id"], row["owner_id"], payload, row["status"],
                         row["attempts"], row["lease_token"], row["lease_until"])

    def enqueue(self, task_id: str, owner_id: str, payload: dict) -> QueueItem:
        if not isinstance(task_id, str) or not task_id.strip() or len(task_id) > 100:
            raise ValueError("task_id must contain 1 to 100 characters")
        if not isinstance(owner_id, str) or not owner_id.strip() or len(owner_id) > 200:
            raise ValueError("owner_id is required")
        if not isinstance(payload, dict):
            raise TypeError("payload must be an object")
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > 20000:
            raise ValueError("payload exceeds 20000 characters")
        now = time.time()
        with self._connect() as db:
            try:
                db.execute("INSERT INTO task_queue(task_id,owner_id,payload_json,status,created_at,updated_at) VALUES(?,?,?,'queued',?,?)",
                           (task_id.strip(), owner_id, encoded, now, now))
            except sqlite3.IntegrityError as exc:
                raise ValueError("task already exists in queue") from exc
            row = db.execute("SELECT * FROM task_queue WHERE task_id=?", (task_id.strip(),)).fetchone()
        return self._item(row)

    def claim_next(self, worker_id: str, *, lease_seconds: int = 60) -> QueueItem | None:
        if not isinstance(worker_id, str) or not worker_id.strip() or len(worker_id) > 100:
            raise ValueError("worker_id is required")
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool) or not 5 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 5 and 3600")
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""UPDATE task_queue SET status=CASE WHEN attempts >= ? THEN 'failed' ELSE 'queued' END,
                          lease_token=NULL, lease_until=NULL, updated_at=?,
                          error=CASE WHEN attempts >= ? THEN 'Worker lease expired; retry limit reached.' ELSE error END
                          WHERE status='running' AND lease_until <= ?""",
                       (self.max_attempts, now, self.max_attempts, now))
            row = db.execute("SELECT * FROM task_queue WHERE status='queued' ORDER BY created_at, task_id LIMIT 1").fetchone()
            if row is None:
                db.commit()
                return None
            token = uuid4().hex
            updated = db.execute("""UPDATE task_queue SET status='running', attempts=attempts+1,
                                    lease_token=?, lease_until=?, updated_at=?
                                    WHERE task_id=? AND status='queued'""",
                                 (token, now + lease_seconds, now, row["task_id"]))
            if updated.rowcount != 1:
                db.rollback()
                return None
            claimed = db.execute("SELECT * FROM task_queue WHERE task_id=?", (row["task_id"],)).fetchone()
            db.commit()
        return self._item(claimed)

    def complete(self, task_id: str, lease_token: str, *, succeeded: bool, error: str | None = None) -> bool:
        if not isinstance(succeeded, bool):
            raise TypeError("succeeded must be a boolean")
        status = "succeeded" if succeeded else "failed"
        safe_error = error[:500] if isinstance(error, str) else None
        with self._connect() as db:
            cursor = db.execute("""UPDATE task_queue SET status=?, error=?, lease_token=NULL,
                                   lease_until=NULL, updated_at=?
                                   WHERE task_id=? AND status='running' AND lease_token=?""",
                                (status, safe_error, time.time(), task_id, lease_token))
            return cursor.rowcount == 1

    def cancel(self, task_id: str, owner_id: str) -> bool:
        """Cancel queued work; running work requires cooperative worker cancellation."""
        with self._connect() as db:
            cursor = db.execute("""UPDATE task_queue SET status='cancelled', updated_at=?
                                   WHERE task_id=? AND owner_id=? AND status='queued'""",
                                (time.time(), task_id, owner_id))
            return cursor.rowcount == 1

    def get(self, task_id: str, owner_id: str) -> QueueItem | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM task_queue WHERE task_id=? AND owner_id=?",
                             (task_id, owner_id)).fetchone()
        return self._item(row) if row else None
