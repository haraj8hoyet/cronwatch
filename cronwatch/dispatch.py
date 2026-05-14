"""Dispatcher: fan-out an AlertEvent to all registered notification channels."""

from __future__ import annotations

from typing import List

from cronwatch.alerter import AlertEvent
from cronwatch.notifier import NotificationChannel


class Dispatcher:
    """Sends an AlertEvent to every registered NotificationChannel.

    Each channel's ``send`` method is called in registration order.  The
    overall result is ``True`` if *at least one* channel returned ``True``.
    """

    def __init__(self) -> None:
        self._channels: List[NotificationChannel] = []

    def register(self, channel: NotificationChannel) -> None:
        """Append *channel* to the dispatch list."""
        self._channels.append(channel)

    def dispatch(self, event: AlertEvent) -> bool:
        """Send *event* to all channels.  Returns True if any channel succeeded."""
        results = [ch.send(event) for ch in self._channels]
        return any(results)

    @property
    def channel_count(self) -> int:
        """Number of registered channels."""
        return len(self._channels)
