"""Factory for building AlertEnvelopes from AlertEvents and job configuration."""
from __future__ import annotations

from typing import Optional

from cronwatch.alerter import AlertEvent
from cronwatch.config import JobConfig
from cronwatch.envelope import AlertEnvelope


def build_envelope(
    event: AlertEvent,
    job_cfg: Optional[JobConfig] = None,
) -> AlertEnvelope:
    """Create an AlertEnvelope from an event, optionally enriched with job metadata."""
    tags: list[str] = []
    labels: dict[str, str] = {}

    if job_cfg is not None:
        tags = list(getattr(job_cfg, "tags", None) or [])
        labels = dict(getattr(job_cfg, "labels", None) or {})

    # Always tag with the event kind for easy routing
    kind_tag = f"kind:{event.kind}"
    if kind_tag not in tags:
        tags.append(kind_tag)

    return AlertEnvelope(
        event=event,
        tags=tags,
        labels=labels,
    )
