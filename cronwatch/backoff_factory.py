"""Build a BackoffRegistry from CronwatchConfig / AlertConfig."""
from __future__ import annotations

from typing import Optional

from cronwatch.backoff import BackoffRegistry

_DEFAULT_BASE = 30.0
_DEFAULT_MAX = 3600.0
_DEFAULT_MULT = 2.0


def build_backoff_registry(alert_config: Optional[object] = None) -> BackoffRegistry:
    """Return a BackoffRegistry configured from *alert_config*.

    Falls back to sensible defaults when *alert_config* is ``None`` or when
    the ``backoff`` sub-key is absent.
    """
    if alert_config is None:
        return BackoffRegistry(
            base_delay=_DEFAULT_BASE,
            max_delay=_DEFAULT_MAX,
            multiplier=_DEFAULT_MULT,
        )

    backoff_cfg: Optional[dict] = getattr(alert_config, "backoff", None)
    if not isinstance(backoff_cfg, dict):
        return BackoffRegistry(
            base_delay=_DEFAULT_BASE,
            max_delay=_DEFAULT_MAX,
            multiplier=_DEFAULT_MULT,
        )

    return BackoffRegistry(
        base_delay=float(backoff_cfg.get("base_delay", _DEFAULT_BASE)),
        max_delay=float(backoff_cfg.get("max_delay", _DEFAULT_MAX)),
        multiplier=float(backoff_cfg.get("multiplier", _DEFAULT_MULT)),
    )
