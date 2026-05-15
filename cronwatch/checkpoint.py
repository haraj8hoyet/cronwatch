"""Checkpoint tracking — persists the last-seen run timestamp per job
so cronwatch can detect missed runs across daemon restarts.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class CheckpointStore:
    """Persist and retrieve the last-acknowledged run time for each job."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._conn = self._connect()
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                job_name  TEXT PRIMARY KEY,
                last_seen TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, job_name: str, ts: datetime) -> None:
        """Upsert the checkpoint timestamp for *job_name*."""
        iso = ts.astimezone(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO checkpoints (job_name, last_seen)
            VALUES (?, ?)
            ON CONFLICT(job_name) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (job_name, iso),
        )
        self._conn.commit()

    def load(self, job_name: str) -> Optional[datetime]:
        """Return the stored checkpoint for *job_name*, or ``None`` if absent."""
        row = self._conn.execute(
            "SELECT last_seen FROM checkpoints WHERE job_name = ?",
            (job_name,),
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["last_seen"]).replace(tzinfo=timezone.utc)

    def delete(self, job_name: str) -> None:
        """Remove the checkpoint for *job_name* (e.g. when a job is retired)."""
        self._conn.execute(
            "DELETE FROM checkpoints WHERE job_name = ?", (job_name,)
        )
        self._conn.commit()

    def all_jobs(self) -> list[str]:
        """Return the names of all jobs that have a stored checkpoint."""
        rows = self._conn.execute(
            "SELECT job_name FROM checkpoints ORDER BY job_name"
        ).fetchall()
        return [r["job_name"] for r in rows]

    def close(self) -> None:
        self._conn.close()
