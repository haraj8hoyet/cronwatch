"""Per-job alert rate limiting with sliding window counters."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class RateLimitEntry:
    """Tracks alert timestamps for a single job within a sliding window."""

    window_seconds: int
    max_alerts: int
    _timestamps: Deque[float] = field(default_factory=deque)

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def is_allowed(self, now: float | None = None) -> bool:
        """Return True if an alert may be sent right now."""
        now = now if now is not None else time.monotonic()
        self._evict_expired(now)
        return len(self._timestamps) < self.max_alerts

    def record(self, now: float | None = None) -> None:
        """Record that an alert was sent at *now*."""
        now = now if now is not None else time.monotonic()
        self._evict_expired(now)
        self._timestamps.append(now)

    @property
    def current_count(self) -> int:
        self._evict_expired(time.monotonic())
        return len(self._timestamps)

    def seconds_until_next_allowed(self, now: float | None = None) -> float:
        """Return seconds until an alert is allowed, or 0.0 if already allowed.

        Useful for surfacing back-off information in log messages or dashboards.
        """
        now = now if now is not None else time.monotonic()
        self._evict_expired(now)
        if len(self._timestamps) < self.max_alerts:
            return 0.0
        # The oldest timestamp in the window is the one that will expire first.
        oldest = self._timestamps[0]
        return max(0.0, oldest + self.window_seconds - now)


class AlertRateLimiter:
    """Registry of per-job rate-limit entries.

    Args:
        window_seconds: Length of the sliding window in seconds.
        max_alerts: Maximum number of alerts allowed within the window.
    """

    def __init__(self, window_seconds: int = 3600, max_alerts: int = 5) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_alerts <= 0:
            raise ValueError("max_alerts must be positive")
        self._window = window_seconds
        self._max = max_alerts
        self._entries: Dict[str, RateLimitEntry] = {}

    def _entry(self, job_name: str) -> RateLimitEntry:
        if job_name not in self._entries:
            self._entries[job_name] = RateLimitEntry(
                window_seconds=self._window,
                max_alerts=self._max,
            )
        return self._entries[job_name]

    def is_allowed(self, job_name: str, now: float | None = None) -> bool:
        """Return True if *job_name* may send another alert."""
        return self._entry(job_name).is_allowed(now)

    def record(self, job_name: str, now: float | None = None) -> None:
        """Record that an alert was sent for *job_name*."""
        self._entry(job_name).record(now)

    def current_count(self, job_name: str) -> int:
        """Return the number of alerts recorded in the current window."""
        return self._entry(job_name).current_count

    def seconds_until_next_allowed(self, job_name: str, now: float | None = None) -> float:
        """Return seconds until *job_name* may send another alert, or 0.0 if already allowed."""
        return self._entry(job_name).seconds_until_next_allowed(now)

    def reset(self, job_name: str) -> None:
        """Clear rate-limit state for *job_name*."""
        self._entries.pop(job_name, None)
