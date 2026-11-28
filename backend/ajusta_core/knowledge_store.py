"""User-owned persistent knowledge records with explicit provenance metadata.

Records are saved knowledge, not model training. Provenance and confidence are
user-supplied annotations and are never treated as independent truth verification.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from uuid import uuid4


@dataclass(frozen=True)
class KnowledgeRecord:
    id: str
    user_id: str
    title: str
    content: str
    created_at: str
    source: str | None = None
    confidence: float | None = None


class SQLiteKnowledgeStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path == ":memory:":
            raise ValueError("a file-backed database is required for persistent knowledge")
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_records (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    source TEXT,
                    confidence REAL
                )
            """)
            # Forward-only, additive migration for databases created by earlier AJUSTA versions.
            columns = {row["name"] for row in connection.execute(
                "PRAGMA table_info(knowledge_records)"
            ).fetchall()}
            if "source" not in columns:
                connection.execute("ALTER TABLE knowledge_records ADD COLUMN source TEXT")
            if "confidence" not in columns:
                connection.execute("ALTER TABLE knowledge_records ADD COLUMN confidence REAL")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS knowledge_owner_created_idx "
                "ON knowledge_records(user_id, created_at DESC, id)"
            )
            connection.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    id UNINDEXED, user_id UNINDEXED, title, content,
                    tokenize='unicode61'
                )
            """)
            connection.executescript("""
                CREATE TRIGGER IF NOT EXISTS knowledge_fts_insert
                AFTER INSERT ON knowledge_records BEGIN
                    INSERT INTO knowledge_fts(id,user_id,title,content)
                    VALUES(new.id,new.user_id,new.title,new.content);
                END;
                CREATE TRIGGER IF NOT EXISTS knowledge_fts_delete
                AFTER DELETE ON knowledge_records BEGIN
                    DELETE FROM knowledge_fts WHERE id=old.id;
                END;
                CREATE TRIGGER IF NOT EXISTS knowledge_fts_update
                AFTER UPDATE ON knowledge_records BEGIN
                    DELETE FROM knowledge_fts WHERE id=old.id;
                    INSERT INTO knowledge_fts(id,user_id,title,content)
                    VALUES(new.id,new.user_id,new.title,new.content);
                END;
            """)
            indexed = connection.execute("SELECT COUNT(*) FROM knowledge_fts").fetchone()[0]
            if indexed == 0:
                connection.execute("""
                    INSERT INTO knowledge_fts(id,user_id,title,content)
                    SELECT id,user_id,title,content FROM knowledge_records
                """)

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> KnowledgeRecord:
        return KnowledgeRecord(
            id=row["id"], user_id=row["user_id"], title=row["title"],
            content=row["content"], created_at=row["created_at"],
            source=row["source"], confidence=row["confidence"],
        )

    def create(
        self, user_id: str, title: str, content: str, *,
        source: str | None = None, confidence: float | None = None,
    ) -> KnowledgeRecord:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id is required")
        if not isinstance(title, str) or not isinstance(content, str):
            raise TypeError("title and content must be strings")
        title = title.strip()
        content = content.strip()
        if not title or len(title) > 160:
            raise ValueError("title must contain 1 to 160 characters")
        if not content or len(content) > 20000:
            raise ValueError("content must contain 1 to 20000 characters")
        if source is not None and (
            not isinstance(source, str) or not source.strip() or len(source.strip()) > 500
        ):
            raise ValueError("source must contain 1 to 500 characters when provided")
        if confidence is not None and (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError("confidence must be a number between 0 and 1")
        source = source.strip() if source is not None else None
        confidence = float(confidence) if confidence is not None else None
        record_id = uuid4().hex
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO knowledge_records(id,user_id,title,content,source,confidence) "
                "VALUES(?,?,?,?,?,?)",
                (record_id, user_id.strip(), title, content, source, confidence),
            )
            row = connection.execute(
                "SELECT * FROM knowledge_records WHERE id=?", (record_id,)
            ).fetchone()
        return self._record(row)

    def list_for_user(self, user_id: str) -> tuple[KnowledgeRecord, ...]:
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id is required")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_records WHERE user_id=? "
                "ORDER BY created_at DESC, id DESC", (user_id,)
            ).fetchall()
        return tuple(self._record(row) for row in rows)

    def search_for_user(
        self, user_id: str, query: str, *, limit: int = 20
    ) -> tuple[KnowledgeRecord, ...]:
        """Search title and content with FTS5 while enforcing owner isolation."""
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id is required")
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        terms = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
        if not terms:
            raise ValueError("query must contain searchable words")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        match_query = " AND ".join('"' + term.replace('"', '""') + '"' for term in terms[:12])
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT records.*
                FROM knowledge_fts
                JOIN knowledge_records AS records ON records.id = knowledge_fts.id
                WHERE knowledge_fts MATCH ? AND records.user_id = ?
                ORDER BY bm25(knowledge_fts), records.created_at DESC
                LIMIT ?
                """,
                (match_query, user_id, limit),
            ).fetchall()
        return tuple(self._record(row) for row in rows)

    def delete(self, user_id: str, record_id: str) -> bool:
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("user_id is required")
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM knowledge_records WHERE id=? AND user_id=?",
                (record_id, user_id),
            )
        return cursor.rowcount == 1
