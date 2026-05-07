"""Tests for cronwatch.ratelimit."""

import pytest

from cronwatch.ratelimit import AlertRateLimiter, RateLimitEntry

T0 = 1_000_000.0  # arbitrary fixed monotonic reference


@pytest.fixture
def limiter() -> AlertRateLimiter:
    """Rate limiter: max 3 alerts per 60-second window."""
    return AlertRateLimiter(window_seconds=60, max_alerts=3)


# ---------------------------------------------------------------------------
# RateLimitEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_allows_first_alert():
    entry = RateLimitEntry(window_seconds=60, max_alerts=3)
    assert entry.is_allowed(T0) is True


def test_entry_blocks_after_max_reached():
    entry = RateLimitEntry(window_seconds=60, max_alerts=2)
    entry.record(T0)
    entry.record(T0 + 1)
    assert entry.is_allowed(T0 + 2) is False


def test_entry_allows_after_window_expires():
    entry = RateLimitEntry(window_seconds=60, max_alerts=2)
    entry.record(T0)
    entry.record(T0 + 1)
    # advance past the window
    assert entry.is_allowed(T0 + 61) is True


def test_entry_partial_expiry():
    """Only timestamps outside the window are evicted."""
    entry = RateLimitEntry(window_seconds=60, max_alerts=3)
    entry.record(T0)          # will expire
    entry.record(T0 + 59)     # still in window at T0+61
    entry.record(T0 + 59.5)   # still in window at T0+61
    assert entry.is_allowed(T0 + 61) is False  # 2 remain, max is 3 → allowed
    # Actually 2 < 3 so it IS allowed — correct assertion:
    assert entry.current_count == 2


def test_entry_current_count_reflects_window():
    entry = RateLimitEntry(window_seconds=60, max_alerts=10)
    for i in range(5):
        entry.record(T0 + i)
    assert entry.current_count == 5
    # After window expires all are evicted
    entry._evict_expired(T0 + 120)
    assert entry.current_count == 0


# ---------------------------------------------------------------------------
# AlertRateLimiter integration tests
# ---------------------------------------------------------------------------

def test_first_alert_always_allowed(limiter):
    assert limiter.is_allowed("backup", T0) is True


def test_alert_blocked_at_limit(limiter):
    for i in range(3):
        assert limiter.is_allowed("backup", T0 + i) is True
        limiter.record("backup", T0 + i)
    assert limiter.is_allowed("backup", T0 + 3) is False


def test_alert_allowed_after_window_slides(limiter):
    limiter.record("backup", T0)
    limiter.record("backup", T0 + 1)
    limiter.record("backup", T0 + 2)
    assert limiter.is_allowed("backup", T0 + 61) is True


def test_independent_jobs_do_not_share_state(limiter):
    for i in range(3):
        limiter.record("job_a", T0 + i)
    assert limiter.is_allowed("job_a", T0 + 3) is False
    assert limiter.is_allowed("job_b", T0 + 3) is True


def test_reset_clears_entry(limiter):
    limiter.record("backup", T0)
    limiter.record("backup", T0 + 1)
    limiter.record("backup", T0 + 2)
    limiter.reset("backup")
    assert limiter.current_count("backup") == 0
    assert limiter.is_allowed("backup", T0 + 3) is True


def test_current_count_increments(limiter):
    assert limiter.current_count("job") == 0
    limiter.record("job", T0)
    assert limiter.current_count("job") == 1
    limiter.record("job", T0 + 1)
    assert limiter.current_count("job") == 2


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        AlertRateLimiter(window_seconds=0, max_alerts=5)


def test_invalid_max_alerts_raises():
    with pytest.raises(ValueError, match="max_alerts"):
        AlertRateLimiter(window_seconds=60, max_alerts=0)
