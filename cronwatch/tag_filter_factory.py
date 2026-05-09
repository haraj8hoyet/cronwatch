"""Build a TagFilterRegistry from alert configuration."""
from __future__ import annotations

from typing import Any, Dict, Optional

from cronwatch.tag_filter import TagFilter, TagFilterRegistry


def build_tag_filter_registry(
    alert_cfg: Optional[Any] = None,
) -> TagFilterRegistry:
    """Construct a :class:`TagFilterRegistry` from *alert_cfg*.

    Expected shape of ``alert_cfg.tag_filters`` (list of dicts)::

        tag_filters:
          - name: critical
            include: ["critical", "prod-*"]
            exclude: ["test"]
          - name: ignore-batch
            exclude: ["batch"]

    If *alert_cfg* is None or has no ``tag_filters`` attribute the returned
    registry is empty.
    """
    registry = TagFilterRegistry()

    if alert_cfg is None:
        return registry

    raw: Any = getattr(alert_cfg, "tag_filters", None)
    if not raw:
        return registry

    for entry in raw:
        if isinstance(entry, dict):
            name: str = entry.get("name", "")
            if not name:
                continue
            include = _coerce_list(entry.get("include", []))
            exclude = _coerce_list(entry.get("exclude", []))
        else:
            # Plain string — treat as a single include glob with auto-name.
            name = str(entry)
            include = [name]
            exclude = []

        registry.register(name, TagFilter(include=include, exclude=exclude))

    return registry


def _coerce_list(value: Any) -> list:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [value]
    return []
