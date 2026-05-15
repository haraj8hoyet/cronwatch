"""Tests for cronwatch.incident_store — IncidentStore."""
from __future__ import annotations

from pathlib import Path

import pytest

from cronwatch.incident import Incident, IncidentState
from cronwatch.incident_store import IncidentStore


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "incidents.db"


@pytest.fixture
def store(db_path: Path) -> IncidentStore:
    s = IncidentStore(db_path)
    yield s
    s.close()


def _make_incident(job: str = "backup") -> Incident:
    return Incident(job_name=job)


def test_db_file_is_created(db_path, store):
    assert db_path.exists()


def test_save_and_load_roundtrip(store):
    inc = _make_incident("nightly")
    store.save(inc)
    loaded = store.load(inc.incident_id)
    assert loaded is not None
    assert loaded.incident_id == inc.incident_id
    assert loaded.job_name == "nightly"
    assert loaded.state == IncidentState.OPEN


def test_load_returns_none_for_unknown(store):
    assert store.load("does-not-exist") is None


def test_save_updates_existing_record(store):
    inc = _make_incident("daily")
    store.save(inc)
    inc.resolve()
    store.save(inc)
    loaded = store.load(inc.incident_id)
    assert loaded.state == IncidentState.RESOLVED
    assert loaded.resolved_at is not None


def test_open_for_job_returns_open_incident(store):
    inc = _make_incident("sync")
    store.save(inc)
    result = store.open_for_job("sync")
    assert result is not None
    assert result.incident_id == inc.incident_id


def test_open_for_job_returns_none_when_resolved(store):
    inc = _make_incident("sync")
    inc.resolve()
    store.save(inc)
    result = store.open_for_job("sync")
    assert result is None


def test_recent_returns_latest_first(store):
    for name in ["job_a", "job_b", "job_c"]:
        store.save(_make_incident(name))
    results = store.recent(limit=10)
    assert len(results) == 3


def test_recent_respects_limit(store):
    for i in range(5):
        store.save(_make_incident(f"job_{i}"))
    results = store.recent(limit=3)
    assert len(results) == 3


def test_event_count_persisted(store):
    inc = _make_incident("counter")
    from unittest.mock import MagicMock
    from cronwatch.alerter import AlertEvent
    ev = MagicMock(spec=AlertEvent)
    ev.job_name = "counter"
    inc.add_event(ev)
    inc.add_event(ev)
    store.save(inc)
    loaded = store.load(inc.incident_id)
    assert loaded.event_count == 2
