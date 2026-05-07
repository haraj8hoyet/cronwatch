"""Tests for cronwatch.status — StatusChecker and StatusReport."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronwatch.config import JobConfig
from cronwatch.history import JobHistory
from cronwatch.tracker import JobRun
from cronwatch.status import JobStatus, StatusChecker, StatusReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _make_run(name: str, started: datetime, exit_code: int, seconds: float) -> JobRun:
    run = MagicMock(spec=JobRun)
    run.job_name = name
    run.started_at = started
    run.exit_code = exit_code
    run.duration = seconds
    return run


@pytest.fixture()
def job_config() -> JobConfig:
    return JobConfig(name="backup", schedule="0 2 * * *", command="/usr/bin/backup.sh")


@pytest.fixture()
def history(tmp_path: Path) -> JobHistory:
    return JobHistory(str(tmp_path / "test.db"))


# ---------------------------------------------------------------------------
# JobStatus
# ---------------------------------------------------------------------------

class TestJobStatus:
    def test_state_ok(self):
        s = JobStatus("j", "* * * * *", _utc(2024, 1, 1), 0, 1.2, False, None)
        assert s.state == "OK"

    def test_state_failed(self):
        s = JobStatus("j", "* * * * *", _utc(2024, 1, 1), 1, 1.2, False, None)
        assert s.state == "FAILED"

    def test_state_missed(self):
        s = JobStatus("j", "* * * * *", _utc(2024, 1, 1), 0, 1.2, True, None)
        assert s.state == "MISSED"

    def test_state_unknown_when_no_run(self):
        s = JobStatus("j", "* * * * *", None, None, None, False, None)
        assert s.state == "UNKNOWN"

    def test_str_contains_name(self):
        s = JobStatus("myjob", "* * * * *", _utc(2024, 6, 1, 12, 0), 0, 5.3, False, None)
        assert "myjob" in str(s)
        assert "OK" in str(s)


# ---------------------------------------------------------------------------
# StatusReport
# ---------------------------------------------------------------------------

class TestStatusReport:
    def test_str_contains_header(self):
        report = StatusReport(generated_at=_utc(2024, 6, 1, 10, 0))
        assert "Cronwatch Status" in str(report)

    def test_str_no_jobs_message(self):
        report = StatusReport(generated_at=_utc(2024, 6, 1, 10, 0))
        assert "No jobs configured" in str(report)


# ---------------------------------------------------------------------------
# StatusChecker
# ---------------------------------------------------------------------------

class TestStatusChecker:
    def test_no_history_gives_unknown(self, history, job_config):
        mock_history = MagicMock()
        mock_history.recent.return_value = []
        checker = StatusChecker(mock_history, [job_config])
        report = checker.report(now=_utc(2024, 6, 1, 12, 0))
        assert len(report.jobs) == 1
        assert report.jobs[0].state in ("UNKNOWN", "MISSED")

    def test_recent_ok_run(self, job_config):
        run = _make_run("backup", _utc(2024, 6, 1, 2, 0), 0, 10.5)
        mock_history = MagicMock()
        mock_history.recent.return_value = [run]
        checker = StatusChecker(mock_history, [job_config])
        report = checker.report(now=_utc(2024, 6, 1, 3, 0))
        js = report.jobs[0]
        assert js.last_exit_code == 0
        assert js.last_duration_seconds == pytest.approx(10.5)

    def test_report_lists_all_jobs(self, job_config):
        job2 = JobConfig(name="cleanup", schedule="30 3 * * *", command="/usr/bin/clean.sh")
        mock_history = MagicMock()
        mock_history.recent.return_value = []
        checker = StatusChecker(mock_history, [job_config, job2])
        report = checker.report(now=_utc(2024, 6, 1, 12, 0))
        assert len(report.jobs) == 2
        names = {j.name for j in report.jobs}
        assert names == {"backup", "cleanup"}
