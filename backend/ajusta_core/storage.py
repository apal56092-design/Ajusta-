"""Small durable SQLite task store; suitable for local development and tests."""
from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from .contracts import TaskRequest, TaskResult, TaskStatus


@dataclass(frozen=True)
class StoredTask:
    task_id: str
    instruction: str
    status: TaskStatus
    result: str | None
    evidence: tuple[str, ...]
    error_code: str | None
    error_message: str | None


class SQLiteTaskStore:
    """Persist task requests and outcomes in a file-backed SQLite database.

    Each operation opens and closes its own connection, allowing separate store
    instances to access the same database without sharing connection state.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("a file-backed database is required for durable storage")
        Path(self.database_path).expanduser().resolve().parent.mkdir(
            parents=True, exist_ok=True
        )
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    instruction TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def create_task(self, task_id: str, request: TaskRequest) -> None:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        if not isinstance(request, TaskRequest):
            raise TypeError("request must be a TaskRequest")
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO tasks (task_id, instruction, status)
                    VALUES (?, ?, ?)
                    """,
                    (task_id.strip(), request.instruction, TaskStatus.QUEUED.value),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"task {task_id!r} already exists") from exc

    def save_result(self, result: TaskResult) -> None:
        if not isinstance(result, TaskResult):
            raise TypeError("result must be a TaskResult")
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET status = ?, result = ?, evidence_json = ?, error_code = ?,
                    error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
                """,
                (
                    result.status.value,
                    result.result,
                    json.dumps(result.evidence),
                    result.error_code,
                    result.error_message,
                    result.task_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"task {result.task_id!r} does not exist")

    def get_task(self, task_id: str) -> StoredTask | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT task_id, instruction, status, result, evidence_json,
                       error_code, error_message
                FROM tasks WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        evidence = json.loads(row["evidence_json"])
        if not isinstance(evidence, list) or any(
            not isinstance(item, str) for item in evidence
        ):
            raise ValueError("stored task evidence is invalid")
        return StoredTask(
            task_id=row["task_id"],
            instruction=row["instruction"],
            status=TaskStatus(row["status"]),
            result=row["result"],
            evidence=tuple(evidence),
            error_code=row["error_code"],
            error_message=row["error_message"],
        )
