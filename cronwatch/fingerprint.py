"""Alert fingerprinting — generates stable identifiers for alert events
so that downstream components (dedup, throttle, audit) can correlate
alerts for the same logical failure across multiple occurrences."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional

from cronwatch.alerter import AlertEvent


@dataclass
class AlertFingerprint:
    """Stable identifier derived from an AlertEvent."""

    job_name: str
    alert_type: str  # 'failure' | 'missed'
    exit_code: Optional[int]
    hex_digest: str

    def __str__(self) -> str:
        return self.hex_digest

    def short(self) -> str:
        """Return first 12 hex characters for compact display."""
        return self.hex_digest[:12]


class FingerprintGenerator:
    """Generates deterministic fingerprints for AlertEvent instances.

    The fingerprint is based on fields that identify *what went wrong*
    (job name, alert type, exit code) rather than *when* it happened,
    so repeated failures produce the same fingerprint.
    """

    def generate(self, event: AlertEvent) -> AlertFingerprint:
        """Return an AlertFingerprint for *event*."""
        alert_type = self._classify(event)
        payload = json.dumps(
            {
                "job": event.job_name,
                "type": alert_type,
                "exit_code": event.exit_code,
            },
            sort_keys=True,
        ).encode()
        digest = hashlib.sha256(payload).hexdigest()
        return AlertFingerprint(
            job_name=event.job_name,
            alert_type=alert_type,
            exit_code=event.exit_code,
            hex_digest=digest,
        )

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify(event: AlertEvent) -> str:
        if event.exit_code is None:
            return "missed"
        return "failure"
