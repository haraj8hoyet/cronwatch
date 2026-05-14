"""Build an AlertRouter from CronwatchConfig."""

from __future__ import annotations

from typing import Optional

from cronwatch.channel_factory import build_dispatcher
from cronwatch.config import CronwatchConfig
from cronwatch.dispatch import Dispatcher
from cronwatch.routing import AlertRouter, RoutingRule


def build_alert_router(cfg: CronwatchConfig) -> AlertRouter:
    """Construct an AlertRouter from *cfg*.

    The ``alert.routing`` key (optional) is expected to be a list of dicts:

    .. code-block:: yaml

        alert:
          routing:
            - pattern: "backup_*"
              channel_group: ops
              priority: 10
          channel_groups:
            ops:
              email:
                smtp_host: mail.example.com
                to: [ops@example.com]
    """
    default_dispatcher = build_dispatcher(cfg)
    router = AlertRouter(default=default_dispatcher)

    alert_cfg = cfg.alert if cfg.alert else None
    if alert_cfg is None:
        return router

    raw_groups: dict = getattr(alert_cfg, "channel_groups", None) or {}
    for group_name, group_alert_cfg in raw_groups.items():
        group_dispatcher = build_dispatcher(
            CronwatchConfig(jobs=[], alert=group_alert_cfg)
        )
        router.register_group(group_name, group_dispatcher)

    raw_rules = getattr(alert_cfg, "routing", None) or []
    for entry in raw_rules:
        if isinstance(entry, dict):
            rule = RoutingRule(
                pattern=entry.get("pattern", "*"),
                channel_group=entry.get("channel_group", ""),
                priority=int(entry.get("priority", 0)),
            )
            router.add_rule(rule)

    return router
