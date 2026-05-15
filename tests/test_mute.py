"""Tests for cronwatch.mute."""
import time
import pytest

from cronwatch.mute import AlertMuter, MuteEntry


# ---------------------------------------------------------------------------
# MuteEntry
# ---------------------------------------------------------------------------

def test_entry_active_before_expiry():
    now = time.time()
    entry = MuteEntry(job_name="job", expires_at=now + 60)
    assert entry.is_active(now=now) is True


def test_entry_inactive_after_expiry():
    now = time.time()
    entry = MuteEntry(job_name="job", expires_at=now - 1)
    assert entry.is_active(now=now) is False


def test_entry_remaining_seconds_positive():
    now = time.time()
    entry = MuteEntry(job_name="job", expires_at=now + 30)
    assert entry.remaining_seconds(now=now) == pytest.approx(30, abs=0.1)


def test_entry_remaining_seconds_zero_when_expired():
    now = time.time()
    entry = MuteEntry(job_name="job", expires_at=now - 5)
    assert entry.remaining_seconds(now=now) == 0.0


# ---------------------------------------------------------------------------
# AlertMuter
# ---------------------------------------------------------------------------

@pytest.fixture()
def muter() -> AlertMuter:
    return AlertMuter()


def test_mute_creates_active_entry(muter):
    muter.mute("job_a", duration_seconds=60)
    assert muter.is_muted("job_a") is True


def test_unmuted_job_is_not_muted(muter):
    assert muter.is_muted("job_b") is False


def test_unmute_removes_entry(muter):
    muter.mute("job_a", duration_seconds=60)
    removed = muter.unmute("job_a")
    assert removed is True
    assert muter.is_muted("job_a") is False


def test_unmute_returns_false_when_not_present(muter):
    assert muter.unmute("nonexistent") is False


def test_expired_mute_is_not_active(muter):
    now = time.time()
    # Inject an already-expired entry manually
    muter._entries["job_c"] = MuteEntry("job_c", expires_at=now - 10)
    assert muter.is_muted("job_c", now=now) is False


def test_expired_entry_evicted_lazily(muter):
    now = time.time()
    muter._entries["job_d"] = MuteEntry("job_d", expires_at=now - 1)
    muter.is_muted("job_d", now=now)
    assert "job_d" not in muter._entries


def test_active_mutes_returns_only_active(muter):
    now = time.time()
    muter.mute("active_job", duration_seconds=100)
    muter._entries["stale_job"] = MuteEntry("stale_job", expires_at=now - 1)
    active = muter.active_mutes(now=now)
    assert "active_job" in active
    assert "stale_job" not in active


def test_mute_stores_reason(muter):
    muter.mute("job_e", duration_seconds=60, reason="maintenance")
    entry = muter.get_entry("job_e")
    assert entry is not None
    assert entry.reason == "maintenance"


def test_mute_raises_for_non_positive_duration(muter):
    with pytest.raises(ValueError):
        muter.mute("job_f", duration_seconds=0)


def test_get_entry_returns_none_for_unknown(muter):
    assert muter.get_entry("unknown") is None
