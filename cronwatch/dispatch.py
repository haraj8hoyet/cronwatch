"""Dispatcher that routes AlertEvents to one or more notification channels."""

from __future__ import annotations

import logging
from typing import Iterable

from cronwatch.alerter import AlertEvent
from cronwatch.notifier import NotificationChannel

logger = logging.getLogger(__name__)


class Dispatcher:
    """Sends an AlertEvent through all registered channels."""

    def __init__(self, channels: Iterable[NotificationChannel] | None = None) -> None:
        self._channels: list[NotificationChannel] = list(channels or [])

    def register(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self._channels.append(channel)

    def dispatch(self, event: AlertEvent) -> dict[str, bool]:
        """Dispatch *event* to all channels.

        Returns a mapping of channel class name -> success bool.
        """
        results: dict[str, bool] = {}
        if not self._channels:
            logger.warning("No notification channels registered; alert dropped.")
            return results
        for channel in self._channels:
            name = type(channel).__name__
            try:
                ok = channel.send(event)
            except Exception as exc:  # noqa: BLE001
                logger.error("Channel %s raised an exception: %s", name, exc)
                ok = False
            results[name] = ok
        return results

    @property
    def channel_count(self) -> int:
        return len(self._channels)
