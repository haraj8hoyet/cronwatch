"""Job execution tracker that records run history and detects failures."""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobRun:
    """Represents a single execution record of a cron job."""

    job_name: str
    started_at: float
    finished_at: Optional[float] = None
    exit_code: Optional[int] = None
    output: Optional[str] = None

    @property
    def duration(self) -> Optional[float]:
        if self.finished_at is not None:
            return self.finished_at - self.started_at
        return None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def failed(self) -> bool:
        return self.exit_code is not None and self.exit_code != 0

    @property
    def is_running(self) -> bool:
        return self.finished_at is None


class JobTracker:
    """Tracks job execution history in memory."""

    def __init__(self, max_history: int = 100):
        self._max_history = max_history
        self._history: dict[str, list[JobRun]] = {}

    def start_run(self, job_name: str) -> JobRun:
        """Record the start of a job execution."""
        run = JobRun(job_name=job_name, started_at=time.time())
        if job_name not in self._history:
            self._history[job_name] = []
        self._history[job_name].append(run)
        if len(self._history[job_name]) > self._max_history:
            self._history[job_name].pop(0)
        return run

    def finish_run(
        self,
        run: JobRun,
        exit_code: int,
        output: Optional[str] = None,
    ) -> None:
        """Record the completion of a job execution."""
        run.finished_at = time.time()
        run.exit_code = exit_code
        run.output = output

    def last_run(self, job_name: str) -> Optional[JobRun]:
        """Return the most recent completed run for a job."""
        runs = self._history.get(job_name, [])
        completed = [r for r in runs if not r.is_running]
        return completed[-1] if completed else None

    def recent_runs(self, job_name: str, limit: int = 10) -> list[JobRun]:
        """Return the most recent runs for a job."""
        runs = self._history.get(job_name, [])
        return runs[-limit:]

    def failure_streak(self, job_name: str) -> int:
        """Return the number of consecutive failures for a job."""
        runs = [r for r in self._history.get(job_name, []) if not r.is_running]
        streak = 0
        for run in reversed(runs):
            if run.failed:
                streak += 1
            else:
                break
        return streak
