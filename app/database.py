"""SQLite persistence layer for the digital registry."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


@dataclass
class DocumentRecord:
    """Persistence representation for a registry document.

    Attributes:
        document_id: Stable public identifier (integer auto-increment).
        entry_date: Registry entry date.
        sender: Document sender.
        subject: Document subject.
        file_path: Absolute or container-local file path.
        original_filename: Original uploaded filename.
        file_size: Final file size in bytes.
        tags: Flat list of tags associated with the document.
        created_at: Creation timestamp (UTC, ISO-8601).
    """

    document_id: int | None
    entry_date: date
    sender: str
    subject: str
    file_path: str
    original_filename: str
    file_size: int
    tags: list[str]
    created_at: str


class Database:
    """Repository abstraction over SQLite operations.

    The schema is normalized as follows:
    - 1NF: atomic fields and no repeating groups in each table.
    - 2NF: many-to-many tags are moved to bridge table document_tags,
      avoiding partial dependency on composite keys.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize the repository with a SQLite database path.

        Args:
            db_path: Path to the SQLite database file.
        """

        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection configured with row factory."""

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    def initialize(self) -> None:
        """Create relational tables and indexes if they do not exist."""

        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_date TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS document_tags (
                    document_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (document_id, tag_id),
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_documents_entry_date ON documents(entry_date);
                CREATE INDEX IF NOT EXISTS idx_documents_sender ON documents(sender);
                CREATE INDEX IF NOT EXISTS idx_documents_subject ON documents(subject);
                CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
                """
            )

    def insert_document(self, record: DocumentRecord) -> None:
        """Persist one document and all associated tags.

        Args:
            record: Complete document payload.
        """

        normalized_tags = sorted({tag.strip().lower() for tag in record.tags if tag.strip()})

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO documents (
                    entry_date, sender, subject, file_path, original_filename, file_size, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.entry_date.isoformat(),
                    record.sender,
                    record.subject,
                    record.file_path,
                    record.original_filename,
                    record.file_size,
                    record.created_at,
                ),
            )
            
            record.document_id = cursor.lastrowid

            for tag in normalized_tags:
                conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,))
                conn.execute(
                    """
                    INSERT OR IGNORE INTO document_tags(document_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                    """,
                    (record.document_id, tag),
                )

    def search_documents(
        self,
        date_from: date | None,
        date_to: date | None,
        sender: str | None,
        subject: str | None,
        tag: str | None,
    ) -> list[DocumentRecord]:
        """Search documents using optional filters.

        Args:
            date_from: Inclusive start date filter.
            date_to: Inclusive end date filter.
            sender: Case-insensitive sender substring filter.
            subject: Case-insensitive subject substring filter.
            tag: Exact normalized tag filter.

        Returns:
            list[DocumentRecord]: Filtered document records.
        """

        conditions: list[str] = []
        params: list[str] = []

        base_query = """
            SELECT d.*, GROUP_CONCAT(t.name, ', ') AS tag_list
            FROM documents d
            LEFT JOIN document_tags dt ON d.id = dt.document_id
            LEFT JOIN tags t ON t.id = dt.tag_id
        """

        if date_from:
            conditions.append("d.entry_date >= ?")
            params.append(date_from.isoformat())
        if date_to:
            conditions.append("d.entry_date <= ?")
            params.append(date_to.isoformat())
        if sender:
            conditions.append("LOWER(d.sender) LIKE ?")
            params.append(f"%{sender.lower()}%")
        if subject:
            conditions.append("LOWER(d.subject) LIKE ?")
            params.append(f"%{subject.lower()}%")
        if tag:
            conditions.append(
                "d.id IN (SELECT document_id FROM document_tags dt2 JOIN tags t2 ON t2.id = dt2.tag_id WHERE t2.name = ?)"
            )
            params.append(tag.strip().lower())

        query_parts = [base_query]
        if conditions:
            query_parts.append("WHERE " + " AND ".join(conditions))
        query_parts.append("GROUP BY d.id")
        query_parts.append("ORDER BY d.entry_date DESC, d.created_at DESC")

        query = "\n".join(query_parts)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            DocumentRecord(
                document_id=int(row["id"]),
                entry_date=date.fromisoformat(row["entry_date"]),
                sender=row["sender"],
                subject=row["subject"],
                file_path=row["file_path"],
                original_filename=row["original_filename"],
                file_size=int(row["file_size"]),
                tags=[tag.strip() for tag in (row["tag_list"] or "").split(",") if tag.strip()],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_document_by_id(self, document_id: int) -> DocumentRecord | None:
        """Return one document with tags by its identifier.

        Args:
            document_id: Unique document identifier.

        Returns:
            DocumentRecord | None: Found record or None when missing.
        """

        query = """
            SELECT d.*, GROUP_CONCAT(t.name, ', ') AS tag_list
            FROM documents d
            LEFT JOIN document_tags dt ON d.id = dt.document_id
            LEFT JOIN tags t ON t.id = dt.tag_id
            WHERE d.id = ?
            GROUP BY d.id
        """

        with self._connect() as conn:
            row = conn.execute(query, (document_id,)).fetchone()

        if row is None:
            return None

        return DocumentRecord(
            document_id=int(row["id"]),
            entry_date=date.fromisoformat(row["entry_date"]),
            sender=row["sender"],
            subject=row["subject"],
            file_path=row["file_path"],
            original_filename=row["original_filename"],
            file_size=int(row["file_size"]),
            tags=[tag.strip() for tag in (row["tag_list"] or "").split(",") if tag.strip()],
            created_at=row["created_at"],
        )

    def update_document_fields(
        self,
        document_id: int,
        sender: str,
        subject: str,
        tags: list[str],
    ) -> bool:
        """Update mutable fields of a document record.

        The document_id and entry_date are immutable (audit trail).

        Args:
            document_id: Stable document identifier (immutable).
            sender: New sender value.
            subject: New subject value.
            tags: New tags list.

        Returns:
            bool: True if update succeeded, False if document not found.
        """

        normalized_tags = sorted({tag.strip().lower() for tag in tags if tag.strip()})

        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id FROM documents WHERE id = ?",
                (document_id,),
            )
            if cursor.fetchone() is None:
                return False

            conn.execute(
                "UPDATE documents SET sender = ?, subject = ? WHERE id = ?",
                (sender.strip(), subject.strip(), document_id),
            )

            conn.execute(
                "DELETE FROM document_tags WHERE document_id = ?",
                (document_id,),
            )

            for tag in normalized_tags:
                conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (tag,))
                conn.execute(
                    """
                    INSERT OR IGNORE INTO document_tags(document_id, tag_id)
                    SELECT ?, id FROM tags WHERE name = ?
                    """,
                    (document_id, tag),
                )

            return True


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""

    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
