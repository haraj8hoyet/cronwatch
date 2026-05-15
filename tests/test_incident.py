"""Tests for cronwatch.incident — IncidentState, Incident, IncidentManager."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.incident import Incident, IncidentManager, IncidentState


def _event(job: str = "backup", kind: str = "failure") -> AlertEvent:
    ev = MagicMock(spec=AlertEvent)
    ev.job_name = job
    ev.kind = kind
    ev.exit_code = 1
    return ev


# ---------------------------------------------------------------------------
# Incident
# ---------------------------------------------------------------------------

def test_incident_initial_state():
    inc = Incident(job_name="backup")
    assert inc.state == IncidentState.OPEN
    assert inc.event_count == 0
    assert inc.is_open
    assert inc.resolved_at is None


def test_incident_add_event_increments_count():
    inc = Incident(job_name="backup")
    inc.add_event(_event())
    assert inc.event_count == 1


def test_incident_resolve_sets_state_and_timestamp():
    inc = Incident(job_name="backup")
    inc.resolve()
    assert inc.state == IncidentState.RESOLVED
    assert inc.resolved_at is not None
    assert not inc.is_open


def test_incident_resolve_idempotent():
    inc = Incident(job_name="backup")
    inc.resolve()
    first_ts = inc.resolved_at
    inc.resolve()  # second call should not change timestamp
    assert inc.resolved_at == first_ts


def test_incident_acknowledge_changes_state():
    inc = Incident(job_name="backup")
    inc.acknowledge()
    assert inc.state == IncidentState.ACKNOWLEDGED
    assert inc.is_open  # acknowledged is still open


def test_incident_str_contains_key_fields():
    inc = Incident(job_name="backup", incident_id="abc123")
    s = str(inc)
    assert "abc123" in s
    assert "backup" in s
    assert "open" in s


# ---------------------------------------------------------------------------
# IncidentManager
# ---------------------------------------------------------------------------

@pytest.fixture
def manager() -> IncidentManager:
    return IncidentManager()


def test_manager_creates_new_incident_on_first_event(manager):
    ev = _event("db_backup")
    inc = manager.open_or_update(ev)
    assert inc.job_name == "db_backup"
    assert inc.event_count == 1


def test_manager_reuses_open_incident_for_same_job(manager):
    ev1 = _event("db_backup")
    ev2 = _event("db_backup")
    inc1 = manager.open_or_update(ev1)
    inc2 = manager.open_or_update(ev2)
    assert inc1.incident_id == inc2.incident_id
    assert inc2.event_count == 2


def test_manager_creates_new_incident_after_resolution(manager):
    ev = _event("db_backup")
    inc1 = manager.open_or_update(ev)
    manager.resolve("db_backup")
    inc2 = manager.open_or_update(_event("db_backup"))
    assert inc1.incident_id != inc2.incident_id


def test_manager_resolve_returns_none_when_no_incident(manager):
    result = manager.resolve("nonexistent")
    assert result is None


def test_manager_open_incidents_excludes_resolved(manager):
    manager.open_or_update(_event("job_a"))
    manager.open_or_update(_event("job_b"))
    manager.resolve("job_a")
    open_names = [i.job_name for i in manager.open_incidents()]
    assert "job_b" in open_names
    assert "job_a" not in open_names


def test_manager_acknowledge(manager):
    manager.open_or_update(_event("job_a"))
    inc = manager.acknowledge("job_a")
    assert inc is not None
    assert inc.state == IncidentState.ACKNOWLEDGED


def test_manager_get_returns_none_for_unknown(manager):
    assert manager.get("ghost") is None
