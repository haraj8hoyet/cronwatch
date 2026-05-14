"""Exponential backoff calculator for alert retry scheduling."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_BASE_DELAY: float = 30.0
_DEFAULT_MAX_DELAY: float = 3600.0
_DEFAULT_MULTIPLIER: float = 2.0


@dataclass
class BackoffEntry:
    """Tracks backoff state for a single alert key."""

    base_delay: float = _DEFAULT_BASE_DELAY
    max_delay: float = _DEFAULT_MAX_DELAY
    multiplier: float = _DEFAULT_MULTIPLIER
    attempt: int = 0
    last_attempt_at: Optional[float] = None
    _extra: dict = field(default_factory=dict, repr=False)

    def current_delay(self) -> float:
        """Return the delay (seconds) that should precede the next attempt."""
        if self.attempt == 0:
            return 0.0
        delay = self.base_delay * (self.multiplier ** (self.attempt - 1))
        return min(delay, self.max_delay)

    def is_ready(self, now: Optional[float] = None) -> bool:
        """Return True when enough time has elapsed to allow the next attempt."""
        if self.last_attempt_at is None:
            return True
        now = now if now is not None else time.monotonic()
        return (now - self.last_attempt_at) >= self.current_delay()

    def record_attempt(self, now: Optional[float] = None) -> None:
        """Advance the attempt counter and record the timestamp."""
        self.last_attempt_at = now if now is not None else time.monotonic()
        self.attempt += 1

    def reset(self) -> None:
        """Reset backoff state after a successful delivery."""
        self.attempt = 0
        self.last_attempt_at = None


class BackoffRegistry:
    """Manages BackoffEntry instances keyed by alert fingerprint."""

    def __init__(
        self,
        base_delay: float = _DEFAULT_BASE_DELAY,
        max_delay: float = _DEFAULT_MAX_DELAY,
        multiplier: float = _DEFAULT_MULTIPLIER,
    ) -> None:
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._multiplier = multiplier
        self._entries: dict[str, BackoffEntry] = {}

    def _get_or_create(self, key: str) -> BackoffEntry:
        if key not in self._entries:
            self._entries[key] = BackoffEntry(
                base_delay=self._base_delay,
                max_delay=self._max_delay,
                multiplier=self._multiplier,
            )
        return self._entries[key]

    def is_ready(self, key: str, now: Optional[float] = None) -> bool:
        return self._get_or_create(key).is_ready(now=now)

    def record_attempt(self, key: str, now: Optional[float] = None) -> None:
        self._get_or_create(key).record_attempt(now=now)

    def reset(self, key: str) -> None:
        if key in self._entries:
            self._entries[key].reset()

    def current_delay(self, key: str) -> float:
        return self._get_or_create(key).current_delay()

    def attempt_count(self, key: str) -> int:
        return self._get_or_create(key).attempt
