"""Tests for cronwatch.heartbeat module."""

from datetime import datetime, timedelta

import pytest

from cronwatch.heartbeat import HeartbeatMonitor, HeartbeatRecord


# ---------------------------------------------------------------------------
# HeartbeatRecord
# ---------------------------------------------------------------------------

def test_record_not_stale_when_never_seen():
    record = HeartbeatRecord(job_name="backup", grace_seconds=30)
    assert record.is_stale() is False


def test_record_not_stale_within_grace():
    record = HeartbeatRecord(job_name="backup", grace_seconds=60)
    now = datetime.utcnow()
    record.touch(at=now - timedelta(seconds=30))
    assert record.is_stale(now=now) is False


def test_record_stale_after_grace_exceeded():
    record = HeartbeatRecord(job_name="backup", grace_seconds=60)
    now = datetime.utcnow()
    record.touch(at=now - timedelta(seconds=90))
    assert record.is_stale(now=now) is True


def test_touch_updates_last_seen():
    record = HeartbeatRecord(job_name="backup", grace_seconds=60)
    assert record.last_seen is None
    record.touch()
    assert record.last_seen is not None


def test_record_stale_exactly_at_grace_boundary():
    """A record touched exactly grace_seconds ago should be considered stale."""
    record = HeartbeatRecord(job_name="backup", grace_seconds=60)
    now = datetime.utcnow()
    record.touch(at=now - timedelta(seconds=60))
    assert record.is_stale(now=now) is True


# ---------------------------------------------------------------------------
# HeartbeatMonitor
# ---------------------------------------------------------------------------

@pytest.fixture()
def monitor() -> HeartbeatMonitor:
    m = HeartbeatMonitor()
    m.register("job_a", grace_seconds=60)
    m.register("job_b", grace_seconds=120)
    return m


def test_register_adds_jobs(monitor):
    assert len(monitor) == 2


def test_register_idempotent(monitor):
    monitor.register("job_a", grace_seconds=60)
    assert len(monitor) == 2


def test_touch_unknown_job_raises(monitor):
    with pytest.raises(KeyError, match="not registered"):
        monitor.touch("unknown_job")


def test_no_stale_jobs_initially(monitor):
    """Jobs with no last_seen are not considered stale."""
    assert monitor.stale_jobs() == []


def test_stale_jobs_detected(monitor):
    now = datetime.utcnow()
    old_ts = now - timedelta(seconds=200)
    monitor.touch("job_a", at=old_ts)
    monitor.touch("job_b", at=old_ts)
    stale = monitor.stale_jobs(now=now)
    assert "job_a" in stale
    assert "job_b" in stale


def test_fresh_job_not_stale(monitor):
    now = datetime.utcnow()
    monitor.touch("job_a", at=now - timedelta(seconds=10))
    monitor.touch("job_b", at=now - timedelta(seconds=200))
    stale = monitor.stale_jobs(now=now)
    assert "job_a" not in stale
    assert "job_b" in stale


def test_touch_advances_last_seen(monitor):
    """Calling touch twice should update last_seen to the more recent timestamp."""
    now = datetime.utcnow()
    earlier = now - timedelta(seconds=50)
    monitor.touch("job_a", at=earlier)
    monitor.touch("job_a", at=now)
    record = monitor._records["job_a"]
    assert record.last_seen == now
