"""Incident tracking: groups related alert events into named incidents."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from cronwatch.alerter import AlertEvent


class IncidentState(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Incident:
    job_name: str
    incident_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: IncidentState = IncidentState.OPEN
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    events: List[AlertEvent] = field(default_factory=list)

    def add_event(self, event: AlertEvent) -> None:
        self.events.append(event)

    def resolve(self) -> None:
        if self.state != IncidentState.RESOLVED:
            self.state = IncidentState.RESOLVED
            self.resolved_at = datetime.now(timezone.utc)

    def acknowledge(self) -> None:
        if self.state == IncidentState.OPEN:
            self.state = IncidentState.ACKNOWLEDGED

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def is_open(self) -> bool:
        return self.state != IncidentState.RESOLVED

    def __str__(self) -> str:
        return (
            f"Incident({self.incident_id}) job={self.job_name} "
            f"state={self.state.value} events={self.event_count}"
        )


class IncidentManager:
    """Manages open/resolved incidents keyed by job name."""

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}

    def open_or_update(self, event: AlertEvent) -> Incident:
        """Return the active incident for the job, creating one if needed."""
        job = event.job_name
        if job not in self._incidents or not self._incidents[job].is_open:
            self._incidents[job] = Incident(job_name=job)
        incident = self._incidents[job]
        incident.add_event(event)
        return incident

    def resolve(self, job_name: str) -> Optional[Incident]:
        """Mark the active incident for a job as resolved."""
        incident = self._incidents.get(job_name)
        if incident and incident.is_open:
            incident.resolve()
            return incident
        return None

    def acknowledge(self, job_name: str) -> Optional[Incident]:
        incident = self._incidents.get(job_name)
        if incident and incident.state == IncidentState.OPEN:
            incident.acknowledge()
            return incident
        return None

    def get(self, job_name: str) -> Optional[Incident]:
        return self._incidents.get(job_name)

    def open_incidents(self) -> List[Incident]:
        return [i for i in self._incidents.values() if i.is_open]

    def all_incidents(self) -> List[Incident]:
        return list(self._incidents.values())
