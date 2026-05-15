"""Factory: build a MetricSampler from CronwatchConfig."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from cronwatch.sampler import MetricSampler

if TYPE_CHECKING:
    from cronwatch.config import CronwatchConfig

_DEFAULT_DB = "cronwatch_metrics.db"


def build_metric_sampler(config: "CronwatchConfig | None" = None) -> MetricSampler:
    """Return a :class:`MetricSampler` wired to the configured database path.

    Resolution order for the database path:
    1. ``config.metrics_db`` (if present on the config object)
    2. ``CRONWATCH_METRICS_DB`` environment variable
    3. Hard-coded default ``cronwatch_metrics.db`` in the current directory
    """
    db_path = _resolve_db_path(config)
    return MetricSampler(db_path=db_path)


def _resolve_db_path(config: "CronwatchConfig | None") -> str:
    if config is not None:
        candidate = getattr(config, "metrics_db", None)
        if candidate:
            return str(candidate)
    env_val = os.environ.get("CRONWATCH_METRICS_DB", "").strip()
    if env_val:
        return env_val
    return _DEFAULT_DB
