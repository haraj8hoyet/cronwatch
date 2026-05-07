"""Tests for cronwatch.throttle."""

import pytest
from cronwatch.throttle import AlertThrottle, ThrottleEntry


NOW = 1_000_000.0
COOLDOWN = 300


@pytest.fixture
def throttle() -> AlertThrottle:
    return AlertThrottle(cooldown_seconds=COOLDOWN)


def test_first_alert_always_sent(throttle: AlertThrottle) -> None:
    assert throttle.should_send("backup", now=NOW) is True


def test_second_alert_suppressed_within_cooldown(throttle: AlertThrottle) -> None:
    throttle.should_send("backup", now=NOW)
    assert throttle.should_send("backup", now=NOW + 10) is False


def test_alert_allowed_after_cooldown_expires(throttle: AlertThrottle) -> None:
    throttle.should_send("backup", now=NOW)
    assert throttle.should_send("backup", now=NOW + COOLDOWN + 1) is True


def test_suppressed_count_increments(throttle: AlertThrottle) -> None:
    throttle.should_send("backup", now=NOW)
    throttle.should_send("backup", now=NOW + 1)
    throttle.should_send("backup", now=NOW + 2)
    assert throttle.suppressed_count("backup") == 2


def test_suppressed_count_resets_after_cooldown(throttle: AlertThrottle) -> None:
    throttle.should_send("backup", now=NOW)
    throttle.should_send("backup", now=NOW + 1)
    throttle.should_send("backup", now=NOW + COOLDOWN + 1)
    assert throttle.suppressed_count("backup") == 0


def test_suppressed_count_unknown_job_is_zero(throttle: AlertThrottle) -> None:
    assert throttle.suppressed_count("unknown") == 0


def test_reset_clears_state(throttle: AlertThrottle) -> None:
    throttle.should_send("backup", now=NOW)
    throttle.reset("backup")
    # After reset the next call should be treated as first alert
    assert throttle.should_send("backup", now=NOW + 1) is True


def test_reset_unknown_job_is_noop(throttle: AlertThrottle) -> None:
    throttle.reset("nonexistent")  # should not raise


def test_independent_jobs_throttled_separately(throttle: AlertThrottle) -> None:
    throttle.should_send("job_a", now=NOW)
    throttle.should_send("job_b", now=NOW)
    assert throttle.should_send("job_a", now=NOW + 5) is False
    assert throttle.should_send("job_b", now=NOW + 5) is False
    assert throttle.should_send("job_a", now=NOW + COOLDOWN + 1) is True
    # job_b still in cooldown
    assert throttle.should_send("job_b", now=NOW + COOLDOWN + 1) is True


def test_zero_cooldown_always_allows(throttle: AlertThrottle) -> None:
    t = AlertThrottle(cooldown_seconds=0)
    t.should_send("job", now=NOW)
    assert t.should_send("job", now=NOW) is True


def test_negative_cooldown_raises() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        AlertThrottle(cooldown_seconds=-1)


def test_throttle_entry_cooling_down() -> None:
    entry = ThrottleEntry(last_alert_at=NOW)
    assert entry.is_cooling_down(COOLDOWN, now=NOW + 100) is True
    assert entry.is_cooling_down(COOLDOWN, now=NOW + COOLDOWN + 1) is False
