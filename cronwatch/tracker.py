"""Tracks in-progress and completed cron job runs."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional


class JobRun:
    """Record of a single execution of a cron job."""

    def __init__(self) -> None:
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.exit_code: Optional[int] = None

    @property
    def duration(self) -> Optional[float]:
        """Wall-clock seconds between start and finish, or None if incomplete."""
        if self.started_at is None or self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def failed(self) -> bool:
        return self.exit_code is not None and self.exit_code != 0

    @property
    def is_running(self) -> bool:
        return self.started_at is not None and self.finished_at is None


class JobTracker:
    """Thread-safe tracker for job runs across multiple named jobs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: Dict[str, List[JobRun]] = {}

    def start_run(self, job_name: str) -> JobRun:
        """Record that *job_name* has started; returns the new JobRun."""
        run = JobRun()
        run.started_at = datetime.now(tz=timezone.utc)
        with self._lock:
            self._runs.setdefault(job_name, []).append(run)
        return run

    def finish_run(self, job_name: str, exit_code: int) -> Optional[JobRun]:
        """Mark the most recent in-progress run for *job_name* as finished."""
        with self._lock:
            for run in reversed(self._runs.get(job_name, [])):
                if run.is_running:
                    run.finished_at = datetime.now(tz=timezone.utc)
                    run.exit_code = exit_code
                    return run
        return None

    def current_run(self, job_name: str) -> Optional[JobRun]:
        """Return the active (unfinished) run for *job_name*, or None."""
        with self._lock:
            for run in reversed(self._runs.get(job_name, [])):
                if run.is_running:
                    return run
        return None

    def all_runs(self, job_name: str) -> List[JobRun]:
        """Return all recorded runs for *job_name* (oldest first)."""
        with self._lock:
            return list(self._runs.get(job_name, []))

    def last_run(self, job_name: str) -> Optional[JobRun]:
        """Return the most recently *completed* run for *job_name*, or None."""
        with self._lock:
            for run in reversed(self._runs.get(job_name, [])):
                if not run.is_running:
                    return run
        return None

    def known_jobs(self) -> List[str]:
        """Return names of all jobs that have at least one recorded run."""
        with self._lock:
            return list(self._runs.keys())
