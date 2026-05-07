"""Generates summary reports of cron job history and status."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from cronwatch.history import JobHistory
from cronwatch.tracker import JobRun


@dataclass
class JobSummary:
    """Aggregated statistics for a single job over a time window."""

    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    avg_duration_seconds: Optional[float]
    last_run_at: Optional[datetime]
    last_exit_code: Optional[int]

    @property
    def success_rate(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return self.successful_runs / self.total_runs

    def __str__(self) -> str:
        rate = (
            f"{self.success_rate * 100:.1f}%"
            if self.success_rate is not None
            else "n/a"
        )
        avg = (
            f"{self.avg_duration_seconds:.1f}s"
            if self.avg_duration_seconds is not None
            else "n/a"
        )
        last = self.last_run_at.strftime("%Y-%m-%d %H:%M:%S") if self.last_run_at else "never"
        return (
            f"{self.job_name}: runs={self.total_runs}, success={rate}, "
            f"avg_duration={avg}, last_run={last}"
        )


class Reporter:
    """Builds job summaries from historical run data."""

    def __init__(self, history: JobHistory) -> None:
        self._history = history

    def summarise(self, job_name: str, since: datetime) -> JobSummary:
        """Return a summary for *job_name* covering runs on or after *since*."""
        runs: List[JobRun] = self._history.get_runs(job_name, since=since)

        total = len(runs)
        successful = sum(1 for r in runs if r.succeeded)
        failed = sum(1 for r in runs if r.failed)

        durations = [r.duration for r in runs if r.duration is not None]
        avg_duration = sum(durations) / len(durations) if durations else None

        finished_runs = [r for r in runs if r.finished_at is not None]
        finished_runs.sort(key=lambda r: r.finished_at)  # type: ignore[arg-type]
        last_run = finished_runs[-1] if finished_runs else None

        return JobSummary(
            job_name=job_name,
            total_runs=total,
            successful_runs=successful,
            failed_runs=failed,
            avg_duration_seconds=avg_duration,
            last_run_at=last_run.finished_at if last_run else None,
            last_exit_code=last_run.exit_code if last_run else None,
        )

    def report(self, job_names: List[str], window_hours: int = 24) -> List[JobSummary]:
        """Return summaries for all *job_names* over the last *window_hours* hours."""
        since = datetime.utcnow() - timedelta(hours=window_hours)
        return [self.summarise(name, since) for name in job_names]
