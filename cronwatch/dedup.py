"""Alert deduplication: suppress identical alerts within a time window."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DedupEntry:
    """Tracks the last time a specific alert fingerprint was sent."""

    fingerprint: str
    last_sent: float = 0.0
    send_count: int = 0

    def is_duplicate(self, window_seconds: float, now: Optional[float] = None) -> bool:
        """Return True if the same alert was already sent within the window."""
        if self.last_sent == 0.0:
            return False
        ts = now if now is not None else time.monotonic()
        return (ts - self.last_sent) < window_seconds

    def record(self, now: Optional[float] = None) -> None:
        """Mark this fingerprint as sent at the given (or current) time."""
        self.last_sent = now if now is not None else time.monotonic()
        self.send_count += 1


class AlertDeduplicator:
    """Deduplicates outgoing alerts by content fingerprint within a sliding window."""

    def __init__(self, window_seconds: float = 300.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.window_seconds = window_seconds
        self._entries: Dict[str, DedupEntry] = {}

    @staticmethod
    def fingerprint(job_name: str, event_type: str, detail: str = "") -> str:
        """Produce a stable fingerprint string for a given alert."""
        raw = f"{job_name}:{event_type}:{detail}"
        return hashlib.sha1(raw.encode()).hexdigest()

    def is_duplicate(self, fp: str, now: Optional[float] = None) -> bool:
        """Return True if *fp* was already sent within the dedup window."""
        entry = self._entries.get(fp)
        if entry is None:
            return False
        return entry.is_duplicate(self.window_seconds, now=now)

    def record(self, fp: str, now: Optional[float] = None) -> None:
        """Record that an alert with fingerprint *fp* was sent."""
        if fp not in self._entries:
            self._entries[fp] = DedupEntry(fingerprint=fp)
        self._entries[fp].record(now=now)

    def suppressed_count(self, fp: str) -> int:
        """Return how many times *fp* has been sent (0 if never seen)."""
        entry = self._entries.get(fp)
        return entry.send_count if entry else 0

    def purge_expired(self, now: Optional[float] = None) -> int:
        """Remove entries whose window has fully elapsed. Returns count removed."""
        ts = now if now is not None else time.monotonic()
        expired = [
            fp for fp, e in self._entries.items()
            if e.last_sent > 0.0 and (ts - e.last_sent) >= self.window_seconds
        ]
        for fp in expired:
            del self._entries[fp]
        return len(expired)
