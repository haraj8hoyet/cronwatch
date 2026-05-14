"""Alert jitter: randomly delay alert dispatch to avoid thundering-herd
when many jobs fail simultaneously."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JitterEntry:
    """Tracks jitter state for a single alert key."""

    key: str
    delay_seconds: float = 0.0
    scheduled_at: Optional[float] = None  # monotonic timestamp

    def is_pending(self, now: Optional[float] = None) -> bool:
        """Return True if the alert is still within its jitter delay window."""
        if self.scheduled_at is None:
            return False
        t = now if now is not None else time.monotonic()
        return t < self.scheduled_at + self.delay_seconds

    def seconds_remaining(self, now: Optional[float] = None) -> float:
        """Seconds left before the jitter window expires (0 if already elapsed)."""
        if self.scheduled_at is None:
            return 0.0
        t = now if now is not None else time.monotonic()
        remaining = (self.scheduled_at + self.delay_seconds) - t
        return max(0.0, remaining)


class AlertJitter:
    """Assigns and tracks random jitter delays for alert keys.

    Args:
        min_seconds: Lower bound of the random jitter range (inclusive).
        max_seconds: Upper bound of the random jitter range (inclusive).
        seed: Optional RNG seed for deterministic tests.
    """

    def __init__(
        self,
        min_seconds: float = 0.0,
        max_seconds: float = 30.0,
        seed: Optional[int] = None,
    ) -> None:
        if min_seconds < 0 or max_seconds < 0:
            raise ValueError("Jitter bounds must be non-negative")
        if min_seconds > max_seconds:
            raise ValueError("min_seconds must be <= max_seconds")
        self._min = min_seconds
        self._max = max_seconds
        self._rng = random.Random(seed)
        self._entries: dict[str, JitterEntry] = {}

    def assign(self, key: str, now: Optional[float] = None) -> JitterEntry:
        """Assign a new jitter delay for *key* and return the entry.

        If an entry already exists and is still pending, it is returned
        unchanged so callers don't keep pushing the window forward.
        """
        existing = self._entries.get(key)
        t = now if now is not None else time.monotonic()
        if existing is not None and existing.is_pending(t):
            return existing
        delay = self._rng.uniform(self._min, self._max)
        entry = JitterEntry(key=key, delay_seconds=delay, scheduled_at=t)
        self._entries[key] = entry
        return entry

    def is_pending(self, key: str, now: Optional[float] = None) -> bool:
        """Return True if *key* has an active (unexpired) jitter delay."""
        entry = self._entries.get(key)
        if entry is None:
            return False
        return entry.is_pending(now)

    def clear(self, key: str) -> None:
        """Remove the jitter entry for *key* (e.g. after the alert is sent)."""
        self._entries.pop(key, None)

    def entry_count(self) -> int:
        """Return the number of tracked jitter entries."""
        return len(self._entries)
