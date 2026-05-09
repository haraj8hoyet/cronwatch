"""Tests for cronwatch.snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.snapshot import JobSnapshot, SystemSnapshot, SnapshotBuilder


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# JobSnapshot
# ---------------------------------------------------------------------------

class TestJobSnapshot:
    def test_is_healthy_when_state_ok(self):
        snap = JobSnapshot("backup", "ok", None, None, 0)
        assert snap.is_healthy() is True
        assert snap.is_failing() is False

    def test_is_failing_when_state_failing(self):
        snap = JobSnapshot("backup", "failing", None, 1, 3)
        assert snap.is_failing() is True
        assert snap.is_healthy() is False

    def test_str_with_last_run(self):
        ts = _utc(2024, 6, 1, 12, 0, 0)
        snap = JobSnapshot("nightly", "ok", ts, 0, 0)
        text = str(snap)
        assert "nightly" in text
        assert "ok" in text
        assert "2024-06-01" in text

    def test_str_never_when_no_last_run(self):
        snap = JobSnapshot("nightly", "idle", None, None, 0)
        assert "never" in str(snap)


# ---------------------------------------------------------------------------
# SystemSnapshot
# ---------------------------------------------------------------------------

class TestSystemSnapshot:
    def _make_snap(self, state: str) -> JobSnapshot:
        return JobSnapshot("job", state, None, None, 0)

    def test_total_counts_all_jobs(self):
        ss = SystemSnapshot(
            captured_at=_utc(2024, 1, 1),
            jobs=[self._make_snap("ok"), self._make_snap("failing"), self._make_snap("idle")],
        )
        assert ss.total == 3

    def test_healthy_counts_ok_only(self):
        ss = SystemSnapshot(
            captured_at=_utc(2024, 1, 1),
            jobs=[self._make_snap("ok"), self._make_snap("ok"), self._make_snap("failing")],
        )
        assert ss.healthy == 2

    def test_failing_counts_failing_only(self):
        ss = SystemSnapshot(
            captured_at=_utc(2024, 1, 1),
            jobs=[self._make_snap("ok"), self._make_snap("failing")],
        )
        assert ss.failing == 1

    def test_str_contains_counts(self):
        ss = SystemSnapshot(captured_at=_utc(2024, 1, 1), jobs=[])
        text = str(ss)
        assert "total=0" in text
        assert "healthy=0" in text
        assert "failing=0" in text


# ---------------------------------------------------------------------------
# SnapshotBuilder
# ---------------------------------------------------------------------------

class TestSnapshotBuilder:
    def _make_status(self, name: str, state: str, failures: int, exit_code=None):
        last_run = None
        if exit_code is not None:
            last_run = MagicMock()
            last_run.exit_code = exit_code
            last_run.end_time = _utc(2024, 5, 1)
        status = MagicMock()
        status.job_name = name
        status.state = state
        status.consecutive_failures = failures
        status.last_run = last_run
        return status

    def test_build_returns_system_snapshot(self):
        report = MagicMock()
        report.statuses = []
        ss = SnapshotBuilder().build(report)
        assert isinstance(ss, SystemSnapshot)
        assert ss.total == 0

    def test_build_maps_statuses_to_job_snapshots(self):
        report = MagicMock()
        report.statuses = [
            self._make_status("job_a", "ok", 0, exit_code=0),
            self._make_status("job_b", "failing", 2, exit_code=1),
        ]
        ss = SnapshotBuilder().build(report)
        assert ss.total == 2
        assert ss.healthy == 1
        assert ss.failing == 1

    def test_build_handles_no_last_run(self):
        report = MagicMock()
        report.statuses = [self._make_status("idle_job", "idle", 0, exit_code=None)]
        ss = SnapshotBuilder().build(report)
        assert ss.jobs[0].last_run_at is None
        assert ss.jobs[0].last_exit_code is None
