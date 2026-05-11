"""Tests for cronwatch.webhook_factory."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, Optional

import pytest

from cronwatch.webhook import WebhookChannel
from cronwatch.webhook_factory import build_webhook_channels


def _cfg(webhooks: Optional[Any]) -> SimpleNamespace:
    return SimpleNamespace(webhooks=webhooks)


def test_returns_empty_when_no_alert_config():
    assert build_webhook_channels(None) == []


def test_returns_empty_when_webhooks_is_none():
    assert build_webhook_channels(_cfg(None)) == []


def test_returns_empty_when_webhooks_is_empty_list():
    assert build_webhook_channels(_cfg([])) == []


def test_single_url_string_creates_channel():
    cfg = _cfg(["https://hooks.example.com/notify"])
    channels = build_webhook_channels(cfg)
    assert len(channels) == 1
    assert isinstance(channels[0], WebhookChannel)
    assert channels[0].url == "https://hooks.example.com/notify"


def test_dict_entry_creates_channel_with_options():
    cfg = _cfg([{
        "url": "https://hooks.example.com/notify",
        "timeout": 30,
        "secret_header": "X-Token",
        "secret_value": "abc",
    }])
    channels = build_webhook_channels(cfg)
    assert len(channels) == 1
    ch = channels[0]
    assert ch.timeout == 30
    assert ch.secret_header == "X-Token"
    assert ch.secret_value == "abc"


def test_multiple_entries_all_created():
    cfg = _cfg([
        "https://a.example.com/hook",
        {"url": "https://b.example.com/hook", "timeout": 15},
    ])
    channels = build_webhook_channels(cfg)
    assert len(channels) == 2


def test_entry_with_empty_url_is_skipped():
    cfg = _cfg([{"url": "   "}, "https://valid.example.com/hook"])
    channels = build_webhook_channels(cfg)
    assert len(channels) == 1
    assert channels[0].url == "https://valid.example.com/hook"


def test_extra_headers_propagated():
    cfg = _cfg([{"url": "https://example.com", "headers": {"X-App": "cron"}}])
    channels = build_webhook_channels(cfg)
    assert channels[0].extra_headers == {"X-App": "cron"}
