"""Tests for cronwatch.notifier and cronwatch.dispatch."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.dispatch import Dispatcher
from cronwatch.notifier import EmailChannel, LogChannel


@pytest.fixture()
def failure_event() -> AlertEvent:
    return AlertEvent(
        job_name="nightly-backup",
        event_type="failure",
        exit_code=1,
        duration=42.0,
        message="Job exited with code 1",
    )


# ---------------------------------------------------------------------------
# LogChannel
# ---------------------------------------------------------------------------

def test_log_channel_returns_true(failure_event: AlertEvent) -> None:
    channel = LogChannel()
    assert channel.send(failure_event) is True


def test_log_channel_writes_subject(failure_event: AlertEvent, caplog) -> None:
    channel = LogChannel(level=logging.WARNING)
    with caplog.at_level(logging.WARNING, logger="cronwatch.notifier"):
        channel.send(failure_event)
    assert failure_event.subject in caplog.text


# ---------------------------------------------------------------------------
# EmailChannel
# ---------------------------------------------------------------------------

def test_email_channel_sends_message(failure_event: AlertEvent) -> None:
    channel = EmailChannel(
        smtp_host="localhost",
        smtp_port=25,
        sender="cronwatch@example.com",
        recipients=["ops@example.com"],
        use_tls=False,
    )
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    with patch("cronwatch.notifier.smtplib.SMTP", return_value=mock_smtp):
        result = channel.send(failure_event)
    assert result is True
    mock_smtp.send_message.assert_called_once()


def test_email_channel_returns_false_on_smtp_error(failure_event: AlertEvent) -> None:
    import smtplib

    channel = EmailChannel(
        smtp_host="bad-host",
        smtp_port=25,
        sender="a@b.com",
        recipients=["c@d.com"],
        use_tls=False,
    )
    with patch("cronwatch.notifier.smtplib.SMTP", side_effect=smtplib.SMTPException("err")):
        result = channel.send(failure_event)
    assert result is False


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def test_dispatcher_calls_all_channels(failure_event: AlertEvent) -> None:
    ch1 = MagicMock(spec=["send"])
    ch1.send.return_value = True
    ch2 = MagicMock(spec=["send"])
    ch2.send.return_value = False
    dispatcher = Dispatcher([ch1, ch2])
    results = dispatcher.dispatch(failure_event)
    ch1.send.assert_called_once_with(failure_event)
    ch2.send.assert_called_once_with(failure_event)
    assert len(results) == 2


def test_dispatcher_handles_channel_exception(failure_event: AlertEvent) -> None:
    bad_channel = MagicMock(spec=["send"])
    bad_channel.send.side_effect = RuntimeError("boom")
    dispatcher = Dispatcher([bad_channel])
    results = dispatcher.dispatch(failure_event)
    assert results["MagicMock"] is False


def test_dispatcher_empty_channels_returns_empty(failure_event: AlertEvent) -> None:
    dispatcher = Dispatcher()
    results = dispatcher.dispatch(failure_event)
    assert results == {}


def test_dispatcher_register_increases_count() -> None:
    dispatcher = Dispatcher()
    assert dispatcher.channel_count == 0
    dispatcher.register(LogChannel())
    assert dispatcher.channel_count == 1
