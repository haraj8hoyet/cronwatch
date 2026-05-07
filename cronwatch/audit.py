"""Audit log: append-only record of silence and alert-suppression events."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditEntry:
    event_type: str      # e.g. "silenced", "lifted", "alert_suppressed"
    job_name: str
    timestamp: float
    detail: str = ""

    def __str__(self) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))
        return f"[{ts}] {self.event_type} job={self.job_name} {self.detail}".strip()


class AuditLog:
    """SQLite-backed append-only audit log for silence/suppression events."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = self._connect()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT NOT NULL,
                job_name    TEXT NOT NULL,
                timestamp   REAL NOT NULL,
                detail      TEXT NOT NULL DEFAULT ''
            )
            """
        )
        self._conn.commit()

    def record(self, event_type: str, job_name: str, detail: str = "",
               now: Optional[float] = None) -> AuditEntry:
        """Append an audit entry and return it."""
        ts = now if now is not None else time.time()
        self._conn.execute(
            "INSERT INTO audit (event_type, job_name, timestamp, detail) VALUES (?,?,?,?)",
            (event_type, job_name, ts, detail),
        )
        self._conn.commit()
        return AuditEntry(event_type=event_type, job_name=job_name, timestamp=ts, detail=detail)

    def query(self, job_name: Optional[str] = None, limit: int = 100) -> List[AuditEntry]:
        """Return recent audit entries, optionally filtered by job name."""
        if job_name:
            rows = self._conn.execute(
                "SELECT * FROM audit WHERE job_name=? ORDER BY timestamp DESC LIMIT ?",
                (job_name, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM audit ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            AuditEntry(
                event_type=r["event_type"],
                job_name=r["job_name"],
                timestamp=r["timestamp"],
                detail=r["detail"],
            )
            for r in rows
        ]
