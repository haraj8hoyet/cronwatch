"""Alert envelope — wraps an AlertEvent with routing metadata for pipeline processing."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatch.alerter import AlertEvent


@dataclass
class AlertEnvelope:
    """Carries an AlertEvent through the alert pipeline with metadata."""

    event: AlertEvent
    envelope_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    routed_to: List[str] = field(default_factory=list)
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    delivered: bool = False
    delivery_attempts: int = 0

    def mark_suppressed(self, reason: str) -> None:
        """Mark this envelope as suppressed with the given reason."""
        self.suppressed = True
        self.suppression_reason = reason

    def mark_delivered(self) -> None:
        """Mark this envelope as successfully delivered."""
        self.delivered = True

    def record_attempt(self) -> None:
        """Increment the delivery attempt counter."""
        self.delivery_attempts += 1

    def add_route(self, channel_name: str) -> None:
        """Record that this envelope was routed to a named channel."""
        if channel_name not in self.routed_to:
            self.routed_to.append(channel_name)

    @property
    def age_seconds(self) -> float:
        """Return the age of this envelope in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    def __str__(self) -> str:
        status = "suppressed" if self.suppressed else ("delivered" if self.delivered else "pending")
        return (
            f"AlertEnvelope({self.envelope_id[:8]} job={self.event.job_name!r} "
            f"status={status} attempts={self.delivery_attempts})"
        )
