"""User accounts and revocable opaque sessions backed by SQLite.

This module stores password verifiers and hashes of session tokens, never raw
passwords or bearer tokens. Deploy behind TLS and add abuse controls before
opening self-service registration to the public.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from pathlib import Path

_PASSWORD_ITERATIONS = 310_000
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AuthenticationError(ValueError):
    """Raised when credentials or a session cannot be authenticated."""


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str


class SQLiteAuthStore:
    """SQLite-backed user registry and hashed, expiring bearer sessions."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("a file-backed database is required")
        Path(self.database_path).expanduser().resolve().parent.mkdir(
            parents=True, exist_ok=True
        )
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    created_at INTEGER NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS sessions (
                    token_hash BLOB PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id),
                    expires_at INTEGER NOT NULL,
                    revoked_at INTEGER
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id)"
            )

    @staticmethod
    def _password_verifier(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
        )

    def register_user(self, email: str, password: str) -> AuthenticatedUser:
        if not isinstance(email, str) or not _EMAIL_RE.fullmatch(email.strip()):
            raise ValueError("a valid email address is required")
        normalized_email = email.strip().casefold()
        if not isinstance(password, str) or len(password) < 12 or len(password) > 256:
            raise ValueError("password must be between 12 and 256 characters")
        user_id = secrets.token_urlsafe(18)
        salt = secrets.token_bytes(16)
        verifier = self._password_verifier(password, salt)
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO users
                    (user_id, email, password_salt, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (user_id, normalized_email, salt, verifier, int(time.time())),
                )
        except sqlite3.IntegrityError:
            raise ValueError("email is already registered") from None
        return AuthenticatedUser(user_id=user_id, email=normalized_email)

    def authenticate(self, email: str, password: str) -> AuthenticatedUser:
        if not isinstance(email, str) or not isinstance(password, str):
            raise AuthenticationError("invalid email or password")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT user_id, email, password_salt, password_hash FROM users WHERE email = ?",
                (email.strip().casefold(),),
            ).fetchone()
        if row is None:
            # Perform a fixed-cost derivation to reduce account-enumeration timing differences.
            self._password_verifier(password, b"ajusta-fixed-salt")
            raise AuthenticationError("invalid email or password")
        candidate = self._password_verifier(password, row["password_salt"])
        if not hmac.compare_digest(candidate, row["password_hash"]):
            raise AuthenticationError("invalid email or password")
        return AuthenticatedUser(user_id=row["user_id"], email=row["email"])

    def create_session(self, user_id: str, *, ttl_seconds: int = 86_400) -> str:
        if not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= 2_592_000:
            raise ValueError("session lifetime must be between 1 second and 30 days")
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode("utf-8")).digest()
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if exists is None:
                raise ValueError("user does not exist")
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_hash, user_id, int(time.time()) + ttl_seconds),
            )
        return token

    def resolve_session(self, token: str) -> AuthenticatedUser:
        if not isinstance(token, str) or not token:
            raise AuthenticationError("invalid or expired session")
        token_hash = hashlib.sha256(token.encode("utf-8")).digest()
        now = int(time.time())
        with self._connect() as connection:
            row = connection.execute(
                """SELECT users.user_id, users.email, sessions.expires_at,
                          sessions.revoked_at
                   FROM sessions JOIN users USING(user_id)
                   WHERE sessions.token_hash = ?""",
                (token_hash,),
            ).fetchone()
            if row is None or row["revoked_at"] is not None or row["expires_at"] <= now:
                if row is not None and row["expires_at"] <= now:
                    connection.execute(
                        "DELETE FROM sessions WHERE token_hash = ?", (token_hash,)
                    )
                raise AuthenticationError("invalid or expired session")
        return AuthenticatedUser(user_id=row["user_id"], email=row["email"])

    def revoke_session(self, token: str) -> bool:
        if not isinstance(token, str) or not token:
            return False
        token_hash = hashlib.sha256(token.encode("utf-8")).digest()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (int(time.time()), token_hash),
            )
        return cursor.rowcount == 1
