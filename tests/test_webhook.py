"""Tests for cronwatch.webhook."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.webhook import WebhookChannel, _build_payload


@pytest.fixture()
def failure_event() -> AlertEvent:
    return AlertEvent(
        job_name="backup",
        kind="failure",
        exit_code=1,
        timestamp=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def channel() -> WebhookChannel:
    return WebhookChannel(url="https://example.com/hook", timeout=5)


def _fake_response(status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_build_payload_includes_required_fields(failure_event):
    payload = _build_payload(failure_event)
    assert payload["job"] == "backup"
    assert payload["kind"] == "failure"
    assert payload["exit_code"] == 1
    assert "timestamp" in payload


def test_build_payload_omits_exit_code_when_none():
    event = AlertEvent(job_name="ping", kind="missed", exit_code=None, timestamp=None)
    payload = _build_payload(event)
    assert "exit_code" not in payload
    assert "timestamp" not in payload


def test_send_returns_true_on_200(channel, failure_event):
    with patch("urllib.request.urlopen", return_value=_fake_response(200)):
        assert channel.send(failure_event) is True


def test_send_returns_false_on_500(channel, failure_event):
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
        channel.url, 500, "Internal Server Error", {}, None
    )):
        assert channel.send(failure_event) is False


def test_send_returns_false_on_url_error(channel, failure_event):
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("unreachable")):
        assert channel.send(failure_event) is False


def test_secret_header_included(failure_event):
    ch = WebhookChannel(
        url="https://example.com/hook",
        secret_header="X-Secret",
        secret_value="tok123",
    )
    captured_headers: dict = {}

    def fake_urlopen(req, timeout=None):
        captured_headers.update(req.headers)
        return _fake_response(200)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        ch.send(failure_event)

    assert captured_headers.get("X-secret") == "tok123"


def test_extra_headers_merged(failure_event):
    ch = WebhookChannel(
        url="https://example.com/hook",
        extra_headers={"X-Team": "ops"},
    )
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured.update(req.headers)
        return _fake_response(200)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        ch.send(failure_event)

    assert captured.get("X-team") == "ops"
