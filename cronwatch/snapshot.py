"""Point-in-time snapshot of all monitored job states for dashboards / reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from cronwatch.status import JobStatus, StatusReport


@dataclass
class JobSnapshot:
    """Immutable record of a single job's state at snapshot time."""

    job_name: str
    state: str
    last_run_at: Optional[datetime]
    last_exit_code: Optional[int]
    consecutive_failures: int
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_healthy(self) -> bool:
        return self.state == "ok"

    def is_failing(self) -> bool:
        return self.state == "failing"

    def __str__(self) -> str:
        ts = self.last_run_at.isoformat() if self.last_run_at else "never"
        return (
            f"{self.job_name}: state={self.state} "
            f"last_run={ts} failures={self.consecutive_failures}"
        )


@dataclass
class SystemSnapshot:
    """Aggregated snapshot of all jobs at a single point in time."""

    captured_at: datetime
    jobs: List[JobSnapshot] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.jobs)

    @property
    def healthy(self) -> int:
        return sum(1 for j in self.jobs if j.is_healthy())

    @property
    def failing(self) -> int:
        return sum(1 for j in self.jobs if j.is_failing())

    def __str__(self) -> str:
        ts = self.captured_at.isoformat()
        return (
            f"SystemSnapshot at {ts}: "
            f"total={self.total} healthy={self.healthy} failing={self.failing}"
        )


class SnapshotBuilder:
    """Builds a SystemSnapshot from a StatusReport."""

    def build(self, report: StatusReport) -> SystemSnapshot:
        now = datetime.now(timezone.utc)
        jobs: List[JobSnapshot] = []
        for status in report.statuses:
            last_run = status.last_run
            jobs.append(
                JobSnapshot(
                    job_name=status.job_name,
                    state=status.state,
                    last_run_at=last_run.end_time if last_run else None,
                    last_exit_code=last_run.exit_code if last_run else None,
                    consecutive_failures=status.consecutive_failures,
                    captured_at=now,
                )
            )
        return SystemSnapshot(captured_at=now, jobs=jobs)
