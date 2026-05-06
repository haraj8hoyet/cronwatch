"""Persistent job run history using a simple SQLite backend."""

import sqlite3
import contextlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from cronwatch.tracker import JobRun


DEFAULT_DB_PATH = Path("/var/lib/cronwatch/history.db")


class JobHistory:
    """Stores and retrieves historical job run records."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextlib.contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_runs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name    TEXT NOT NULL,
                    started_at  TEXT NOT NULL,
                    finished_at TEXT,
                    exit_code   INTEGER
                )
                """
            )

    def record(self, job_name: str, run: JobRun) -> None:
        """Persist a completed (or in-progress) JobRun to the database."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO job_runs (job_name, started_at, finished_at, exit_code)
                VALUES (?, ?, ?, ?)
                """,
                (
                    job_name,
                    run.started_at.isoformat(),
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.exit_code,
                ),
            )

    def recent(self, job_name: str, limit: int = 10) -> List[dict]:
        """Return the most recent runs for a job as plain dicts."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT job_name, started_at, finished_at, exit_code
                FROM job_runs
                WHERE job_name = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (job_name, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def last_success(self, job_name: str) -> Optional[datetime]:
        """Return the timestamp of the most recent successful run, or None."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT finished_at FROM job_runs
                WHERE job_name = ? AND exit_code = 0
                ORDER BY finished_at DESC
                LIMIT 1
                """,
                (job_name,),
            ).fetchone()
        if row and row["finished_at"]:
            return datetime.fromisoformat(row["finished_at"])
        return None
