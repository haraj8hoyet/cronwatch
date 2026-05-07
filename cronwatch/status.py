"""Status summary for all monitored jobs, suitable for CLI or HTTP output."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronwatch.history import JobHistory
from cronwatch.scheduler import MissedRunDetector
from cronwatch.config import JobConfig


@dataclass
class JobStatus:
    name: str
    schedule: str
    last_run_at: Optional[datetime]
    last_exit_code: Optional[int]
    last_duration_seconds: Optional[float]
    is_missed: bool
    next_expected_at: Optional[datetime]

    @property
    def state(self) -> str:
        if self.is_missed:
            return "MISSED"
        if self.last_exit_code is None:
            return "UNKNOWN"
        return "OK" if self.last_exit_code == 0 else "FAILED"

    def __str__(self) -> str:
        last = self.last_run_at.strftime("%Y-%m-%d %H:%M:%S") if self.last_run_at else "never"
        nxt = self.next_expected_at.strftime("%Y-%m-%d %H:%M:%S") if self.next_expected_at else "unknown"
        dur = f"{self.last_duration_seconds:.1f}s" if self.last_duration_seconds is not None else "-"
        return (
            f"{self.name:<30} {self.state:<8} last={last}  dur={dur:<8} next={nxt}"
        )


@dataclass
class StatusReport:
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    jobs: List[JobStatus] = field(default_factory=list)

    def __str__(self) -> str:
        header = f"Cronwatch Status — {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        separator = "-" * len(header)
        lines = [header, separator]
        if not self.jobs:
            lines.append("  No jobs configured.")
        else:
            for job in self.jobs:
                lines.append(f"  {job}")
        return "\n".join(lines)


class StatusChecker:
    """Builds a StatusReport from config and history."""

    def __init__(self, history: JobHistory, jobs: List[JobConfig]) -> None:
        self._history = history
        self._jobs = jobs

    def report(self, now: Optional[datetime] = None) -> StatusReport:
        now = now or datetime.now(timezone.utc)
        statuses: List[JobStatus] = []

        for job in self._jobs:
            runs = self._history.recent(job.name, limit=1)
            last_run = runs[0] if runs else None

            detector = MissedRunDetector(job.schedule)
            missed = detector.is_missed(last_run.started_at if last_run else None, now)
            next_exp = detector.next_expected_run(now)

            statuses.append(
                JobStatus(
                    name=job.name,
                    schedule=job.schedule,
                    last_run_at=last_run.started_at if last_run else None,
                    last_exit_code=last_run.exit_code if last_run else None,
                    last_duration_seconds=last_run.duration if last_run else None,
                    is_missed=missed,
                    next_expected_at=next_exp,
                )
            )

        return StatusReport(generated_at=now, jobs=statuses)
