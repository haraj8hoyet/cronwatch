"""Label-based alert filtering for cronwatch.

Allows alerts to be filtered by arbitrary key-value labels attached to
job configs, supporting exact-match and glob-pattern values.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LabelFilter:
    """Matches alerts whose labels satisfy all required key-value constraints."""

    required: Dict[str, str] = field(default_factory=dict)

    def matches(self, labels: Dict[str, str]) -> bool:
        """Return True if *labels* satisfies every required constraint.

        An empty filter matches everything.  Each required value is treated as
        a glob pattern so ``"prod-*"`` matches ``"prod-web"``.
        """
        for key, pattern in self.required.items():
            value = labels.get(key)
            if value is None:
                return False
            if not fnmatch.fnmatch(value, pattern):
                return False
        return True


class LabelFilterRegistry:
    """Registry that maps named groups to their :class:`LabelFilter`."""

    def __init__(self) -> None:
        self._filters: Dict[str, LabelFilter] = {}

    def register(self, group: str, label_filter: LabelFilter) -> None:
        """Register *label_filter* under *group*."""
        self._filters[group] = label_filter

    def get(self, group: str) -> Optional[LabelFilter]:
        """Return the filter registered for *group*, or ``None``."""
        return self._filters.get(group)

    def matches_any(self, labels: Dict[str, str]) -> bool:
        """Return True if *labels* matches at least one registered filter.

        Returns True when the registry is empty (no restrictions).
        """
        if not self._filters:
            return True
        return any(f.matches(labels) for f in self._filters.values())

    def matching_groups(self, labels: Dict[str, str]) -> List[str]:
        """Return the names of all groups whose filter matches *labels*."""
        return [name for name, f in self._filters.items() if f.matches(labels)]

    def __len__(self) -> int:
        return len(self._filters)
