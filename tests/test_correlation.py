"""Tests for cronwatch.correlation."""
from __future__ import annotations

import time

import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.correlation import AlertCorrelator, CorrelationEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(job: str = "backup", kind: str = "failure", exit_code: int = 1) -> AlertEvent:
    return AlertEvent(job_name=job, kind=kind, exit_code=exit_code)


@pytest.fixture()
def correlator() -> AlertCorrelator:
    return AlertCorrelator(window_seconds=60.0)


# ---------------------------------------------------------------------------
# CorrelationEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_initial_size_is_zero():
    entry = CorrelationEntry(incident_key="k", window_seconds=60.0)
    assert entry.size == 0


def test_entry_add_increments_size():
    entry = CorrelationEntry(incident_key="k", window_seconds=60.0)
    entry.add(_event())
    assert entry.size == 1


def test_entry_not_expired_within_window():
    entry = CorrelationEntry(incident_key="k", window_seconds=60.0)
    entry.add(_event())
    assert not entry.is_expired(time.monotonic())


def test_entry_expired_after_window():
    entry = CorrelationEntry(incident_key="k", window_seconds=60.0)
    entry.add(_event())
    future = time.monotonic() + 120.0
    assert entry.is_expired(future)


# ---------------------------------------------------------------------------
# AlertCorrelator tests
# ---------------------------------------------------------------------------

def test_add_creates_new_entry(correlator):
    ev = _event()
    entry = correlator.add(ev)
    assert entry.size == 1
    assert correlator.active_count == 1


def test_add_same_job_and_kind_groups_together(correlator):
    ev1 = _event()
    ev2 = _event()
    correlator.add(ev1)
    entry = correlator.add(ev2)
    assert entry.size == 2
    assert correlator.active_count == 1


def test_add_different_kind_creates_separate_entry(correlator):
    correlator.add(_event(kind="failure"))
    correlator.add(_event(kind="missed"))
    assert correlator.active_count == 2


def test_add_different_job_creates_separate_entry(correlator):
    correlator.add(_event(job="backup"))
    correlator.add(_event(job="cleanup"))
    assert correlator.active_count == 2


def test_get_returns_none_for_unknown_event(correlator):
    assert correlator.get(_event()) is None


def test_get_returns_entry_after_add(correlator):
    ev = _event()
    correlator.add(ev)
    result = correlator.get(ev)
    assert result is not None
    assert result.size == 1


def test_flush_expired_removes_stale_entries(correlator):
    ev = _event()
    correlator.add(ev)
    future = time.monotonic() + 200.0
    expired = correlator.flush_expired(now=future)
    assert len(expired) == 1
    assert correlator.active_count == 0


def test_flush_expired_keeps_fresh_entries(correlator):
    correlator.add(_event())
    expired = correlator.flush_expired(now=time.monotonic())
    assert expired == []
    assert correlator.active_count == 1


def test_expired_entry_replaced_on_next_add(correlator):
    ev = _event()
    first = correlator.add(ev)
    future = time.monotonic() + 200.0
    correlator.flush_expired(now=future)
    # Simulate time passing so new entry is created
    second = correlator.add(ev)
    assert second is not first
    assert second.size == 1
