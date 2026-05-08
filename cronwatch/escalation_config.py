"""Load and validate escalation settings from CronwatchConfig."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cronwatch.config import AlertConfig


_DEFAULT_THRESHOLD = 3
_DEFAULT_COOLDOWN_MINUTES = 60


@dataclass(frozen=True)
class EscalationSettings:
    """Parsed escalation parameters derived from AlertConfig."""
    threshold: int
    cooldown_minutes: int
    notify_on_recovery: bool

    @classmethod
    def from_alert_config(cls, cfg: Optional[AlertConfig]) -> "EscalationSettings":
        """Build EscalationSettings from an AlertConfig, applying defaults."""
        if cfg is None:
            return cls(
                threshold=_DEFAULT_THRESHOLD,
                cooldown_minutes=_DEFAULT_COOLDOWN_MINUTES,
                notify_on_recovery=True,
            )
        raw = cfg.extra if hasattr(cfg, "extra") and cfg.extra else {}
        escalation_raw = raw.get("escalation", {})

        threshold = int(escalation_raw.get("threshold", _DEFAULT_THRESHOLD))
        if threshold < 1:
            raise ValueError(f"escalation.threshold must be >= 1, got {threshold}")

        cooldown = int(escalation_raw.get("cooldown_minutes", _DEFAULT_COOLDOWN_MINUTES))
        if cooldown < 0:
            raise ValueError(f"escalation.cooldown_minutes must be >= 0, got {cooldown}")

        notify_recovery = bool(escalation_raw.get("notify_on_recovery", True))

        return cls(
            threshold=threshold,
            cooldown_minutes=cooldown,
            notify_on_recovery=notify_recovery,
        )


def build_escalation_policy_from_config(
    cfg: Optional[AlertConfig],
) -> "EscalationSettings":
    """Convenience wrapper used by the watcher to obtain escalation settings."""
    return EscalationSettings.from_alert_config(cfg)
