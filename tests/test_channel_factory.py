"""Tests for cronwatch.channel_factory."""

from __future__ import annotations

import pytest

from cronwatch.channel_factory import build_dispatcher
from cronwatch.config import AlertConfig
from cronwatch.notifier import EmailChannel, LogChannel


@pytest.fixture()
def minimal_alert_cfg() -> AlertConfig:
    """AlertConfig with no channels configured."""
    return AlertConfig(email=None, log_fallback=False)


@pytest.fixture()
def email_alert_cfg() -> AlertConfig:
    return AlertConfig(
        email={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "sender": "cronwatch@example.com",
            "recipients": ["ops@example.com"],
            "use_tls": True,
        },
        log_fallback=False,
    )


@pytest.fixture()
def log_fallback_cfg() -> AlertConfig:
    return AlertConfig(email=None, log_fallback=True)


def test_no_channels_adds_log_default(minimal_alert_cfg: AlertConfig) -> None:
    dispatcher = build_dispatcher(minimal_alert_cfg)
    assert dispatcher.channel_count == 1
    assert isinstance(dispatcher._channels[0], LogChannel)


def test_email_channel_registered(email_alert_cfg: AlertConfig) -> None:
    dispatcher = build_dispatcher(email_alert_cfg)
    types = [type(c) for c in dispatcher._channels]
    assert EmailChannel in types


def test_log_fallback_registered(log_fallback_cfg: AlertConfig) -> None:
    dispatcher = build_dispatcher(log_fallback_cfg)
    types = [type(c) for c in dispatcher._channels]
    assert LogChannel in types


def test_email_and_log_fallback_both_registered() -> None:
    cfg = AlertConfig(
        email={
            "smtp_host": "localhost",
            "smtp_port": 25,
            "sender": "a@b.com",
            "recipients": ["c@d.com"],
        },
        log_fallback=True,
    )
    dispatcher = build_dispatcher(cfg)
    assert dispatcher.channel_count == 2
    types = {type(c) for c in dispatcher._channels}
    assert types == {EmailChannel, LogChannel}


def test_email_channel_smtp_host_set(email_alert_cfg: AlertConfig) -> None:
    dispatcher = build_dispatcher(email_alert_cfg)
    email_ch = next(c for c in dispatcher._channels if isinstance(c, EmailChannel))
    assert email_ch.smtp_host == "smtp.example.com"
    assert email_ch.smtp_port == 587
    assert email_ch.recipients == ["ops@example.com"]
