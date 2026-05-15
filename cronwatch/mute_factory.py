"""Build an AlertMuter from CronwatchConfig."""
from __future__ import annotations

from typing import TYPE_CHECKING

from cronwatch.mute import AlertMuter

if TYPE_CHECKING:
    from cronwatch.config import CronwatchConfig


def build_alert_muter(config: "CronwatchConfig") -> AlertMuter:
    """Construct an AlertMuter pre-populated with any statically configured
    mute windows defined under ``alert.mute`` in the config file.

    Each entry may be a plain job-name string (muted for 1 hour by default)
    or a mapping with keys ``job``, ``duration_seconds``, and optional
    ``reason``.

    Example YAML::

        alert:
          mute:
            - job: backup_job
              duration_seconds: 3600
              reason: "scheduled maintenance"
            - nightly_report
    """
    muter = AlertMuter()
    alert_cfg = getattr(config, "alert", None)
    if alert_cfg is None:
        return muter

    mute_list = getattr(alert_cfg, "mute", None) or []
    for entry in mute_list:
        if isinstance(entry, str):
            muter.mute(entry, duration_seconds=3600)
        elif isinstance(entry, dict):
            job_name = entry.get("job", "")
            duration = float(entry.get("duration_seconds", 3600))
            reason = entry.get("reason", "")
            if job_name:
                muter.mute(job_name, duration_seconds=duration, reason=reason)
    return muter
