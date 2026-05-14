"""Cron schedule parsing and missed-run detection."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from croniter import croniter

from cronwatch.config import JobConfig

logger = logging.getLogger(__name__)


class MissedRunDetector:
    """Detects whether a cron job missed its expected execution window."""

    def __init__(self, job: JobConfig) -> None:
        self.job = job

    def last_expected_run(self, now: Optional[datetime] = None) -> datetime:
        """Return the most recent scheduled time before *now*."""
        if now is None:
            now = datetime.utcnow()
        cron = croniter(self.job.schedule, now)
        return cron.get_prev(datetime)

    def next_expected_run(self, now: Optional[datetime] = None) -> datetime:
        """Return the next scheduled time after *now*."""
        if now is None:
            now = datetime.utcnow()
        cron = croniter(self.job.schedule, now)
        return cron.get_next(datetime)

    def seconds_until_next_run(self, now: Optional[datetime] = None) -> float:
        """Return the number of seconds until the next scheduled run.

        Useful for logging or scheduling wake-up timers.
        """
        if now is None:
            now = datetime.utcnow()
        return (self.next_expected_run(now) - now).total_seconds()

    def is_missed(self, last_seen: Optional[datetime], now: Optional[datetime] = None) -> bool:
        """Return True when the job has not run within its expected window.

        A run is considered missed when:
          - *last_seen* is None (never ran), or
          - *last_seen* is earlier than the most recent expected start time
            minus the configured grace period.
        """
        if now is None:
            now = datetime.utcnow()

        expected = self.last_expected_run(now)
        grace = timedelta(seconds=self.job.grace_period)
        deadline = expected + grace

        if now < deadline:
            # Still within the grace window — not yet overdue.
            return False

        if last_seen is None:
            logger.debug("Job '%s' has never run; expected at %s.", self.job.name, expected)
            return True

        if last_seen < expected:
            logger.debug(
                "Job '%s' last ran at %s, but was expected at %s.",
                self.job.name,
                last_seen,
                expected,
            )
            return True

        return False


def validate_schedule(schedule: str) -> bool:
    """Return True if *schedule* is a valid cron expression."""
    try:
        croniter(schedule)
        return True
    except (ValueError, KeyError):
        return False
