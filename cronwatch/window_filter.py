"""Time-window based alert filtering.

Allows alerts to be suppressed outside of configured active windows,
e.g. only alert during business hours.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional


_TIME_RE = re.compile(r'^(\d{1,2}):(\d{2})$')


def _parse_time(value: str) -> time:
    m = _TIME_RE.match(value.strip())
    if not m:
        raise ValueError(f"Invalid time format {value!r}, expected HH:MM")
    return time(int(m.group(1)), int(m.group(2)))


@dataclass
class ActiveWindow:
    """A named time window during which alerts are permitted."""
    name: str
    start: time
    end: time
    # ISO weekday numbers 1=Mon … 7=Sun; empty means every day
    weekdays: List[int] = field(default_factory=list)

    def is_active(self, now: Optional[datetime] = None) -> bool:
        """Return True if *now* falls inside this window."""
        if now is None:
            now = datetime.utcnow()
        if self.weekdays and now.isoweekday() not in self.weekdays:
            return False
        current = now.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= current <= self.end
        # Overnight window e.g. 22:00 – 06:00
        return current >= self.start or current <= self.end


class WindowFilterRegistry:
    """Registry of active windows; decides whether an alert may pass."""

    def __init__(self) -> None:
        self._windows: List[ActiveWindow] = []

    def add_window(self, window: ActiveWindow) -> None:
        self._windows.append(window)

    def is_allowed(self, now: Optional[datetime] = None) -> bool:
        """Return True when at least one window is active (or none configured)."""
        if not self._windows:
            return True
        return any(w.is_active(now) for w in self._windows)

    @property
    def window_count(self) -> int:
        return len(self._windows)
