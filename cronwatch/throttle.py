"""Alert throttling to suppress repeated notifications for the same job."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ThrottleEntry:
    """Tracks the last alert time and suppression count for a job."""

    last_alert_at: float
    suppressed_count: int = 0

    def is_cooling_down(self, cooldown_seconds: int, now: Optional[float] = None) -> bool:
        """Return True if the cooldown period has not yet elapsed."""
        now = now if now is not None else time.time()
        return (now - self.last_alert_at) < cooldown_seconds


class AlertThrottle:
    """Prevents alert storms by rate-limiting notifications per job.

    Args:
        cooldown_seconds: Minimum seconds between alerts for the same job.
    """

    def __init__(self, cooldown_seconds: int = 300) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        self.cooldown_seconds = cooldown_seconds
        self._entries: Dict[str, ThrottleEntry] = {}

    def should_send(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if an alert should be sent for the given job.

        Updates internal state when the alert is allowed through.
        """
        now = now if now is not None else time.time()
        entry = self._entries.get(job_name)

        if entry is None:
            self._entries[job_name] = ThrottleEntry(last_alert_at=now)
            return True

        if entry.is_cooling_down(self.cooldown_seconds, now):
            entry.suppressed_count += 1
            return False

        entry.last_alert_at = now
        entry.suppressed_count = 0
        return True

    def suppressed_count(self, job_name: str) -> int:
        """Return how many alerts have been suppressed for a job since last send."""
        entry = self._entries.get(job_name)
        return entry.suppressed_count if entry else 0

    def reset(self, job_name: str) -> None:
        """Clear throttle state for a job (e.g. after a successful run)."""
        self._entries.pop(job_name, None)
