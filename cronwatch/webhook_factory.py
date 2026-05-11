"""Factory helpers for constructing WebhookChannel instances from config."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cronwatch.webhook import WebhookChannel


def build_webhook_channels(alert_cfg: Optional[Any]) -> List[WebhookChannel]:
    """Return a list of WebhookChannel objects derived from AlertConfig.

    The config is expected to expose a ``webhooks`` attribute that is a list
    of dicts with at least a ``url`` key.  Missing or empty lists return [].
    """
    if alert_cfg is None:
        return []
    webhooks_raw = getattr(alert_cfg, "webhooks", None) or []
    channels: List[WebhookChannel] = []
    for entry in webhooks_raw:
        if isinstance(entry, str):
            entry = {"url": entry}
        channel = _channel_from_dict(entry)
        if channel is not None:
            channels.append(channel)
    return channels


def _channel_from_dict(cfg: Dict[str, Any]) -> Optional[WebhookChannel]:
    url = cfg.get("url", "").strip()
    if not url:
        return None
    return WebhookChannel(
        url=url,
        timeout=int(cfg.get("timeout", 10)),
        extra_headers=dict(cfg.get("headers", {})),
        secret_header=cfg.get("secret_header"),
        secret_value=cfg.get("secret_value"),
    )
