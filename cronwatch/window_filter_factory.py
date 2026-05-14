"""Build a WindowFilterRegistry from CronwatchConfig."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from cronwatch.window_filter import ActiveWindow, WindowFilterRegistry, _parse_time


_WEEKDAY_MAP: Dict[str, int] = {
    "mon": 1, "tue": 2, "wed": 3, "thu": 4,
    "fri": 5, "sat": 6, "sun": 7,
}


def _coerce_weekdays(raw: Optional[List[Any]]) -> List[int]:
    if not raw:
        return []
    result: List[int] = []
    for item in raw:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str):
            key = item.lower()[:3]
            if key in _WEEKDAY_MAP:
                result.append(_WEEKDAY_MAP[key])
            else:
                result.append(int(item))
    return result


def build_window_filter_registry(config: Any) -> WindowFilterRegistry:
    """Construct a WindowFilterRegistry from a CronwatchConfig instance.

    Expected config structure (alert section)::

        alert:
          active_windows:
            - name: business_hours
              start: "08:00"
              end: "18:00"
              weekdays: [mon, tue, wed, thu, fri]
    """
    registry = WindowFilterRegistry()
    alert_cfg = getattr(config, "alert", None)
    if alert_cfg is None:
        return registry

    raw_windows: Optional[List[Dict[str, Any]]] = getattr(
        alert_cfg, "active_windows", None
    )
    if not raw_windows:
        return registry

    for entry in raw_windows:
        if isinstance(entry, str):
            # bare "HH:MM-HH:MM" shorthand
            start_s, _, end_s = entry.partition("-")
            window = ActiveWindow(
                name=entry,
                start=_parse_time(start_s),
                end=_parse_time(end_s),
            )
        else:
            window = ActiveWindow(
                name=entry.get("name", "unnamed"),
                start=_parse_time(entry["start"]),
                end=_parse_time(entry["end"]),
                weekdays=_coerce_weekdays(entry.get("weekdays")),
            )
        registry.add_window(window)

    return registry
