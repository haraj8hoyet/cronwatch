"""Build a BackoffRegistry from CronwatchConfig / AlertConfig."""
from __future__ import annotations

from typing import Optional

from cronwatch.backoff import BackoffRegistry

_DEFAULT_BASE = 30.0
_DEFAULT_MAX = 3600.0
_DEFAULT_MULT = 2.0


def _registry_from_dict(backoff_cfg: dict) -> BackoffRegistry:
    """Build a BackoffRegistry from a validated backoff config dict.

    Raises ``ValueError`` if any numeric value is non-positive.
    """
    base_delay = float(backoff_cfg.get("base_delay", _DEFAULT_BASE))
    max_delay = float(backoff_cfg.get("max_delay", _DEFAULT_MAX))
    multiplier = float(backoff_cfg.get("multiplier", _DEFAULT_MULT))

    if base_delay <= 0:
        raise ValueError(f"backoff.base_delay must be positive, got {base_delay}")
    if max_delay <= 0:
        raise ValueError(f"backoff.max_delay must be positive, got {max_delay}")
    if multiplier <= 0:
        raise ValueError(f"backoff.multiplier must be positive, got {multiplier}")

    return BackoffRegistry(
        base_delay=base_delay,
        max_delay=max_delay,
        multiplier=multiplier,
    )


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

    return _registry_from_dict(backoff_cfg)
