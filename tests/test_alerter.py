"""Tests for cronwatch.alerter module."""

import smtplib
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerter import AlertEvent, Alerter
from cronwatch.config import AlertConfig


FIXED_TS = datetime(2024, 6, 1, 12, 0, 0)


@pytest.fixture
def failure_event():
    return AlertEvent(
        job_name="backup",
        event_type="failure",
        timestamp=FIXED_TS,
        exit_code=1,
        message="Disk full",
    )


@pytest.fixture
def missed_event():
    return AlertEvent(
        job_name="cleanup",
        event_type="missed",
        timestamp=FIXED_TS,
    )


def test_alert_event_subject(failure_event):
    assert failure_event.subject() == "[cronwatch] FAILURE: backup"


def test_alert_event_body_contains_fields(failure_event):
    body = failure_event.body()
    assert "backup" in body
    assert "failure" in body
    assert "1" in body
    assert "Disk full" in body


def test_alert_event_body_no_exit_code(missed_event):
    body = missed_event.body()
    assert "Exit code" not in body
    assert "missed" in body


def test_send_logs_when_no_channel(caplog, missed_event):
    alerter = Alerter(AlertConfig())
    with caplog.at_level("WARNING"):
        alerter.send(missed_event)
    assert "No alert channel configured" in caplog.text


def test_send_email_called(failure_event):
    email_cfg = {
        "from": "cronwatch@example.com",
        "to": ["ops@example.com"],
        "host": "smtp.example.com",
        "port": 587,
        "tls": False,
    }
    alerter = Alerter(AlertConfig(email=email_cfg))

    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("cronwatch.alerter.smtplib.SMTP", return_value=mock_smtp) as smtp_cls:
        alerter.send(failure_event)
        smtp_cls.assert_called_once_with("smtp.example.com", 587)
        mock_smtp.sendmail.assert_called_once()


def test_send_email_with_tls_and_auth(failure_event):
    email_cfg = {
        "from": "cronwatch@example.com",
        "to": ["ops@example.com"],
        "host": "smtp.example.com",
        "port": 587,
        "tls": True,
        "username": "user",
        "password": "secret",
    }
    alerter = Alerter(AlertConfig(email=email_cfg))
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("cronwatch.alerter.smtplib.SMTP", return_value=mock_smtp):
        alerter.send(failure_event)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user", "secret")
