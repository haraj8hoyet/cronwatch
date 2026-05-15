"""Alert muting: temporarily suppress all alerts for a specific job."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class MuteEntry:
    """Tracks a mute window for a single job."""
    job_name: str
    expires_at: float  # Unix timestamp
    reason: str = ""

    def is_active(self, now: Optional[float] = None) -> bool:
        """Return True if the mute window has not yet expired."""
        t = now if now is not None else time.time()
        return t < self.expires_at

    def remaining_seconds(self, now: Optional[float] = None) -> float:
        """Seconds remaining in the mute window (0 if expired)."""
        t = now if now is not None else time.time()
        return max(0.0, self.expires_at - t)


class AlertMuter:
    """Registry of per-job mute windows."""

    def __init__(self) -> None:
        self._entries: Dict[str, MuteEntry] = {}

    def mute(self, job_name: str, duration_seconds: float, reason: str = "") -> MuteEntry:
        """Mute *job_name* for *duration_seconds* seconds."""
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        entry = MuteEntry(
            job_name=job_name,
            expires_at=time.time() + duration_seconds,
            reason=reason,
        )
        self._entries[job_name] = entry
        return entry

    def unmute(self, job_name: str) -> bool:
        """Remove an active mute. Returns True if a mute was present."""
        return self._entries.pop(job_name, None) is not None

    def is_muted(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if *job_name* is currently muted."""
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        if entry.is_active(now):
            return True
        # Lazily evict expired entries
        del self._entries[job_name]
        return False

    def get_entry(self, job_name: str) -> Optional[MuteEntry]:
        """Return the MuteEntry for *job_name*, or None."""
        return self._entries.get(job_name)

    def active_mutes(self, now: Optional[float] = None) -> Dict[str, MuteEntry]:
        """Return a dict of all currently active mute entries."""
        t = now if now is not None else time.time()
        return {k: v for k, v in self._entries.items() if v.is_active(t)}
