"""Tag-based filtering for cron job alerts and reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Iterable, List, Optional, Set


@dataclass
class TagFilter:
    """Matches jobs whose tag set satisfies include/exclude rules."""

    include: List[str] = field(default_factory=list)  # glob patterns
    exclude: List[str] = field(default_factory=list)  # glob patterns

    def matches(self, tags: Iterable[str]) -> bool:
        """Return True when *tags* pass include and exclude rules.

        - If *include* is empty, all tags are implicitly included.
        - A job is excluded when ANY of its tags matches an exclude pattern.
        - A job is included when ANY of its tags matches an include pattern
          (or include list is empty).
        """
        tag_set: Set[str] = set(tags)

        # Exclusion takes priority.
        for pattern in self.exclude:
            if any(fnmatch(t, pattern) for t in tag_set):
                return False

        if not self.include:
            return True

        for pattern in self.include:
            if any(fnmatch(t, pattern) for t in tag_set):
                return True

        return False


class TagFilterRegistry:
    """Holds named TagFilter instances and evaluates them against a job."""

    def __init__(self) -> None:
        self._filters: dict[str, TagFilter] = {}

    def register(self, name: str, tag_filter: TagFilter) -> None:
        """Register a named filter."""
        self._filters[name] = tag_filter

    def get(self, name: str) -> Optional[TagFilter]:
        """Return the filter registered under *name*, or None."""
        return self._filters.get(name)

    def any_match(self, tags: Iterable[str]) -> bool:
        """Return True when at least one registered filter matches *tags*."""
        tag_list = list(tags)
        return any(f.matches(tag_list) for f in self._filters.values())

    def all_match(self, tags: Iterable[str]) -> bool:
        """Return True when every registered filter matches *tags*."""
        tag_list = list(tags)
        if not self._filters:
            return False
        return all(f.matches(tag_list) for f in self._filters.values())

    @property
    def filter_count(self) -> int:
        return len(self._filters)
