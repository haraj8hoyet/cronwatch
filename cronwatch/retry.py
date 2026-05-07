"""Alert retry policy: track failed alert deliveries and decide when to retry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_BASE_DELAY = 60.0   # seconds
_DEFAULT_BACKOFF = 2.0       # exponential multiplier


@dataclass
class RetryEntry:
    job_name: str
    attempts: int = 0
    last_attempt_at: Optional[float] = None
    succeeded_at: Optional[float] = None

    def next_delay(self, base_delay: float, backoff: float) -> float:
        """Seconds to wait before the next attempt (exponential back-off)."""
        if self.attempts == 0:
            return 0.0
        return base_delay * (backoff ** (self.attempts - 1))

    def is_ready(
        self,
        now: float,
        base_delay: float,
        backoff: float,
        max_attempts: int,
    ) -> bool:
        """Return True when a retry is due and attempts remain."""
        if self.attempts >= max_attempts:
            return False
        if self.last_attempt_at is None:
            return True
        return (now - self.last_attempt_at) >= self.next_delay(base_delay, backoff)

    def record_attempt(self, now: Optional[float] = None) -> None:
        self.attempts += 1
        self.last_attempt_at = now if now is not None else time.monotonic()

    def mark_success(self, now: Optional[float] = None) -> None:
        self.succeeded_at = now if now is not None else time.monotonic()


class AlertRetryPolicy:
    """Manages per-job retry state for failed alert dispatches."""

    def __init__(
        self,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        base_delay: float = _DEFAULT_BASE_DELAY,
        backoff: float = _DEFAULT_BACKOFF,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff = backoff
        self._entries: Dict[str, RetryEntry] = {}

    def _get(self, job_name: str) -> RetryEntry:
        if job_name not in self._entries:
            self._entries[job_name] = RetryEntry(job_name=job_name)
        return self._entries[job_name]

    def should_retry(self, job_name: str, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.monotonic()
        return self._get(job_name).is_ready(
            t, self.base_delay, self.backoff, self.max_attempts
        )

    def record_attempt(self, job_name: str, now: Optional[float] = None) -> None:
        self._get(job_name).record_attempt(now)

    def mark_success(self, job_name: str, now: Optional[float] = None) -> None:
        entry = self._get(job_name)
        entry.mark_success(now)
        # Reset so future failures start fresh
        entry.attempts = 0
        entry.last_attempt_at = None

    def attempts(self, job_name: str) -> int:
        return self._entries.get(job_name, RetryEntry(job_name=job_name)).attempts

    def clear(self, job_name: str) -> None:
        self._entries.pop(job_name, None)
