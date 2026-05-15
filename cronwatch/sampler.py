"""Metric sampler: collects periodic success-rate samples for trend analysis."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class MetricSample:
    job_name: str
    timestamp: float
    success_rate: float  # 0.0 – 1.0
    run_count: int

    def __str__(self) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))
        return (
            f"{self.job_name} @ {ts}: "
            f"rate={self.success_rate:.2%} runs={self.run_count}"
        )


class MetricSampler:
    """Persists periodic metric snapshots per job to a SQLite store."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = self._connect()
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_samples (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name    TEXT    NOT NULL,
                timestamp   REAL    NOT NULL,
                success_rate REAL   NOT NULL,
                run_count   INTEGER NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ms_job_ts "
            "ON metric_samples (job_name, timestamp)"
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, sample: MetricSample) -> None:
        """Persist a single metric sample."""
        self._conn.execute(
            "INSERT INTO metric_samples (job_name, timestamp, success_rate, run_count) "
            "VALUES (?, ?, ?, ?)",
            (sample.job_name, sample.timestamp, sample.success_rate, sample.run_count),
        )
        self._conn.commit()

    def recent(self, job_name: str, limit: int = 20) -> List[MetricSample]:
        """Return the most recent *limit* samples for *job_name*, oldest first."""
        rows = self._conn.execute(
            "SELECT job_name, timestamp, success_rate, run_count "
            "FROM metric_samples WHERE job_name = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (job_name, limit),
        ).fetchall()
        return [
            MetricSample(
                job_name=r["job_name"],
                timestamp=r["timestamp"],
                success_rate=r["success_rate"],
                run_count=r["run_count"],
            )
            for r in reversed(rows)
        ]

    def latest(self, job_name: str) -> Optional[MetricSample]:
        """Return the single most-recent sample or *None*."""
        samples = self.recent(job_name, limit=1)
        return samples[0] if samples else None

    def purge_before(self, cutoff_ts: float) -> int:
        """Delete samples older than *cutoff_ts*; returns the number removed."""
        cur = self._conn.execute(
            "DELETE FROM metric_samples WHERE timestamp < ?", (cutoff_ts,)
        )
        self._conn.commit()
        return cur.rowcount
