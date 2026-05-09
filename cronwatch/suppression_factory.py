"""Build a SuppressionRegistry from CronwatchConfig."""

from __future__ import annotations

from typing import Any, Dict, List

from cronwatch.suppression import SuppressionRegistry, SuppressionRule


def build_suppression_registry(config: Any) -> SuppressionRegistry:
    """Construct a :class:`SuppressionRegistry` from the loaded config.

    The config object is expected to expose an ``alert`` attribute whose
    underlying dict may contain a ``suppress`` list.  Each entry may be:

    * a plain string  – treated as a glob pattern
    * a dict with keys ``pattern``, optional ``regex`` (bool), optional
      ``reason`` (str)

    If no suppression section is present an empty registry is returned.
    """
    registry = SuppressionRegistry()

    alert_cfg = getattr(config, "alert", None)
    if alert_cfg is None:
        return registry

    raw: List[Any] = getattr(alert_cfg, "suppress", None) or []

    for entry in raw:
        if isinstance(entry, str):
            registry.add_rule(SuppressionRule(pattern=entry))
        elif isinstance(entry, dict):
            registry.add_rule(
                SuppressionRule(
                    pattern=entry.get("pattern", ""),
                    use_regex=bool(entry.get("regex", False)),
                    reason=entry.get("reason", ""),
                )
            )

    return registry
