"""Durable SQLite catalog for reviewed AJUSTA skill manifests.

This catalog stores declarative metadata only. It never imports or executes skill code.
"""
from contextlib import contextmanager
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from .skills import (
    RegisteredSkill,
    SkillManifest,
    SkillStatus,
    SkillValidationError,
    validate_manifest,
)


class SQLiteSkillStore:
    """Persist skill versions and lifecycle state with explicit review gates."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("a file-backed database is required for durable skill storage")
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
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
                """CREATE TABLE IF NOT EXISTS skills (
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT NOT NULL,
                    input_schema_json TEXT NOT NULL,
                    output_schema_json TEXT NOT NULL,
                    permissions_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (name, version)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS skills_status_idx ON skills(status)"
            )

    @staticmethod
    def _decode(row: sqlite3.Row) -> RegisteredSkill:
        try:
            manifest = SkillManifest(
                name=row["name"],
                version=row["version"],
                description=row["description"],
                input_schema=json.loads(row["input_schema_json"]),
                output_schema=json.loads(row["output_schema_json"]),
                permissions=tuple(json.loads(row["permissions_json"])),
            )
            validate_manifest(manifest)
            return RegisteredSkill(manifest=manifest, status=SkillStatus(row["status"]))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError("stored skill record is invalid") from exc

    def register(self, manifest: SkillManifest) -> RegisteredSkill:
        validate_manifest(manifest)
        try:
            input_schema = json.dumps(manifest.input_schema, sort_keys=True)
            output_schema = json.dumps(manifest.output_schema, sort_keys=True)
            permissions = json.dumps(list(manifest.permissions))
        except (TypeError, ValueError) as exc:
            raise SkillValidationError("skill schemas must contain JSON-compatible values") from exc
        try:
            with self._connection() as connection:
                connection.execute(
                    """INSERT INTO skills
                       (name,version,description,input_schema_json,output_schema_json,permissions_json,status)
                       VALUES (?,?,?,?,?,?,?)""",
                    (manifest.name, manifest.version, manifest.description,
                     input_schema, output_schema, permissions, SkillStatus.DRAFT.value),
                )
        except sqlite3.IntegrityError as exc:
            raise SkillValidationError("skill version is already registered") from exc
        return RegisteredSkill(manifest=manifest, status=SkillStatus.DRAFT)

    def get(self, name: str, version: str | None = None) -> RegisteredSkill:
        with self._connection() as connection:
            if version is None:
                row = connection.execute(
                    "SELECT * FROM skills WHERE name=? ORDER BY version DESC LIMIT 1", (name,)
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM skills WHERE name=? AND version=?", (name, version)
                ).fetchone()
        if row is None:
            raise KeyError(f"skill not found: {name}")
        return self._decode(row)

    def list_skills(self, *, status: SkillStatus | None = None) -> tuple[RegisteredSkill, ...]:
        with self._connection() as connection:
            if status is None:
                rows = connection.execute("SELECT * FROM skills ORDER BY name, version").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM skills WHERE status=? ORDER BY name, version", (status.value,)
                ).fetchall()
        return tuple(self._decode(row) for row in rows)

    def _transition(
        self,
        name: str,
        version: str | None,
        *,
        allowed: tuple[SkillStatus, ...],
        target: SkillStatus,
    ) -> RegisteredSkill:
        current = self.get(name, version)
        if current.status not in allowed:
            if target is SkillStatus.ACTIVE:
                raise SkillValidationError("skill must be approved before activation")
            if target is SkillStatus.APPROVED:
                raise SkillValidationError("only draft or disabled skills can be reviewed")
            raise SkillValidationError("only active skills can be disabled")
        with self._connection() as connection:
            cursor = connection.execute(
                """UPDATE skills SET status=?, updated_at=CURRENT_TIMESTAMP
                   WHERE name=? AND version=? AND status=?""",
                (target.value, current.name, current.version, current.status.value),
            )
            if cursor.rowcount != 1:
                raise SkillValidationError("skill changed concurrently; reload before retrying")
        return replace(current, status=target)

    def approve(self, name: str, version: str | None = None) -> RegisteredSkill:
        return self._transition(
            name, version,
            allowed=(SkillStatus.DRAFT, SkillStatus.DISABLED),
            target=SkillStatus.APPROVED,
        )

    def activate(self, name: str, version: str | None = None) -> RegisteredSkill:
        return self._transition(
            name, version,
            allowed=(SkillStatus.APPROVED,),
            target=SkillStatus.ACTIVE,
        )

    def disable(self, name: str, version: str | None = None) -> RegisteredSkill:
        return self._transition(
            name, version,
            allowed=(SkillStatus.ACTIVE,),
            target=SkillStatus.DISABLED,
        )
