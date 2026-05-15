"""Trend analysis for job success rates over time."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class TrendPoint:
    """A single data point in a job's success-rate trend."""

    timestamp: datetime
    success_rate: float  # 0.0 – 1.0
    sample_size: int


@dataclass
class TrendResult:
    """Computed trend for a single job."""

    job_name: str
    points: List[TrendPoint] = field(default_factory=list)

    @property
    def is_degrading(self) -> bool:
        """Return True when the latest rate is lower than the earliest rate."""
        if len(self.points) < 2:
            return False
        return self.points[-1].success_rate < self.points[0].success_rate

    @property
    def latest_rate(self) -> Optional[float]:
        if not self.points:
            return None
        return self.points[-1].success_rate

    @property
    def delta(self) -> Optional[float]:
        """Change in success rate from first to last point (negative = worse)."""
        if len(self.points) < 2:
            return None
        return self.points[-1].success_rate - self.points[0].success_rate

    def __str__(self) -> str:
        rate = f"{self.latest_rate:.1%}" if self.latest_rate is not None else "n/a"
        direction = "degrading" if self.is_degrading else "stable/improving"
        return f"TrendResult({self.job_name}: {rate} [{direction}])"


class TrendAnalyzer:
    """Analyses a sequence of JobRun-like records to produce trend data."""

    def __init__(self, bucket_hours: int = 6, max_buckets: int = 8) -> None:
        if bucket_hours < 1:
            raise ValueError("bucket_hours must be >= 1")
        if max_buckets < 1:
            raise ValueError("max_buckets must be >= 1")
        self.bucket_hours = bucket_hours
        self.max_buckets = max_buckets

    def analyze(self, job_name: str, runs) -> TrendResult:
        """Build a TrendResult from an iterable of JobRun-compatible objects.

        Each run must expose:
          - ``started_at`` (datetime, UTC)
          - ``succeeded`` (bool)
        """
        now = datetime.now(timezone.utc)
        bucket_seconds = self.bucket_hours * 3600
        buckets: dict[int, list[bool]] = {}

        for run in runs:
            age = (now - run.started_at).total_seconds()
            bucket_index = int(age // bucket_seconds)
            if bucket_index >= self.max_buckets:
                continue
            buckets.setdefault(bucket_index, []).append(run.succeeded)

        points: list[TrendPoint] = []
        for idx in sorted(buckets.keys(), reverse=True):
            outcomes = buckets[idx]
            rate = sum(outcomes) / len(outcomes)
            bucket_start = now.replace(
                second=0, microsecond=0
            ).__class__.fromtimestamp(
                now.timestamp() - (idx + 1) * bucket_seconds, tz=timezone.utc
            )
            points.append(TrendPoint(
                timestamp=bucket_start,
                success_rate=rate,
                sample_size=len(outcomes),
            ))

        return TrendResult(job_name=job_name, points=points)
