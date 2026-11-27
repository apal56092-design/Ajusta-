"""Durable, owner-scoped SQLite queue and progress event store.

Queue payloads are data only. Trusted host application code performs all execution.
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
    progress_percent: int = 0
    progress_message: str = "Queued"
    cancel_requested: bool = False


class SQLiteTaskQueue:
    """File-backed queue with atomic claims, leases, and append-only progress events."""

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
                task_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, payload_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed','cancelled')),
                attempts INTEGER NOT NULL DEFAULT 0, lease_token TEXT, lease_until REAL,
                created_at REAL NOT NULL, updated_at REAL NOT NULL, error TEXT,
                progress_percent INTEGER NOT NULL DEFAULT 0, progress_message TEXT NOT NULL DEFAULT 'Queued',
                cancel_requested_at REAL
            )""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(task_queue)")}
            if "progress_percent" not in columns:
                db.execute("ALTER TABLE task_queue ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0")
            if "progress_message" not in columns:
                db.execute("ALTER TABLE task_queue ADD COLUMN progress_message TEXT NOT NULL DEFAULT 'Queued'")
            if "cancel_requested_at" not in columns:
                db.execute("ALTER TABLE task_queue ADD COLUMN cancel_requested_at REAL")
            db.execute("CREATE INDEX IF NOT EXISTS task_queue_claim_idx ON task_queue(status, created_at)")
            db.execute("""CREATE TABLE IF NOT EXISTS task_progress_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                owner_id TEXT NOT NULL, status TEXT NOT NULL, progress_percent INTEGER NOT NULL,
                message TEXT NOT NULL, created_at REAL NOT NULL
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS task_progress_owner_idx ON task_progress_events(task_id, owner_id, event_id)")

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
                         row["attempts"], row["lease_token"], row["lease_until"],
                         row["progress_percent"], row["progress_message"],
                         row["cancel_requested_at"] is not None)

    @staticmethod
    def _event(db, task_id, owner_id, status, percent, message, now):
        db.execute("""INSERT INTO task_progress_events
            (task_id,owner_id,status,progress_percent,message,created_at) VALUES(?,?,?,?,?,?)""",
            (task_id, owner_id, status, percent, message[:300], now))

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
                db.execute("""INSERT INTO task_queue
                    (task_id,owner_id,payload_json,status,created_at,updated_at)
                    VALUES(?,?,?,'queued',?,?)""", (task_id.strip(), owner_id, encoded, now, now))
            except sqlite3.IntegrityError as exc:
                raise ValueError("task already exists in queue") from exc
            self._event(db, task_id.strip(), owner_id, "queued", 0, "Waiting for a worker", now)
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
            expired = db.execute("""SELECT task_id,owner_id,attempts FROM task_queue
                WHERE status='running' AND lease_until <= ?""", (now,)).fetchall()
            db.execute("""UPDATE task_queue SET status=CASE WHEN attempts >= ? THEN 'failed' ELSE 'queued' END,
                lease_token=NULL, lease_until=NULL, updated_at=?,
                error=CASE WHEN attempts >= ? THEN 'Worker lease expired; retry limit reached.' ELSE error END,
                progress_message=CASE WHEN attempts >= ? THEN 'Worker lease expired; retry limit reached.' ELSE 'Retrying after worker lease expiry' END
                WHERE status='running' AND lease_until <= ?""",
                (self.max_attempts, now, self.max_attempts, self.max_attempts, now))
            for item in expired:
                status = "failed" if item["attempts"] >= self.max_attempts else "queued"
                self._event(db, item["task_id"], item["owner_id"], status, 0,
                            "Worker lease expired; task failed" if status == "failed" else "Retrying after worker lease expiry", now)
            row = db.execute("SELECT * FROM task_queue WHERE status='queued' ORDER BY created_at, task_id LIMIT 1").fetchone()
            if row is None:
                db.commit()
                return None
            token = uuid4().hex
            updated = db.execute("""UPDATE task_queue SET status='running', attempts=attempts+1,
                lease_token=?, lease_until=?, updated_at=?, progress_percent=5, progress_message='Worker started'
                WHERE task_id=? AND status='queued'""", (token, now + lease_seconds, now, row["task_id"]))
            if updated.rowcount != 1:
                db.rollback()
                return None
            self._event(db, row["task_id"], row["owner_id"], "running", 5, "Worker started", now)
            claimed = db.execute("SELECT * FROM task_queue WHERE task_id=?", (row["task_id"],)).fetchone()
            db.commit()
        return self._item(claimed)

    def renew_lease(self, task_id: str, lease_token: str, *, lease_seconds: int = 300) -> bool:
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool) or not 5 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 5 and 3600")
        now = time.time()
        with self._connect() as db:
            cursor = db.execute("""UPDATE task_queue SET lease_until=?, updated_at=?
                WHERE task_id=? AND status='running' AND lease_token=?""",
                (now + lease_seconds, now, task_id, lease_token))
            return cursor.rowcount == 1

    def request_cancel(self, task_id: str, owner_id: str) -> str:
        now = time.time()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT status,progress_percent,cancel_requested_at FROM task_queue
                WHERE task_id=? AND owner_id=?""", (task_id, owner_id)).fetchone()
            if row is None:
                db.commit()
                return "not_found"
            if row["status"] == "queued":
                db.execute("""UPDATE task_queue SET status='cancelled',updated_at=?,
                    progress_message='Cancelled before execution' WHERE task_id=? AND owner_id=? AND status='queued'""",
                    (now, task_id, owner_id))
                self._event(db, task_id, owner_id, "cancelled", row["progress_percent"], "Cancelled before execution", now)
                db.commit()
                return "cancelled"
            if row["status"] == "running":
                if row["cancel_requested_at"] is None:
                    db.execute("""UPDATE task_queue SET cancel_requested_at=?,updated_at=?,
                        progress_message='Cancellation requested' WHERE task_id=? AND owner_id=? AND status='running'""",
                        (now, now, task_id, owner_id))
                    self._event(db, task_id, owner_id, "running", row["progress_percent"], "Cancellation requested", now)
                db.commit()
                return "requested"
            db.commit()
            return "terminal"

    def is_cancel_requested(self, task_id: str, lease_token: str) -> bool:
        with self._connect() as db:
            row = db.execute("""SELECT cancel_requested_at FROM task_queue
                WHERE task_id=? AND status='running' AND lease_token=?""",
                (task_id, lease_token)).fetchone()
        return row is not None and row["cancel_requested_at"] is not None

    def report_progress(self, task_id: str, lease_token: str, progress_percent: int, message: str) -> bool:
        if not isinstance(progress_percent, int) or isinstance(progress_percent, bool) or not 0 <= progress_percent <= 99:
            raise ValueError("progress_percent must be between 0 and 99")
        if not isinstance(message, str) or not message.strip() or len(message) > 300:
            raise ValueError("progress message must contain 1 to 300 characters")
        now = time.time()
        with self._connect() as db:
            row = db.execute("""SELECT owner_id,progress_percent,cancel_requested_at FROM task_queue
                WHERE task_id=? AND status='running' AND lease_token=?""", (task_id, lease_token)).fetchone()
            if row is None or progress_percent < row["progress_percent"]:
                return False
            db.execute("""UPDATE task_queue SET progress_percent=?, progress_message=?, updated_at=?
                WHERE task_id=? AND status='running' AND lease_token=?""",
                (progress_percent, message, now, task_id, lease_token))
            self._event(db, task_id, row["owner_id"], "running", progress_percent, message, now)
            return True

    def complete(self, task_id: str, lease_token: str, *, succeeded: bool, error: str | None = None, cancelled: bool = False) -> bool:
        if not isinstance(succeeded, bool):
            raise TypeError("succeeded must be a boolean")
        if not isinstance(cancelled, bool):
            raise TypeError("cancelled must be a boolean")
        status = "cancelled" if cancelled else ("succeeded" if succeeded else "failed")
        safe_error = error[:500] if isinstance(error, str) else None
        now = time.time()
        message = "Task cancelled cooperatively" if cancelled else ("Task completed" if succeeded else "Task failed")
        with self._connect() as db:
            row = db.execute("""SELECT owner_id,progress_percent,cancel_requested_at FROM task_queue
                WHERE task_id=? AND status='running' AND lease_token=?""", (task_id, lease_token)).fetchone()
            if row is None:
                return False
            if row["cancel_requested_at"] is not None:
                cancelled = True
                status = "cancelled"
                message = "Task cancelled cooperatively"
            percent = 100 if succeeded and not cancelled else row["progress_percent"]
            cursor = db.execute("""UPDATE task_queue SET status=?, error=?, lease_token=NULL,
                lease_until=NULL, updated_at=?, progress_percent=?, progress_message=?, cancel_requested_at=NULL
                WHERE task_id=? AND status='running' AND lease_token=?""",
                (status, safe_error, now, percent, message, task_id, lease_token))
            if cursor.rowcount == 1:
                self._event(db, task_id, row["owner_id"], status, percent, message, now)
                return True
            return False

    def cancel(self, task_id: str, owner_id: str) -> bool:
        """Backward-compatible queued-only cancellation helper."""
        return self.request_cancel(task_id, owner_id) == "cancelled"

    def get(self, task_id: str, owner_id: str) -> QueueItem | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM task_queue WHERE task_id=? AND owner_id=?", (task_id, owner_id)).fetchone()
        return self._item(row) if row else None

    def list_events(self, task_id: str, owner_id: str, *, limit: int = 50) -> list[dict]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        with self._connect() as db:
            rows = db.execute("""SELECT event_id,status,progress_percent,message,created_at
                FROM task_progress_events WHERE task_id=? AND owner_id=?
                ORDER BY event_id DESC LIMIT ?""", (task_id, owner_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]
