"""Tests for cronwatch.jitter."""

import time
import pytest

from cronwatch.jitter import AlertJitter, JitterEntry


# ---------------------------------------------------------------------------
# JitterEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_not_pending_when_no_scheduled_at():
    entry = JitterEntry(key="job1", delay_seconds=10.0, scheduled_at=None)
    assert entry.is_pending() is False


def test_entry_pending_within_window():
    now = time.monotonic()
    entry = JitterEntry(key="job1", delay_seconds=60.0, scheduled_at=now)
    assert entry.is_pending(now=now + 1.0) is True


def test_entry_not_pending_after_window():
    now = time.monotonic()
    entry = JitterEntry(key="job1", delay_seconds=5.0, scheduled_at=now)
    assert entry.is_pending(now=now + 10.0) is False


def test_entry_seconds_remaining_positive():
    now = time.monotonic()
    entry = JitterEntry(key="job1", delay_seconds=30.0, scheduled_at=now)
    remaining = entry.seconds_remaining(now=now + 10.0)
    assert abs(remaining - 20.0) < 0.01


def test_entry_seconds_remaining_zero_when_expired():
    now = time.monotonic()
    entry = JitterEntry(key="job1", delay_seconds=5.0, scheduled_at=now)
    assert entry.seconds_remaining(now=now + 100.0) == 0.0


def test_entry_seconds_remaining_zero_when_no_scheduled_at():
    entry = JitterEntry(key="job1", delay_seconds=10.0, scheduled_at=None)
    assert entry.seconds_remaining() == 0.0


# ---------------------------------------------------------------------------
# AlertJitter unit tests
# ---------------------------------------------------------------------------

@pytest.fixture
def jitter():
    return AlertJitter(min_seconds=5.0, max_seconds=15.0, seed=42)


def test_assign_creates_entry(jitter):
    now = time.monotonic()
    entry = jitter.assign("backup", now=now)
    assert entry.key == "backup"
    assert 5.0 <= entry.delay_seconds <= 15.0
    assert entry.scheduled_at == now


def test_assign_same_key_while_pending_returns_same_entry(jitter):
    now = time.monotonic()
    entry1 = jitter.assign("backup", now=now)
    entry2 = jitter.assign("backup", now=now + 1.0)  # still pending
    assert entry1 is entry2


def test_assign_same_key_after_expiry_creates_new_entry(jitter):
    now = time.monotonic()
    entry1 = jitter.assign("backup", now=now)
    # Force expiry by passing a time well past the max delay
    entry2 = jitter.assign("backup", now=now + 1000.0)
    assert entry1 is not entry2


def test_is_pending_true_within_window(jitter):
    now = time.monotonic()
    jitter.assign("job_x", now=now)
    assert jitter.is_pending("job_x", now=now + 1.0) is True


def test_is_pending_false_for_unknown_key(jitter):
    assert jitter.is_pending("unknown") is False


def test_is_pending_false_after_expiry(jitter):
    now = time.monotonic()
    jitter.assign("job_x", now=now)
    assert jitter.is_pending("job_x", now=now + 10000.0) is False


def test_clear_removes_entry(jitter):
    now = time.monotonic()
    jitter.assign("job_y", now=now)
    assert jitter.entry_count() == 1
    jitter.clear("job_y")
    assert jitter.entry_count() == 0
    assert jitter.is_pending("job_y") is False


def test_clear_nonexistent_key_is_safe(jitter):
    jitter.clear("does_not_exist")  # should not raise


def test_invalid_bounds_raise():
    with pytest.raises(ValueError):
        AlertJitter(min_seconds=-1.0, max_seconds=10.0)


def test_min_greater_than_max_raises():
    with pytest.raises(ValueError):
        AlertJitter(min_seconds=20.0, max_seconds=5.0)


def test_zero_jitter_range():
    j = AlertJitter(min_seconds=0.0, max_seconds=0.0)
    now = time.monotonic()
    entry = j.assign("job", now=now)
    assert entry.delay_seconds == 0.0
    assert entry.is_pending(now=now + 0.001) is False
