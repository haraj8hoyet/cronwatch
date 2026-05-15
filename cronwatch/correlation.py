"""Alert correlation: groups related alerts by shared attributes into incidents."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.alerter import AlertEvent


@dataclass
class CorrelationEntry:
    """Tracks a set of correlated alert events under a single incident key."""

    incident_key: str
    created_at: float = field(default_factory=time.monotonic)
    last_updated: float = field(default_factory=time.monotonic)
    events: List[AlertEvent] = field(default_factory=list)
    window_seconds: float = 300.0

    def add(self, event: AlertEvent) -> None:
        self.events.append(event)
        self.last_updated = time.monotonic()

    def is_expired(self, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.monotonic()
        return (t - self.last_updated) > self.window_seconds

    @property
    def size(self) -> int:
        return len(self.events)


class AlertCorrelator:
    """Correlates incoming alerts into incidents based on job name and event kind."""

    def __init__(self, window_seconds: float = 300.0) -> None:
        self._window = window_seconds
        self._entries: Dict[str, CorrelationEntry] = {}

    def _incident_key(self, event: AlertEvent) -> str:
        return f"{event.job_name}:{event.kind}"

    def add(self, event: AlertEvent) -> CorrelationEntry:
        """Add an event to its incident bucket, creating one if necessary."""
        key = self._incident_key(event)
        now = time.monotonic()
        entry = self._entries.get(key)
        if entry is None or entry.is_expired(now):
            entry = CorrelationEntry(
                incident_key=key,
                window_seconds=self._window,
            )
            self._entries[key] = entry
        entry.add(event)
        return entry

    def get(self, event: AlertEvent) -> Optional[CorrelationEntry]:
        """Return the current incident entry for an event, or None."""
        return self._entries.get(self._incident_key(event))

    def flush_expired(self, now: Optional[float] = None) -> List[CorrelationEntry]:
        """Remove and return all expired incident entries."""
        t = now if now is not None else time.monotonic()
        expired = [e for e in self._entries.values() if e.is_expired(t)]
        for e in expired:
            del self._entries[e.incident_key]
        return expired

    @property
    def active_count(self) -> int:
        return len(self._entries)
