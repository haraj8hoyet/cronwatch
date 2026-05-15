"""Alert budget tracking — limits total alerts fired within a rolling window."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class BudgetEntry:
    """Tracks alert timestamps for a single budget bucket."""

    window_seconds: int
    max_alerts: int
    _timestamps: Deque[float] = field(default_factory=deque, repr=False)

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def is_within_budget(self, now: float | None = None) -> bool:
        """Return True if another alert can be fired without exceeding the budget."""
        if now is None:
            now = time.monotonic()
        self._evict_expired(now)
        return len(self._timestamps) < self.max_alerts

    def record(self, now: float | None = None) -> None:
        """Record that an alert was fired."""
        if now is None:
            now = time.monotonic()
        self._evict_expired(now)
        self._timestamps.append(now)

    def current_count(self, now: float | None = None) -> int:
        """Return the number of alerts recorded within the current window."""
        if now is None:
            now = time.monotonic()
        self._evict_expired(now)
        return len(self._timestamps)

    def remaining(self, now: float | None = None) -> int:
        """Return how many more alerts are allowed in the current window."""
        return max(0, self.max_alerts - self.current_count(now))


class AlertBudget:
    """Manages per-job (or global) alert budgets."""

    def __init__(self, window_seconds: int = 3600, max_alerts: int = 10) -> None:
        self._window = window_seconds
        self._max = max_alerts
        self._entries: dict[str, BudgetEntry] = {}

    def _entry(self, key: str) -> BudgetEntry:
        if key not in self._entries:
            self._entries[key] = BudgetEntry(
                window_seconds=self._window, max_alerts=self._max
            )
        return self._entries[key]

    def is_within_budget(self, key: str, now: float | None = None) -> bool:
        return self._entry(key).is_within_budget(now)

    def record(self, key: str, now: float | None = None) -> None:
        self._entry(key).record(now)

    def current_count(self, key: str, now: float | None = None) -> int:
        return self._entry(key).current_count(now)

    def remaining(self, key: str, now: float | None = None) -> int:
        return self._entry(key).remaining(now)

    def reset(self, key: str) -> None:
        """Clear budget history for a key (e.g. after manual acknowledgement)."""
        self._entries.pop(key, None)
