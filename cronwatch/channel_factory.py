"""Build notification channels from CronwatchConfig."""

from __future__ import annotations

import logging

from cronwatch.config import AlertConfig
from cronwatch.dispatch import Dispatcher
from cronwatch.notifier import EmailChannel, LogChannel

logger = logging.getLogger(__name__)


def build_dispatcher(alert_cfg: AlertConfig) -> Dispatcher:
    """Construct a :class:`Dispatcher` wired with channels from *alert_cfg*."""
    dispatcher = Dispatcher()

    if alert_cfg.email:
        email_cfg = alert_cfg.email
        channel = EmailChannel(
            smtp_host=email_cfg.get("smtp_host", "localhost"),
            smtp_port=int(email_cfg.get("smtp_port", 25)),
            sender=email_cfg["sender"],
            recipients=email_cfg["recipients"],
            username=email_cfg.get("username"),
            password=email_cfg.get("password"),
            use_tls=bool(email_cfg.get("use_tls", True)),
        )
        dispatcher.register(channel)
        logger.debug("Registered EmailChannel (host=%s)", email_cfg.get("smtp_host"))

    if alert_cfg.log_fallback:
        dispatcher.register(LogChannel())
        logger.debug("Registered LogChannel as fallback")

    if dispatcher.channel_count == 0:
        logger.warning(
            "No notification channels configured; adding LogChannel as default."
        )
        dispatcher.register(LogChannel())

    return dispatcher
