"""Job metadata store: attach arbitrary key-value pairs to jobs and persist them."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class JobMetadata:
    """Holds metadata entries for a single job."""

    job_name: str
    entries: Dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.entries.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.entries[key] = value

    def remove(self, key: str) -> None:
        self.entries.pop(key, None)

    def __len__(self) -> int:
        return len(self.entries)


class MetadataStore:
    """Persists job metadata in a SQLite database."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = self._connect()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_metadata (
                job_name TEXT NOT NULL,
                key      TEXT NOT NULL,
                value    TEXT NOT NULL,
                PRIMARY KEY (job_name, key)
            )
            """
        )
        self._conn.commit()

    def save(self, metadata: JobMetadata) -> None:
        """Persist all entries for a job (upsert)."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM job_metadata WHERE job_name = ?", (metadata.job_name,)
            )
            self._conn.executemany(
                "INSERT INTO job_metadata (job_name, key, value) VALUES (?, ?, ?)",
                [(metadata.job_name, k, v) for k, v in metadata.entries.items()],
            )

    def load(self, job_name: str) -> JobMetadata:
        """Load metadata for a job; returns empty JobMetadata if not found."""
        rows = self._conn.execute(
            "SELECT key, value FROM job_metadata WHERE job_name = ?", (job_name,)
        ).fetchall()
        return JobMetadata(job_name=job_name, entries={r["key"]: r["value"] for r in rows})

    def delete(self, job_name: str) -> None:
        """Remove all metadata for a job."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM job_metadata WHERE job_name = ?", (job_name,)
            )

    def all_job_names(self) -> list[str]:
        """Return names of all jobs that have stored metadata."""
        rows = self._conn.execute(
            "SELECT DISTINCT job_name FROM job_metadata ORDER BY job_name"
        ).fetchall()
        return [r["job_name"] for r in rows]
