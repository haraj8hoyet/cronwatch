"""Alert escalation policy: upgrade severity after repeated failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class EscalationEntry:
    job_name: str
    consecutive_failures: int = 0
    last_failure: Optional[datetime] = None
    escalated: bool = False

    def record_failure(self, when: Optional[datetime] = None) -> None:
        self.consecutive_failures += 1
        self.last_failure = when or datetime.now(timezone.utc)

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.escalated = False
        self.last_failure = None

    def should_escalate(self, threshold: int) -> bool:
        """Return True when failures have reached the escalation threshold."""
        return self.consecutive_failures >= threshold and not self.escalated

    def mark_escalated(self) -> None:
        self.escalated = True


class EscalationPolicy:
    """Track per-job failure counts and decide when to escalate."""

    def __init__(self, threshold: int = 3) -> None:
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        self.threshold = threshold
        self._entries: Dict[str, EscalationEntry] = {}

    def _get(self, job_name: str) -> EscalationEntry:
        if job_name not in self._entries:
            self._entries[job_name] = EscalationEntry(job_name=job_name)
        return self._entries[job_name]

    def record_failure(self, job_name: str, when: Optional[datetime] = None) -> bool:
        """Record a failure; return True if this failure triggers escalation."""
        entry = self._get(job_name)
        entry.record_failure(when)
        if entry.should_escalate(self.threshold):
            entry.mark_escalated()
            return True
        return False

    def record_success(self, job_name: str) -> None:
        self._get(job_name).record_success()

    def consecutive_failures(self, job_name: str) -> int:
        return self._get(job_name).consecutive_failures

    def is_escalated(self, job_name: str) -> bool:
        return self._get(job_name).escalated

    def reset(self, job_name: str) -> None:
        self._entries.pop(job_name, None)
