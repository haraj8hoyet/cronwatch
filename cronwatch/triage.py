"""Alert triage: classify alerts by severity based on failure patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TriageResult:
    severity: Severity
    reason: str
    job_name: str
    consecutive_failures: int = 0
    is_missed: bool = False

    def __str__(self) -> str:
        return (
            f"[{self.severity.upper()}] {self.job_name}: {self.reason}"
            f" (consecutive_failures={self.consecutive_failures})"
        )


@dataclass
class TriagePolicy:
    warning_threshold: int = 1
    critical_threshold: int = 3
    missed_run_severity: Severity = Severity.WARNING


class AlertTriager:
    """Classify an alert event into a severity level."""

    def __init__(self, policy: Optional[TriagePolicy] = None) -> None:
        self._policy = policy or TriagePolicy()

    def triage(
        self,
        job_name: str,
        consecutive_failures: int,
        is_missed: bool = False,
    ) -> TriageResult:
        policy = self._policy

        if is_missed:
            return TriageResult(
                severity=policy.missed_run_severity,
                reason="missed scheduled run",
                job_name=job_name,
                consecutive_failures=consecutive_failures,
                is_missed=True,
            )

        if consecutive_failures >= policy.critical_threshold:
            severity = Severity.CRITICAL
            reason = f"failed {consecutive_failures} times in a row"
        elif consecutive_failures >= policy.warning_threshold:
            severity = Severity.WARNING
            reason = f"failed {consecutive_failures} time(s)"
        else:
            severity = Severity.INFO
            reason = "single transient failure"

        return TriageResult(
            severity=severity,
            reason=reason,
            job_name=job_name,
            consecutive_failures=consecutive_failures,
            is_missed=False,
        )
