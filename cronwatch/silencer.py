"""Silencer: temporarily suppress alerts for specific jobs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SilenceWindow:
    """Represents a silence window for a single job."""

    job_name: str
    until: float  # Unix timestamp
    reason: str = ""

    def is_active(self, now: Optional[float] = None) -> bool:
        """Return True if the silence window is still active."""
        if now is None:
            now = time.time()
        return now < self.until

    def remaining_seconds(self, now: Optional[float] = None) -> float:
        """Return seconds remaining in the silence window (0 if expired)."""
        if now is None:
            now = time.time()
        return max(0.0, self.until - now)


class AlertSilencer:
    """Manages per-job silence windows to suppress noisy alerts."""

    def __init__(self) -> None:
        self._windows: Dict[str, SilenceWindow] = {}

    def silence(self, job_name: str, duration_seconds: float, reason: str = "") -> SilenceWindow:
        """Silence alerts for *job_name* for *duration_seconds* from now."""
        until = time.time() + duration_seconds
        window = SilenceWindow(job_name=job_name, until=until, reason=reason)
        self._windows[job_name] = window
        return window

    def is_silenced(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if *job_name* currently has an active silence window."""
        window = self._windows.get(job_name)
        if window is None:
            return False
        return window.is_active(now)

    def lift(self, job_name: str) -> bool:
        """Remove any silence window for *job_name*. Returns True if one existed."""
        return self._windows.pop(job_name, None) is not None

    def active_windows(self, now: Optional[float] = None) -> Dict[str, SilenceWindow]:
        """Return a dict of all currently active silence windows."""
        if now is None:
            now = time.time()
        return {name: w for name, w in self._windows.items() if w.is_active(now)}

    def purge_expired(self, now: Optional[float] = None) -> int:
        """Remove expired windows. Returns the number removed."""
        if now is None:
            now = time.time()
        expired = [name for name, w in self._windows.items() if not w.is_active(now)]
        for name in expired:
            del self._windows[name]
        return len(expired)
