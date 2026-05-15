"""Factory for building an AlertGrouper from CronwatchConfig."""
from __future__ import annotations

from typing import Optional

from cronwatch.grouping import AlertGrouper

_DEFAULT_WINDOW_SECONDS = 60.0
_MIN_WINDOW_SECONDS = 5.0
_MAX_WINDOW_SECONDS = 3600.0


def build_alert_grouper(cfg: Optional[object] = None) -> AlertGrouper:
    """Construct an :class:`AlertGrouper` from optional config.

    Reads ``cfg.alert.grouping_window_seconds`` when available.  Falls back
    to :data:`_DEFAULT_WINDOW_SECONDS` if the config is absent or the key is
    not set.  The window is clamped to [5, 3600] seconds to prevent
    misconfiguration from causing extreme behaviour.

    Parameters
    ----------
    cfg:
        A :class:`~cronwatch.config.CronwatchConfig` instance, or ``None``.

    Returns
    -------
    AlertGrouper
        Ready-to-use grouper instance.
    """
    window = _DEFAULT_WINDOW_SECONDS

    if cfg is not None:
        alert_cfg = getattr(cfg, "alert", None)
        if alert_cfg is not None:
            raw = getattr(alert_cfg, "grouping_window_seconds", None)
            if raw is not None:
                try:
                    window = float(raw)
                except (TypeError, ValueError):
                    pass

    window = max(_MIN_WINDOW_SECONDS, min(_MAX_WINDOW_SECONDS, window))
    return AlertGrouper(window_seconds=window)
