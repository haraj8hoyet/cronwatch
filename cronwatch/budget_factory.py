"""Build an AlertBudget from CronwatchConfig / AlertConfig."""

from __future__ import annotations

from typing import Any

from cronwatch.budget import AlertBudget

_DEFAULT_WINDOW = 3600   # 1 hour
_DEFAULT_MAX    = 10


def build_alert_budget(config: Any | None) -> AlertBudget:
    """Construct an :class:`AlertBudget` from the alert section of the config.

    Reads ``config.alert.budget`` which may contain::

        budget:
          window_seconds: 3600
          max_alerts: 10

    Falls back to sensible defaults when the key is absent or *config* is None.
    """
    window = _DEFAULT_WINDOW
    max_alerts = _DEFAULT_MAX

    if config is None:
        return AlertBudget(window_seconds=window, max_alerts=max_alerts)

    alert_cfg = getattr(config, "alert", None)
    if alert_cfg is None:
        return AlertBudget(window_seconds=window, max_alerts=max_alerts)

    budget_cfg = getattr(alert_cfg, "budget", None)
    if isinstance(budget_cfg, dict):
        window = int(budget_cfg.get("window_seconds", window))
        max_alerts = int(budget_cfg.get("max_alerts", max_alerts))
    elif budget_cfg is not None:
        # Support simple object-style config (e.g. dataclass / SimpleNamespace)
        window = int(getattr(budget_cfg, "window_seconds", window))
        max_alerts = int(getattr(budget_cfg, "max_alerts", max_alerts))

    return AlertBudget(window_seconds=window, max_alerts=max_alerts)
