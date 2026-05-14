"""Per-job cooldown tracker that prevents alert storms after repeated failures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CooldownEntry:
    """Tracks cooldown state for a single job."""

    job_name: str
    cooldown_seconds: float
    _last_alert_at: Optional[float] = field(default=None, repr=False)
    _alert_count: int = field(default=0, repr=False)

    def is_cooling_down(self, now: Optional[float] = None) -> bool:
        """Return True if the job is still within its cooldown window."""
        if self._last_alert_at is None:
            return False
        ts = now if now is not None else time.monotonic()
        return (ts - self._last_alert_at) < self.cooldown_seconds

    def record_alert(self, now: Optional[float] = None) -> None:
        """Mark that an alert was just sent for this job."""
        self._last_alert_at = now if now is not None else time.monotonic()
        self._alert_count += 1

    def reset(self) -> None:
        """Clear cooldown state, e.g. after a successful run."""
        self._last_alert_at = None
        self._alert_count = 0

    @property
    def alert_count(self) -> int:
        return self._alert_count

    @property
    def seconds_remaining(self) -> float:
        """Seconds left in the current cooldown window, or 0.0 if not active."""
        if self._last_alert_at is None:
            return 0.0
        elapsed = time.monotonic() - self._last_alert_at
        remaining = self.cooldown_seconds - elapsed
        return max(0.0, remaining)


class CooldownRegistry:
    """Registry of per-job cooldown entries."""

    def __init__(self, default_cooldown_seconds: float = 300.0) -> None:
        self._default = default_cooldown_seconds
        self._entries: Dict[str, CooldownEntry] = {}

    def _get_or_create(self, job_name: str) -> CooldownEntry:
        if job_name not in self._entries:
            self._entries[job_name] = CooldownEntry(
                job_name=job_name,
                cooldown_seconds=self._default,
            )
        return self._entries[job_name]

    def is_cooling_down(self, job_name: str, now: Optional[float] = None) -> bool:
        return self._get_or_create(job_name).is_cooling_down(now=now)

    def record_alert(self, job_name: str, now: Optional[float] = None) -> None:
        self._get_or_create(job_name).record_alert(now=now)

    def reset(self, job_name: str) -> None:
        if job_name in self._entries:
            self._entries[job_name].reset()

    def entry(self, job_name: str) -> CooldownEntry:
        return self._get_or_create(job_name)

    def __len__(self) -> int:
        return len(self._entries)
