"""Governed execution for statically registered, reviewed AJUSTA skills.

This is not a general-purpose code sandbox. It never imports code from a skill,
evaluates strings, invokes a shell, or executes model-generated code. Operations
must be trusted application callables registered by the host application.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Callable
from uuid import uuid4

from .skills import SkillStatus, SkillValidationError
from .skill_store import SQLiteSkillStore


class SkillExecutionDenied(PermissionError):
    """Raised when an execution request fails a governance check."""


@dataclass(frozen=True)
class SkillExecutionResult:
    execution_id: str
    skill_name: str
    skill_version: str
    status: str
    output: Any = None


class SQLiteSkillAuditStore:
    """Persist minimal execution metadata; never store input/output secrets."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("a file-backed database is required for audit records")
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS skill_execution_audit (
                    execution_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    skill_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output_sha256 TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS skill_audit_user_created_idx
                ON skill_execution_audit(user_id, created_at DESC)
            """)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def record(self, *, execution_id: str, user_id: str, skill_name: str,
               skill_version: str, status: str, output: Any = None,
               error_code: str | None = None) -> None:
        digest = None
        if status == "succeeded":
            encoded = json.dumps(output, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False).encode("utf-8")
            digest = hashlib.sha256(encoded).hexdigest()
        with self._connect() as db:
            db.execute("""
                INSERT INTO skill_execution_audit
                (execution_id,user_id,skill_name,skill_version,status,output_sha256,error_code,created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (execution_id, user_id, skill_name, skill_version, status,
                  digest, error_code, datetime.now(timezone.utc).isoformat()))


class SkillExecutionEngine:
    """Run active skills only through host-registered callable operations."""

    _APPROVAL_SCOPES = frozenset({
        "external.write", "network.write", "system.execute", "account.modify",
    })

    def __init__(self, *, skill_store: SQLiteSkillStore,
                 audit_store: SQLiteSkillAuditStore) -> None:
        if not isinstance(skill_store, SQLiteSkillStore):
            raise TypeError("skill_store must be a SQLiteSkillStore")
        if not isinstance(audit_store, SQLiteSkillAuditStore):
            raise TypeError("audit_store must be a SQLiteSkillAuditStore")
        self._skills = skill_store
        self._audit = audit_store
        self._operations: dict[tuple[str, str], Callable[[dict[str, Any]], Any]] = {}

    def register_operation(self, name: str, version: str,
                           operation: Callable[[dict[str, Any]], Any]) -> None:
        """Register trusted host code; skill manifests cannot supply callables."""
        if not callable(operation):
            raise TypeError("operation must be callable")
        key = (name, version)
        if key in self._operations:
            raise SkillValidationError("operation is already registered")
        self._operations[key] = operation

    @staticmethod
    def _matches_type(value: Any, expected: str) -> bool:
        checks = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "null": lambda v: v is None,
        }
        return expected not in checks or checks[expected](value)

    @classmethod
    def _validate_schema(cls, value: Any, schema: dict[str, Any], label: str) -> None:
        if not isinstance(schema, dict):
            raise SkillValidationError(f"{label} schema must be an object")
        expected = schema.get("type")
        if expected and not cls._matches_type(value, expected):
            raise SkillValidationError(f"{label} must be of type {expected}")
        if expected == "object":
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            if not isinstance(properties, dict) or not isinstance(required, list):
                raise SkillValidationError(f"{label} schema is invalid")
            missing = [key for key in required if key not in value]
            if missing:
                raise SkillValidationError(f"{label} is missing required fields")
            if schema.get("additionalProperties") is False:
                if set(value) - set(properties):
                    raise SkillValidationError(f"{label} contains unknown fields")
            for key, child_schema in properties.items():
                if key in value:
                    cls._validate_schema(value[key], child_schema, f"{label}.{key}")
        if expected == "array" and "items" in schema:
            for index, item in enumerate(value):
                cls._validate_schema(item, schema["items"], f"{label}[{index}]")

    def execute(self, *, name: str, version: str, user_id: str,
                inputs: dict[str, Any], granted_permissions: set[str] | frozenset[str],
                approved_by_user: bool = False) -> SkillExecutionResult:
        if not isinstance(user_id, str) or not user_id.strip():
            raise SkillExecutionDenied("an authenticated user is required")
        if not isinstance(inputs, dict):
            raise SkillValidationError("skill inputs must be an object")
        if any(key.startswith("_ajusta_") for key in inputs):
            raise SkillValidationError("input contains a reserved AJUSTA context field")
        if not isinstance(granted_permissions, (set, frozenset)):
            raise TypeError("granted_permissions must be a set or frozenset")

        skill = self._skills.get(name, version)
        if skill.status is not SkillStatus.ACTIVE:
            raise SkillExecutionDenied("only active skills can execute")
        required = set(skill.permissions)
        if not required.issubset(granted_permissions):
            raise SkillExecutionDenied("required skill permissions were not granted")
        if required.intersection(self._APPROVAL_SCOPES) and not approved_by_user:
            raise SkillExecutionDenied("explicit user approval is required for this permission scope")

        operation = self._operations.get((name, skill.version))
        if operation is None:
            raise SkillExecutionDenied("no trusted host operation is registered for this skill")
        self._validate_schema(inputs, skill.manifest.input_schema, "input")

        execution_id = uuid4().hex
        try:
            operation_inputs = dict(inputs)
            operation_inputs["_ajusta_user_id"] = user_id
            output = operation(operation_inputs)
            # Ensure results are JSON-safe and bounded before exposing or auditing them.
            encoded = json.dumps(output, ensure_ascii=False, allow_nan=False)
            if len(encoded) > 100_000:
                raise SkillValidationError("skill output exceeds the 100000-character limit")
            self._validate_schema(output, skill.manifest.output_schema, "output")
        except Exception as exc:
            self._audit.record(
                execution_id=execution_id, user_id=user_id, skill_name=name,
                skill_version=skill.version, status="failed",
                error_code=type(exc).__name__[:80],
            )
            raise

        self._audit.record(
            execution_id=execution_id, user_id=user_id, skill_name=name,
            skill_version=skill.version, status="succeeded", output=output,
        )
        return SkillExecutionResult(
            execution_id=execution_id, skill_name=name,
            skill_version=skill.version, status="succeeded", output=output,
        )
