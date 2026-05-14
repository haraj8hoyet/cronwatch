"""Tests for AlertEnvelope and EnvelopeStore."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.envelope import AlertEnvelope
from cronwatch.envelope_store import EnvelopeStore


@pytest.fixture()
def event() -> AlertEvent:
    ev = MagicMock(spec=AlertEvent)
    ev.job_name = "backup"
    ev.kind = "failure"
    return ev


@pytest.fixture()
def envelope(event: AlertEvent) -> AlertEnvelope:
    return AlertEnvelope(event=event, tags=["env:prod"], labels={"team": "ops"})


# --- AlertEnvelope unit tests ---

def test_initial_state(envelope: AlertEnvelope) -> None:
    assert not envelope.suppressed
    assert not envelope.delivered
    assert envelope.delivery_attempts == 0
    assert envelope.suppression_reason is None


def test_mark_suppressed(envelope: AlertEnvelope) -> None:
    envelope.mark_suppressed("rate limit")
    assert envelope.suppressed
    assert envelope.suppression_reason == "rate limit"


def test_mark_delivered(envelope: AlertEnvelope) -> None:
    envelope.mark_delivered()
    assert envelope.delivered


def test_record_attempt_increments(envelope: AlertEnvelope) -> None:
    envelope.record_attempt()
    envelope.record_attempt()
    assert envelope.delivery_attempts == 2


def test_add_route_deduplicates(envelope: AlertEnvelope) -> None:
    envelope.add_route("email")
    envelope.add_route("email")
    assert envelope.routed_to.count("email") == 1


def test_age_seconds_is_non_negative(envelope: AlertEnvelope) -> None:
    assert envelope.age_seconds >= 0.0


def test_str_shows_job_name(envelope: AlertEnvelope) -> None:
    assert "backup" in str(envelope)


def test_str_shows_pending_when_undelivered(envelope: AlertEnvelope) -> None:
    assert "pending" in str(envelope)


def test_str_shows_suppressed(envelope: AlertEnvelope) -> None:
    envelope.mark_suppressed("test")
    assert "suppressed" in str(envelope)


def test_str_shows_delivered(envelope: AlertEnvelope) -> None:
    envelope.mark_delivered()
    assert "delivered" in str(envelope)


# --- EnvelopeStore unit tests ---

def test_store_put_and_count(event: AlertEvent) -> None:
    store = EnvelopeStore()
    store.put(AlertEnvelope(event=event))
    assert store.count() == 1


def test_store_all_returns_list(event: AlertEvent) -> None:
    store = EnvelopeStore()
    e1 = AlertEnvelope(event=event)
    e2 = AlertEnvelope(event=event)
    store.put(e1)
    store.put(e2)
    result = store.all()
    assert len(result) == 2


def test_store_for_job_filters(event: AlertEvent) -> None:
    other = MagicMock(spec=AlertEvent)
    other.job_name = "other"
    other.kind = "failure"
    store = EnvelopeStore()
    store.put(AlertEnvelope(event=event))
    store.put(AlertEnvelope(event=other))
    assert len(store.for_job("backup")) == 1


def test_store_pending_excludes_delivered(event: AlertEvent) -> None:
    store = EnvelopeStore()
    e = AlertEnvelope(event=event)
    e.mark_delivered()
    store.put(e)
    assert store.pending() == []


def test_store_suppressed_list(event: AlertEvent) -> None:
    store = EnvelopeStore()
    e = AlertEnvelope(event=event)
    e.mark_suppressed("test")
    store.put(e)
    assert len(store.suppressed()) == 1


def test_store_respects_max_size(event: AlertEvent) -> None:
    store = EnvelopeStore(max_size=3)
    for _ in range(5):
        store.put(AlertEnvelope(event=event))
    assert store.count() == 3


def test_store_clear(event: AlertEvent) -> None:
    store = EnvelopeStore()
    store.put(AlertEnvelope(event=event))
    store.clear()
    assert store.count() == 0
