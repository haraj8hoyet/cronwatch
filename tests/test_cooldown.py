"""Tests for cronwatch.cooldown."""

from __future__ import annotations

import pytest

from cronwatch.cooldown import CooldownEntry, CooldownRegistry


# ---------------------------------------------------------------------------
# CooldownEntry
# ---------------------------------------------------------------------------


def test_entry_not_cooling_down_initially():
    entry = CooldownEntry(job_name="backup", cooldown_seconds=60.0)
    assert entry.is_cooling_down() is False


def test_entry_cooling_down_immediately_after_alert():
    entry = CooldownEntry(job_name="backup", cooldown_seconds=60.0)
    now = 1_000.0
    entry.record_alert(now=now)
    assert entry.is_cooling_down(now=now + 1.0) is True


def test_entry_not_cooling_down_after_window_expires():
    entry = CooldownEntry(job_name="backup", cooldown_seconds=60.0)
    now = 1_000.0
    entry.record_alert(now=now)
    assert entry.is_cooling_down(now=now + 60.0) is False


def test_entry_still_cooling_just_before_expiry():
    entry = CooldownEntry(job_name="backup", cooldown_seconds=60.0)
    now = 1_000.0
    entry.record_alert(now=now)
    assert entry.is_cooling_down(now=now + 59.9) is True


def test_entry_alert_count_increments():
    entry = CooldownEntry(job_name="backup", cooldown_seconds=60.0)
    assert entry.alert_count == 0
    entry.record_alert(now=0.0)
    entry.record_alert(now=1.0)
    assert entry.alert_count == 2


def test_entry_reset_clears_state():
    entry = CooldownEntry(job_name="backup", cooldown_seconds=60.0)
    entry.record_alert(now=0.0)
    entry.reset()
    assert entry.is_cooling_down(now=1.0) is False
    assert entry.alert_count == 0


def test_entry_seconds_remaining_zero_when_not_active():
    entry = CooldownEntry(job_name="backup", cooldown_seconds=60.0)
    assert entry.seconds_remaining == 0.0


def test_entry_seconds_remaining_zero_after_expiry():
    entry = CooldownEntry(job_name="backup", cooldown_seconds=60.0)
    now = 1_000.0
    entry.record_alert(now=now)
    # Simulate that enough real time has passed by patching last_alert_at
    entry._last_alert_at = now - 120.0  # 120 s ago
    assert entry.seconds_remaining == 0.0


# ---------------------------------------------------------------------------
# CooldownRegistry
# ---------------------------------------------------------------------------


@pytest.fixture()
def registry() -> CooldownRegistry:
    return CooldownRegistry(default_cooldown_seconds=120.0)


def test_registry_not_cooling_down_for_unknown_job(registry):
    assert registry.is_cooling_down("nightly_sync") is False


def test_registry_cooling_down_after_record_alert(registry):
    now = 500.0
    registry.record_alert("nightly_sync", now=now)
    assert registry.is_cooling_down("nightly_sync", now=now + 10.0) is True


def test_registry_not_cooling_down_after_expiry(registry):
    now = 500.0
    registry.record_alert("nightly_sync", now=now)
    assert registry.is_cooling_down("nightly_sync", now=now + 120.0) is False


def test_registry_reset_clears_cooldown(registry):
    now = 500.0
    registry.record_alert("nightly_sync", now=now)
    registry.reset("nightly_sync")
    assert registry.is_cooling_down("nightly_sync", now=now + 1.0) is False


def test_registry_reset_unknown_job_is_noop(registry):
    registry.reset("ghost_job")  # should not raise


def test_registry_entry_returns_correct_object(registry):
    registry.record_alert("db_backup", now=0.0)
    entry = registry.entry("db_backup")
    assert entry.job_name == "db_backup"
    assert entry.alert_count == 1


def test_registry_len_counts_distinct_jobs(registry):
    assert len(registry) == 0
    registry.record_alert("job_a", now=0.0)
    registry.record_alert("job_b", now=0.0)
    assert len(registry) == 2
