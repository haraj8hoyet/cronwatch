"""Alert routing: direct alert events to specific channels based on job tags or names."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List, Optional

from cronwatch.alerter import AlertEvent
from cronwatch.dispatch import Dispatcher


@dataclass
class RoutingRule:
    """A single rule mapping a job-name glob pattern to a named channel group."""

    pattern: str
    channel_group: str
    priority: int = 0

    def matches(self, job_name: str) -> bool:
        """Return True if *job_name* matches this rule's glob pattern."""
        return fnmatch.fnmatchcase(job_name, self.pattern)


class AlertRouter:
    """Routes an AlertEvent to the appropriate Dispatcher based on routing rules.

    Rules are evaluated in descending priority order.  The first matching rule
    determines which channel group (Dispatcher) receives the event.  If no rule
    matches, the *default* dispatcher is used.
    """

    def __init__(self, default: Dispatcher) -> None:
        self._default = default
        self._rules: List[RoutingRule] = []
        self._groups: dict[str, Dispatcher] = {}

    def register_group(self, name: str, dispatcher: Dispatcher) -> None:
        """Register a named Dispatcher that rules can reference."""
        self._groups[name] = dispatcher

    def add_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule; rules are kept sorted by priority (highest first)."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def resolve(self, event: AlertEvent) -> Dispatcher:
        """Return the Dispatcher that should handle *event*."""
        for rule in self._rules:
            if rule.matches(event.job_name):
                dispatcher = self._groups.get(rule.channel_group)
                if dispatcher is not None:
                    return dispatcher
        return self._default

    def route(self, event: AlertEvent) -> bool:
        """Dispatch *event* to the resolved channel group.  Returns True if at
        least one channel accepted the event."""
        dispatcher = self.resolve(event)
        return dispatcher.dispatch(event)

    @property
    def rule_count(self) -> int:
        return len(self._rules)
