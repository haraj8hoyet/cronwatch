"""Alert grouping: batch multiple alert events into a single grouped notification."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.alerter import AlertEvent


@dataclass
class GroupEntry:
    """Accumulates events for a single group key within a flush window."""
    key: str
    window_seconds: float
    events: List[AlertEvent] = field(default_factory=list)
    opened_at: float = field(default_factory=time.monotonic)

    def add(self, event: AlertEvent) -> None:
        self.events.append(event)

    def is_expired(self, now: Optional[float] = None) -> bool:
        """Return True when the grouping window has elapsed."""
        t = now if now is not None else time.monotonic()
        return (t - self.opened_at) >= self.window_seconds

    def size(self) -> int:
        return len(self.events)


class AlertGrouper:
    """Groups incoming alert events by job name and flushes them in batches.

    Events are held until the grouping window expires, then returned together
    so a single notification can cover multiple failures in a burst.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._window = window_seconds
        self._groups: Dict[str, GroupEntry] = {}

    def add(self, event: AlertEvent) -> None:
        """Accept an event.  Opens a new group window if none exists for the job."""
        key = event.job_name
        if key not in self._groups:
            self._groups[key] = GroupEntry(key=key, window_seconds=self._window)
        self._groups[key].add(event)

    def flush(self, now: Optional[float] = None) -> Dict[str, List[AlertEvent]]:
        """Return and remove all groups whose window has expired.

        Returns a mapping of job_name -> list of batched events.
        """
        ready: Dict[str, List[AlertEvent]] = {}
        expired_keys = [
            k for k, g in self._groups.items() if g.is_expired(now)
        ]
        for k in expired_keys:
            ready[k] = self._groups.pop(k).events
        return ready

    def flush_all(self) -> Dict[str, List[AlertEvent]]:
        """Force-flush every pending group regardless of window state."""
        result = {k: g.events for k, g in self._groups.items()}
        self._groups.clear()
        return result

    def pending_count(self) -> int:
        """Total number of events currently held across all groups."""
        return sum(g.size() for g in self._groups.values())

    def group_count(self) -> int:
        """Number of distinct job groups currently open."""
        return len(self._groups)
