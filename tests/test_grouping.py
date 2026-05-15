"""Tests for cronwatch.grouping (AlertGrouper / GroupEntry)."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.grouping import AlertGrouper, GroupEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(job_name: str = "backup", kind: str = "failure") -> AlertEvent:
    ev = MagicMock(spec=AlertEvent)
    ev.job_name = job_name
    ev.kind = kind
    ev.exit_code = 1 if kind == "failure" else None
    return ev


# ---------------------------------------------------------------------------
# GroupEntry
# ---------------------------------------------------------------------------

class TestGroupEntry:
    def test_initial_size_is_zero(self):
        entry = GroupEntry(key="job", window_seconds=30)
        assert entry.size() == 0

    def test_add_increments_size(self):
        entry = GroupEntry(key="job", window_seconds=30)
        entry.add(_event())
        entry.add(_event())
        assert entry.size() == 2

    def test_not_expired_within_window(self):
        entry = GroupEntry(key="job", window_seconds=30)
        assert not entry.is_expired(now=entry.opened_at + 10)

    def test_expired_after_window(self):
        entry = GroupEntry(key="job", window_seconds=30)
        assert entry.is_expired(now=entry.opened_at + 30)

    def test_expired_exactly_at_boundary(self):
        entry = GroupEntry(key="job", window_seconds=30)
        assert entry.is_expired(now=entry.opened_at + 30)


# ---------------------------------------------------------------------------
# AlertGrouper
# ---------------------------------------------------------------------------

@pytest.fixture
def grouper() -> AlertGrouper:
    return AlertGrouper(window_seconds=60.0)


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        AlertGrouper(window_seconds=0)


def test_add_creates_group(grouper):
    grouper.add(_event("sync"))
    assert grouper.group_count() == 1


def test_add_same_job_stays_one_group(grouper):
    grouper.add(_event("sync"))
    grouper.add(_event("sync"))
    assert grouper.group_count() == 1


def test_pending_count_across_groups(grouper):
    grouper.add(_event("sync"))
    grouper.add(_event("sync"))
    grouper.add(_event("backup"))
    assert grouper.pending_count() == 3


def test_flush_returns_expired_groups(grouper):
    grouper.add(_event("sync"))
    # Simulate time past window by manipulating opened_at
    grouper._groups["sync"].opened_at -= 120
    flushed = grouper.flush()
    assert "sync" in flushed
    assert len(flushed["sync"]) == 1


def test_flush_removes_expired_group(grouper):
    grouper.add(_event("sync"))
    grouper._groups["sync"].opened_at -= 120
    grouper.flush()
    assert grouper.group_count() == 0


def test_flush_does_not_return_unexpired_group(grouper):
    grouper.add(_event("sync"))
    flushed = grouper.flush(now=time.monotonic())
    assert "sync" not in flushed
    assert grouper.group_count() == 1


def test_flush_all_clears_everything(grouper):
    grouper.add(_event("sync"))
    grouper.add(_event("backup"))
    result = grouper.flush_all()
    assert set(result.keys()) == {"sync", "backup"}
    assert grouper.group_count() == 0
    assert grouper.pending_count() == 0


def test_flush_all_returns_all_events(grouper):
    for _ in range(3):
        grouper.add(_event("sync"))
    result = grouper.flush_all()
    assert len(result["sync"]) == 3


def test_mixed_expired_and_live(grouper):
    grouper.add(_event("old"))
    grouper.add(_event("new"))
    grouper._groups["old"].opened_at -= 120
    flushed = grouper.flush()
    assert "old" in flushed
    assert "new" not in flushed
    assert grouper.group_count() == 1
