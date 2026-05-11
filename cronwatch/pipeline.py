"""Alert pipeline that chains throttle, dedup, suppression, silencer,
rate-limit, and tag-filter checks before dispatching an alert event.

The pipeline is the single integration point that every alert passes
through before reaching a notification channel.  Each stage can either
allow or block the event; when blocked the reason is recorded in the
audit log so operators can trace why an alert was not delivered.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.alerter import AlertEvent
from cronwatch.audit import AuditLog
from cronwatch.dedup import AlertDeduplicator
from cronwatch.dispatch import Dispatcher
from cronwatch.fingerprint import FingerprintGenerator
from cronwatch.ratelimit import RateLimitEntry
from cronwatch.silencer import AlertSilencer
from cronwatch.suppression import SuppressionRegistry
from cronwatch.tag_filter import TagFilterRegistry
from cronwatch.throttle import AlertThrottle

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Outcome of running an event through the alert pipeline."""

    delivered: bool
    blocked_by: Optional[str] = None  # name of the stage that blocked
    fingerprint: str = ""

    def __str__(self) -> str:  # pragma: no cover
        if self.delivered:
            return f"delivered (fp={self.fingerprint[:12]})"
        return f"blocked by {self.blocked_by} (fp={self.fingerprint[:12]})"


@dataclass
class AlertPipeline:
    """Ordered chain of alert-processing stages.

    Stages are evaluated in declaration order.  The first stage that
    blocks the event wins; remaining stages are skipped.

    Parameters
    ----------
    dispatcher:
        Final delivery target when all stages pass.
    throttle:
        Per-job cooldown between repeated alerts.
    deduplicator:
        Suppresses identical fingerprints within a time window.
    suppression_registry:
        Glob / regex rules that silence alerts by job name.
    silencer:
        Time-window based global silence periods.
    rate_limiter:
        Per-job rate-limit entry (max N alerts per window).
    tag_filter_registry:
        Only deliver alerts whose job tags satisfy the filter.
    audit_log:
        Optional audit sink; when provided every block decision is
        recorded for later review.
    """

    dispatcher: Dispatcher
    throttle: AlertThrottle = field(default_factory=AlertThrottle)
    deduplicator: AlertDeduplicator = field(default_factory=AlertDeduplicator)
    suppression_registry: SuppressionRegistry = field(
        default_factory=SuppressionRegistry
    )
    silencer: AlertSilencer = field(default_factory=AlertSilencer)
    rate_limiter: Optional[RateLimitEntry] = None
    tag_filter_registry: TagFilterRegistry = field(
        default_factory=TagFilterRegistry
    )
    audit_log: Optional[AuditLog] = None
    _fp_gen: FingerprintGenerator = field(
        default_factory=FingerprintGenerator, repr=False
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, event: AlertEvent) -> PipelineResult:
        """Run *event* through every stage and dispatch if all pass.

        Returns a :class:`PipelineResult` describing whether the event
        was delivered and, if not, which stage blocked it.
        """
        fp = self._fp_gen.generate(event)
        fp_short = fp.short

        # --- suppression ---
        if self.suppression_registry.is_suppressed(event.job_name):
            return self._block(event, "suppression", fp_short)

        # --- global silence window ---
        if self.silencer.is_silenced():
            return self._block(event, "silencer", fp_short)

        # --- tag filter ---
        tags = list(getattr(event, "tags", None) or [])
        if not self.tag_filter_registry.matches(event.job_name, tags):
            return self._block(event, "tag_filter", fp_short)

        # --- deduplication ---
        if not self.deduplicator.should_send(event.job_name, str(fp)):
            return self._block(event, "dedup", fp_short)

        # --- throttle ---
        if not self.throttle.should_send(event.job_name):
            return self._block(event, "throttle", fp_short)

        # --- rate limit ---
        if self.rate_limiter is not None:
            if not self.rate_limiter.is_allowed(event.job_name):
                return self._block(event, "rate_limit", fp_short)
            self.rate_limiter.record(event.job_name)

        # --- dispatch ---
        self.deduplicator.record(event.job_name, str(fp))
        self.throttle.record(event.job_name)
        self.dispatcher.dispatch(event)
        logger.debug("alert dispatched job=%s fp=%s", event.job_name, fp_short)
        return PipelineResult(delivered=True, fingerprint=fp_short)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _block(
        self, event: AlertEvent, stage: str, fp_short: str
    ) -> PipelineResult:
        logger.debug(
            "alert blocked stage=%s job=%s fp=%s", stage, event.job_name, fp_short
        )
        if self.audit_log is not None:
            self.audit_log.record(
                action="alert_blocked",
                actor="pipeline",
                detail=f"stage={stage} job={event.job_name} fp={fp_short}",
            )
        return PipelineResult(delivered=False, blocked_by=stage, fingerprint=fp_short)
