"""Periodic digest builder: aggregates job summaries into a single alert body."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from cronwatch.reporter import JobSummary


@dataclass
class DigestReport:
    """Holds an aggregated digest of multiple job summaries."""

    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    summaries: List[JobSummary] = field(default_factory=list)

    @property
    def total_jobs(self) -> int:
        return len(self.summaries)

    @property
    def failing_jobs(self) -> List[JobSummary]:
        return [s for s in self.summaries if s.success_rate < 1.0 and s.total_runs > 0]

    @property
    def healthy_jobs(self) -> List[JobSummary]:
        return [s for s in self.summaries if s.success_rate == 1.0 and s.total_runs > 0]

    @property
    def idle_jobs(self) -> List[JobSummary]:
        return [s for s in self.summaries if s.total_runs == 0]

    def subject(self) -> str:
        n_fail = len(self.failing_jobs)
        if n_fail:
            return f"[cronwatch] Digest — {n_fail} job(s) with failures"
        return "[cronwatch] Digest — all jobs healthy"

    def body(self) -> str:
        lines: List[str] = [
            f"Cronwatch digest — {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"Jobs monitored: {self.total_jobs}",
            "",
        ]
        if self.failing_jobs:
            lines.append("FAILING JOBS:")
            for s in self.failing_jobs:
                pct = f"{s.success_rate * 100:.0f}%"
                lines.append(f"  {s.job_name}: {s.total_runs} runs, {pct} success")
            lines.append("")
        if self.healthy_jobs:
            lines.append("Healthy jobs: " + ", ".join(s.job_name for s in self.healthy_jobs))
        if self.idle_jobs:
            lines.append("No runs recorded: " + ", ".join(s.job_name for s in self.idle_jobs))
        return "\n".join(lines)


class DigestBuilder:
    """Builds a DigestReport from a list of job names using a Reporter."""

    def __init__(self, reporter) -> None:
        self._reporter = reporter

    def build(self, job_names: List[str], hours: int = 24) -> DigestReport:
        summaries = [self._reporter.summary(name, hours=hours) for name in job_names]
        return DigestReport(summaries=summaries)
