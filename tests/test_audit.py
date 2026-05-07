"""Tests for cronwatch.audit."""

import time
import pytest

from cronwatch.audit import AuditEntry, AuditLog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "audit.db")


@pytest.fixture
def audit(db_path) -> AuditLog:
    return AuditLog(db_path)


# ---------------------------------------------------------------------------
# AuditEntry unit tests
# ---------------------------------------------------------------------------

def test_audit_entry_str_contains_fields():
    entry = AuditEntry(event_type="silenced", job_name="backup",
                       timestamp=0.0, detail="maintenance")
    text = str(entry)
    assert "silenced" in text
    assert "backup" in text
    assert "maintenance" in text


def test_audit_entry_str_no_trailing_space_when_no_detail():
    entry = AuditEntry(event_type="lifted", job_name="sync", timestamp=0.0)
    assert not str(entry).endswith(" ")


# ---------------------------------------------------------------------------
# AuditLog tests
# ---------------------------------------------------------------------------

def test_db_file_created(db_path):
    import os
    AuditLog(db_path)
    assert os.path.exists(db_path)


def test_record_returns_entry(audit):
    entry = audit.record("silenced", "nightly", detail="planned", now=1000.0)
    assert entry.event_type == "silenced"
    assert entry.job_name == "nightly"
    assert entry.timestamp == 1000.0
    assert entry.detail == "planned"


def test_query_returns_recorded_entries(audit):
    audit.record("silenced", "job_a", now=1000.0)
    audit.record("lifted", "job_a", now=2000.0)
    entries = audit.query(job_name="job_a")
    assert len(entries) == 2


def test_query_all_returns_all_jobs(audit):
    audit.record("silenced", "job_a", now=1000.0)
    audit.record("silenced", "job_b", now=1001.0)
    entries = audit.query()
    assert len(entries) == 2


def test_query_filtered_by_job(audit):
    audit.record("silenced", "job_a", now=1000.0)
    audit.record("silenced", "job_b", now=1001.0)
    entries = audit.query(job_name="job_a")
    assert all(e.job_name == "job_a" for e in entries)


def test_query_ordered_most_recent_first(audit):
    audit.record("silenced", "job_a", now=1000.0)
    audit.record("lifted", "job_a", now=2000.0)
    entries = audit.query(job_name="job_a")
    assert entries[0].timestamp > entries[1].timestamp


def test_query_limit_respected(audit):
    for i in range(10):
        audit.record("silenced", "job", now=float(i))
    entries = audit.query(limit=3)
    assert len(entries) == 3


def test_record_uses_real_time_when_now_not_given(audit):
    before = time.time()
    entry = audit.record("silenced", "job")
    after = time.time()
    assert before <= entry.timestamp <= after


def test_empty_query_returns_empty_list(audit):
    assert audit.query() == []
