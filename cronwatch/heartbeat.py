"""Heartbeat monitor: detects jobs that have not started within a grace period."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatRecord:
    """Tracks the last known check-in time for a job."""

    job_name: str
    last_seen: Optional[datetime] = None
    grace_seconds: int = 60

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        """Return True if the job has not checked in within the grace period."""
        if self.last_seen is None:
            return False  # Never started — scheduler handles missed-run logic
        now = now or datetime.utcnow()
        return (now - self.last_seen) > timedelta(seconds=self.grace_seconds)

    def touch(self, at: Optional[datetime] = None) -> None:
        """Record a check-in, optionally at a specific time."""
        self.last_seen = at or datetime.utcnow()


class HeartbeatMonitor:
    """Registry of heartbeat records; identifies stale jobs."""

    def __init__(self) -> None:
        self._records: Dict[str, HeartbeatRecord] = {}

    def register(self, job_name: str, grace_seconds: int = 60) -> None:
        """Register a job for heartbeat monitoring."""
        if job_name not in self._records:
            self._records[job_name] = HeartbeatRecord(
                job_name=job_name, grace_seconds=grace_seconds
            )
            logger.debug("Registered heartbeat for job '%s' (grace=%ds)", job_name, grace_seconds)

    def touch(self, job_name: str, at: Optional[datetime] = None) -> None:
        """Update the last-seen timestamp for a job."""
        if job_name not in self._records:
            raise KeyError(f"Job '{job_name}' is not registered with HeartbeatMonitor")
        self._records[job_name].touch(at=at)
        logger.debug("Heartbeat touch for job '%s'", job_name)

    def stale_jobs(self, now: Optional[datetime] = None) -> list[str]:
        """Return names of jobs whose heartbeat has gone stale."""
        now = now or datetime.utcnow()
        return [
            name
            for name, record in self._records.items()
            if record.is_stale(now=now)
        ]

    def __len__(self) -> int:
        return len(self._records)
