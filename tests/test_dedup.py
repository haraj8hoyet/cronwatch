"""Tests for cronwatch.dedup (AlertDeduplicator)."""

import time
import pytest

from cronwatch.dedup import DedupEntry, AlertDeduplicator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def dedup() -> AlertDeduplicator:
    return AlertDeduplicator(window_seconds=60.0)


# ---------------------------------------------------------------------------
# DedupEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_not_duplicate_before_first_send():
    entry = DedupEntry(fingerprint="abc")
    assert entry.is_duplicate(60.0) is False


def test_entry_is_duplicate_within_window():
    now = time.monotonic()
    entry = DedupEntry(fingerprint="abc")
    entry.record(now=now)
    assert entry.is_duplicate(60.0, now=now + 30) is True


def test_entry_not_duplicate_after_window_expires():
    now = time.monotonic()
    entry = DedupEntry(fingerprint="abc")
    entry.record(now=now)
    assert entry.is_duplicate(60.0, now=now + 61) is False


def test_entry_send_count_increments():
    entry = DedupEntry(fingerprint="abc")
    entry.record()
    entry.record()
    assert entry.send_count == 2


# ---------------------------------------------------------------------------
# AlertDeduplicator tests
# ---------------------------------------------------------------------------

def test_fingerprint_is_stable():
    fp1 = AlertDeduplicator.fingerprint("backup", "failure", "exit 1")
    fp2 = AlertDeduplicator.fingerprint("backup", "failure", "exit 1")
    assert fp1 == fp2


def test_fingerprint_differs_by_field():
    fp1 = AlertDeduplicator.fingerprint("backup", "failure")
    fp2 = AlertDeduplicator.fingerprint("backup", "missed")
    assert fp1 != fp2


def test_first_alert_not_duplicate(dedup):
    fp = AlertDeduplicator.fingerprint("job", "failure")
    assert dedup.is_duplicate(fp) is False


def test_second_alert_is_duplicate_within_window(dedup):
    now = time.monotonic()
    fp = AlertDeduplicator.fingerprint("job", "failure")
    dedup.record(fp, now=now)
    assert dedup.is_duplicate(fp, now=now + 10) is True


def test_alert_allowed_after_window_expires(dedup):
    now = time.monotonic()
    fp = AlertDeduplicator.fingerprint("job", "failure")
    dedup.record(fp, now=now)
    assert dedup.is_duplicate(fp, now=now + 61) is False


def test_suppressed_count_zero_before_any_send(dedup):
    fp = AlertDeduplicator.fingerprint("job", "missed")
    assert dedup.suppressed_count(fp) == 0


def test_suppressed_count_tracks_sends(dedup):
    now = time.monotonic()
    fp = AlertDeduplicator.fingerprint("job", "missed")
    dedup.record(fp, now=now)
    dedup.record(fp, now=now + 5)
    assert dedup.suppressed_count(fp) == 2


def test_purge_expired_removes_old_entries(dedup):
    now = time.monotonic()
    fp = AlertDeduplicator.fingerprint("job", "failure")
    dedup.record(fp, now=now)
    removed = dedup.purge_expired(now=now + 120)
    assert removed == 1
    assert dedup.is_duplicate(fp, now=now + 121) is False


def test_purge_expired_keeps_active_entries(dedup):
    now = time.monotonic()
    fp = AlertDeduplicator.fingerprint("job", "failure")
    dedup.record(fp, now=now)
    removed = dedup.purge_expired(now=now + 30)
    assert removed == 0


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        AlertDeduplicator(window_seconds=0)
