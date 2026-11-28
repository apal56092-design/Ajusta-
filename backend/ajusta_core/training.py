"""Governed dataset and model-training orchestration for AJUSTA.

The core owns dataset isolation, validation, run lifecycle, and audit-safe metrics.
Actual model optimization is delegated only to explicitly registered host trainers;
this module never evaluates user-supplied code or silently trains on private memory.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import json
import math
from pathlib import Path
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from uuid import uuid4


MAX_DATASET_NAME = 120
MAX_DESCRIPTION = 1000
MAX_EXAMPLE_INPUT = 8000
MAX_EXAMPLE_TARGET = 8000
MAX_SOURCE = 500
MAX_CONFIG_BYTES = 10000
MAX_METRICS = 50


class TrainingRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class TrainingDataset:
    id: str
    user_id: str
    name: str
    description: str
    created_at: str


@dataclass(frozen=True)
class TrainingExample:
    id: str
    dataset_id: str
    user_id: str
    input_text: str
    target_text: str
    source: str | None
    created_at: str


@dataclass(frozen=True)
class TrainingRun:
    id: str
    user_id: str
    dataset_id: str
    trainer_name: str
    status: TrainingRunStatus
    config: Mapping[str, object]
    metrics: Mapping[str, int | float]
    error_code: str | None
    created_at: str
    completed_at: str | None


def _json_object(value: Mapping[str, object], *, label: str, max_bytes: int) -> str:
    if not isinstance(value, Mapping) or len(value) > 100:
        raise ValueError(f"{label} must be a bounded object")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError):
        raise ValueError(f"{label} must contain finite JSON values") from None
    if len(encoded.encode("utf-8")) > max_bytes:
        raise ValueError(f"{label} exceeds the size limit")
    return encoded


class SQLiteTrainingStore:
    """SQLite-backed, per-user datasets, examples, and immutable run summaries."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("a file-backed database is required for persistent training data")
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS training_datasets (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS training_datasets_owner_idx
                    ON training_datasets(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS training_examples (
                    id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL REFERENCES training_datasets(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    target_text TEXT NOT NULL,
                    source TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS training_examples_dataset_idx
                    ON training_examples(user_id, dataset_id, created_at, id);
                CREATE TABLE IF NOT EXISTS training_runs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    trainer_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    error_code TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS training_runs_owner_idx
                    ON training_runs(user_id, created_at DESC);
            """)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _dataset(row: sqlite3.Row) -> TrainingDataset:
        return TrainingDataset(row["id"], row["user_id"], row["name"],
                               row["description"], row["created_at"])

    @staticmethod
    def _example(row: sqlite3.Row) -> TrainingExample:
        return TrainingExample(row["id"], row["dataset_id"], row["user_id"],
                               row["input_text"], row["target_text"],
                               row["source"], row["created_at"])

    @staticmethod
    def _run(row: sqlite3.Row) -> TrainingRun:
        return TrainingRun(
            id=row["id"], user_id=row["user_id"], dataset_id=row["dataset_id"],
            trainer_name=row["trainer_name"], status=TrainingRunStatus(row["status"]),
            config=json.loads(row["config_json"]), metrics=json.loads(row["metrics_json"]),
            error_code=row["error_code"], created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    def create_dataset(
        self, user_id: str, name: str, description: str = ""
    ) -> TrainingDataset:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id is required")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= MAX_DATASET_NAME:
            raise ValueError("dataset name must contain 1 to 120 characters")
        if not isinstance(description, str) or len(description) > MAX_DESCRIPTION:
            raise ValueError("description exceeds the size limit")
        dataset_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO training_datasets(id,user_id,name,description) VALUES(?,?,?,?)",
                (dataset_id, user_id.strip(), name.strip(), description.strip()),
            )
            row = connection.execute(
                "SELECT * FROM training_datasets WHERE id=?", (dataset_id,)
            ).fetchone()
        return self._dataset(row)

    def list_datasets(self, user_id: str) -> tuple[TrainingDataset, ...]:
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id is required")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM training_datasets WHERE user_id=? ORDER BY created_at DESC,id",
                (user_id,),
            ).fetchall()
        return tuple(self._dataset(row) for row in rows)

    def add_example(
        self, user_id: str, dataset_id: str, input_text: str,
        target_text: str, *, source: str | None = None,
    ) -> TrainingExample:
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id is required")
        if not isinstance(input_text, str) or not input_text.strip() or len(input_text) > MAX_EXAMPLE_INPUT:
            raise ValueError("input must contain 1 to 8000 characters")
        if not isinstance(target_text, str) or not target_text.strip() or len(target_text) > MAX_EXAMPLE_TARGET:
            raise ValueError("target must contain 1 to 8000 characters")
        if source is not None and (
            not isinstance(source, str) or not source.strip() or len(source.strip()) > MAX_SOURCE
        ):
            raise ValueError("source must contain 1 to 500 characters")
        example_id = uuid4().hex
        with self._connect() as connection:
            dataset = connection.execute(
                "SELECT id FROM training_datasets WHERE id=? AND user_id=?",
                (dataset_id, user_id),
            ).fetchone()
            if dataset is None:
                raise KeyError("training dataset not found")
            connection.execute(
                "INSERT INTO training_examples(id,dataset_id,user_id,input_text,target_text,source) "
                "VALUES(?,?,?,?,?,?)",
                (example_id, dataset_id, user_id, input_text.strip(),
                 target_text.strip(), source.strip() if source else None),
            )
            row = connection.execute(
                "SELECT * FROM training_examples WHERE id=?", (example_id,)
            ).fetchone()
        return self._example(row)

    def list_examples(self, user_id: str, dataset_id: str) -> tuple[TrainingExample, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM training_examples WHERE user_id=? AND dataset_id=? "
                "ORDER BY created_at,id",
                (user_id, dataset_id),
            ).fetchall()
        return tuple(self._example(row) for row in rows)

    def create_run(
        self, user_id: str, dataset_id: str, trainer_name: str,
        config: Mapping[str, object],
    ) -> TrainingRun:
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id is required")
        if not isinstance(trainer_name, str) or not trainer_name.strip() or len(trainer_name) > 80:
            raise ValueError("trainer_name must contain 1 to 80 characters")
        config_json = _json_object(config, label="config", max_bytes=MAX_CONFIG_BYTES)
        run_id = uuid4().hex
        with self._connect() as connection:
            dataset = connection.execute(
                "SELECT id FROM training_datasets WHERE id=? AND user_id=?",
                (dataset_id, user_id),
            ).fetchone()
            if dataset is None:
                raise KeyError("training dataset not found")
            count = connection.execute(
                "SELECT COUNT(*) FROM training_examples WHERE user_id=? AND dataset_id=?",
                (user_id, dataset_id),
            ).fetchone()[0]
            if count < 2:
                raise ValueError("at least two reviewed examples are required")
            connection.execute(
                "INSERT INTO training_runs(id,user_id,dataset_id,trainer_name,status,config_json) "
                "VALUES(?,?,?,?,?,?)",
                (run_id, user_id, dataset_id, trainer_name.strip(),
                 TrainingRunStatus.RUNNING.value, config_json),
            )
            row = connection.execute("SELECT * FROM training_runs WHERE id=?", (run_id,)).fetchone()
        return self._run(row)

    def finish_run(
        self, user_id: str, run_id: str, *,
        metrics: Mapping[str, int | float] | None = None,
        error_code: str | None = None,
    ) -> TrainingRun:
        if (metrics is None) == (error_code is None):
            raise ValueError("provide exactly one of metrics or error_code")
        metrics = metrics or {}
        if len(metrics) > MAX_METRICS:
            raise ValueError("too many training metrics")
        for key, value in metrics.items():
            if (not isinstance(key, str) or not key or len(key) > 80
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)):
                raise ValueError("metrics must be finite numeric values with bounded names")
        if error_code is not None and (
            not isinstance(error_code, str) or not error_code or len(error_code) > 80
        ):
            raise ValueError("error_code must be a short non-empty code")
        metrics_json = _json_object(metrics, label="metrics", max_bytes=4000)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM training_runs WHERE id=? AND user_id=?",
                (run_id, user_id),
            ).fetchone()
            if row is None:
                raise KeyError("training run not found")
            if row["status"] != TrainingRunStatus.RUNNING.value:
                raise ValueError("training run is already finalized")
            status = TrainingRunStatus.FAILED if error_code else TrainingRunStatus.COMPLETED
            connection.execute(
                "UPDATE training_runs SET status=?,metrics_json=?,error_code=?,"
                "completed_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
                (status.value, metrics_json, error_code, run_id, user_id),
            )
            updated = connection.execute(
                "SELECT * FROM training_runs WHERE id=?", (run_id,)
            ).fetchone()
        return self._run(updated)

    def get_run(self, user_id: str, run_id: str) -> TrainingRun:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM training_runs WHERE id=? AND user_id=?",
                (run_id, user_id),
            ).fetchone()
        if row is None:
            raise KeyError("training run not found")
        return self._run(row)

    def list_runs(self, user_id: str, *, limit: int = 20) -> tuple[TrainingRun, ...]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM training_runs WHERE user_id=? "
                "ORDER BY created_at DESC,id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return tuple(self._run(row) for row in rows)


Trainer = Callable[[Sequence[TrainingExample], Mapping[str, object]], Mapping[str, int | float]]


class TrainingEngine:
    """Runs only trusted host-registered trainers after explicit user approval."""

    def __init__(self, store: SQLiteTrainingStore) -> None:
        if not isinstance(store, SQLiteTrainingStore):
            raise TypeError("store must be SQLiteTrainingStore")
        self.store = store
        self._trainers: dict[str, Trainer] = {}

    def register_trainer(self, name: str, trainer: Trainer) -> None:
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ValueError("trainer name must contain 1 to 80 characters")
        if not callable(trainer):
            raise TypeError("trainer must be a trusted host callable")
        self._trainers[name] = trainer

    def run(
        self, user_id: str, dataset_id: str, *, trainer_name: str,
        config: Mapping[str, object] | None = None, approved: bool = False,
    ) -> TrainingRun:
        if approved is not True:
            raise PermissionError("explicit user approval is required to start training")
        trainer = self._trainers.get(trainer_name)
        if trainer is None:
            raise KeyError("trainer is not registered")
        examples = self.store.list_examples(user_id, dataset_id)
        if len(examples) < 2:
            raise ValueError("at least two reviewed examples are required")
        run = self.store.create_run(user_id, dataset_id, trainer_name, config or {})
        try:
            metrics = trainer(examples, run.config)
            if not isinstance(metrics, Mapping):
                raise ValueError("trainer metrics must be an object")
            return self.store.finish_run(user_id, run.id, metrics=metrics)
        except Exception:
            return self.store.finish_run(user_id, run.id, error_code="trainer_failed")
