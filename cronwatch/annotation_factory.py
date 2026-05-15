"""Build an AnnotationRegistry from CronwatchConfig."""
from __future__ import annotations

from typing import TYPE_CHECKING

from cronwatch.annotation import AnnotationRegistry

if TYPE_CHECKING:
    from cronwatch.config import CronwatchConfig


def build_annotation_registry(cfg: "CronwatchConfig | None") -> AnnotationRegistry:
    """Populate an AnnotationRegistry from job-level annotation config.

    Each job in *cfg.jobs* may carry an optional ``annotations`` mapping
    (``dict[str, str]``).  All entries are loaded with source ``'config'``.

    Returns an empty registry when *cfg* is None or carries no jobs.
    """
    registry = AnnotationRegistry()

    if cfg is None:
        return registry

    for job in cfg.jobs:
        raw = getattr(job, "annotations", None)
        if not raw or not isinstance(raw, dict):
            continue
        for key, value in raw.items():
            registry.annotate(job.name, str(key), str(value), source="config")

    return registry
