"""Alert suppression rules based on job tags or name patterns."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SuppressionRule:
    """A single suppression rule matching job names by glob or regex."""

    pattern: str
    use_regex: bool = False
    reason: str = ""

    def matches(self, job_name: str) -> bool:
        """Return True if *job_name* is matched by this rule."""
        if self.use_regex:
            return bool(re.search(self.pattern, job_name))
        return fnmatch.fnmatch(job_name, self.pattern)


@dataclass
class SuppressionRegistry:
    """Holds a collection of suppression rules and checks jobs against them."""

    _rules: List[SuppressionRule] = field(default_factory=list)

    def add_rule(self, rule: SuppressionRule) -> None:
        """Register a new suppression rule."""
        self._rules.append(rule)

    def is_suppressed(self, job_name: str) -> bool:
        """Return True if any registered rule matches *job_name*."""
        return any(r.matches(job_name) for r in self._rules)

    def matching_rule(self, job_name: str) -> Optional[SuppressionRule]:
        """Return the first rule that matches *job_name*, or None."""
        for rule in self._rules:
            if rule.matches(job_name):
                return rule
        return None

    def rule_count(self) -> int:
        """Return the number of registered rules."""
        return len(self._rules)

    def clear(self) -> None:
        """Remove all rules."""
        self._rules.clear()
