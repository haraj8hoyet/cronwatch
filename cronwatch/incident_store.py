"""Persistent SQLite-backed store for incident records."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwatch.incident import Incident, IncidentState


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    job_name    TEXT NOT NULL,
    state       TEXT NOT NULL,
    opened_at   TEXT NOT NULL,
    resolved_at TEXT,
    event_count INTEGER NOT NULL DEFAULT 0
);
"""


def _row_to_incident(row: tuple) -> Incident:
    incident_id, job_name, state, opened_at, resolved_at, event_count = row
    inc = Incident(
        job_name=job_name,
        incident_id=incident_id,
        state=IncidentState(state),
        opened_at=datetime.fromisoformat(opened_at),
    )
    if resolved_at:
        inc.resolved_at = datetime.fromisoformat(resolved_at)
    # Restore event count as a synthetic placeholder list
    inc.events = [None] * event_count  # type: ignore[list-item]
    return inc


class IncidentStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def save(self, incident: Incident) -> None:
        resolved = incident.resolved_at.isoformat() if incident.resolved_at else None
        self._conn.execute(
            """
            INSERT INTO incidents (incident_id, job_name, state, opened_at, resolved_at, event_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(incident_id) DO UPDATE SET
                state=excluded.state,
                resolved_at=excluded.resolved_at,
                event_count=excluded.event_count
            """,
            (
                incident.incident_id,
                incident.job_name,
                incident.state.value,
                incident.opened_at.isoformat(),
                resolved,
                incident.event_count,
            ),
        )
        self._conn.commit()

    def load(self, incident_id: str) -> Optional[Incident]:
        cur = self._conn.execute(
            "SELECT incident_id, job_name, state, opened_at, resolved_at, event_count "
            "FROM incidents WHERE incident_id = ?",
            (incident_id,),
        )
        row = cur.fetchone()
        return _row_to_incident(row) if row else None

    def open_for_job(self, job_name: str) -> Optional[Incident]:
        cur = self._conn.execute(
            "SELECT incident_id, job_name, state, opened_at, resolved_at, event_count "
            "FROM incidents WHERE job_name = ? AND state != 'resolved' "
            "ORDER BY opened_at DESC LIMIT 1",
            (job_name,),
        )
        row = cur.fetchone()
        return _row_to_incident(row) if row else None

    def recent(self, limit: int = 20) -> List[Incident]:
        cur = self._conn.execute(
            "SELECT incident_id, job_name, state, opened_at, resolved_at, event_count "
            "FROM incidents ORDER BY opened_at DESC LIMIT ?",
            (limit,),
        )
        return [_row_to_incident(r) for r in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()
