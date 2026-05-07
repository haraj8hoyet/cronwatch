"""Tests for cronwatch.reporter."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwatch.history import JobHistory
from cronwatch.reporter import JobSummary, Reporter
from cronwatch.tracker import JobRun


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_history.db"


@pytest.fixture()
def history(db_path: Path) -> JobHistory:
    return JobHistory(str(db_path))


@pytest.fixture()
def reporter(history: JobHistory) -> Reporter:
    return Reporter(history)


def _make_run(
    history: JobHistory,
    job_name: str,
    exit_code: int = 0,
    duration: float = 1.0,
    offset_minutes: int = 0,
) -> None:
    started = datetime.utcnow() - timedelta(minutes=offset_minutes + 1)
    finished = started + timedelta(seconds=duration)
    run = JobRun(job_name=job_name, started_at=started)
    run.finished_at = finished
    run.exit_code = exit_code
    history.record(run)


def test_summary_empty_history(reporter: Reporter) -> None:
    since = datetime.utcnow() - timedelta(hours=1)
    summary = reporter.summarise("backup", since)
    assert summary.total_runs == 0
    assert summary.successful_runs == 0
    assert summary.failed_runs == 0
    assert summary.avg_duration_seconds is None
    assert summary.last_run_at is None
    assert summary.success_rate is None


def test_summary_all_successful(history: JobHistory, reporter: Reporter) -> None:
    for i in range(3):
        _make_run(history, "sync", exit_code=0, duration=2.0, offset_minutes=i)
    since = datetime.utcnow() - timedelta(hours=1)
    summary = reporter.summarise("sync", since)
    assert summary.total_runs == 3
    assert summary.successful_runs == 3
    assert summary.failed_runs == 0
    assert summary.success_rate == pytest.approx(1.0)
    assert summary.avg_duration_seconds == pytest.approx(2.0)


def test_summary_mixed_results(history: JobHistory, reporter: Reporter) -> None:
    _make_run(history, "deploy", exit_code=0, duration=5.0, offset_minutes=10)
    _make_run(history, "deploy", exit_code=1, duration=3.0, offset_minutes=5)
    since = datetime.utcnow() - timedelta(hours=1)
    summary = reporter.summarise("deploy", since)
    assert summary.total_runs == 2
    assert summary.successful_runs == 1
    assert summary.failed_runs == 1
    assert summary.success_rate == pytest.approx(0.5)
    assert summary.avg_duration_seconds == pytest.approx(4.0)


def test_summary_last_exit_code(history: JobHistory, reporter: Reporter) -> None:
    _make_run(history, "cleanup", exit_code=0, offset_minutes=10)
    _make_run(history, "cleanup", exit_code=2, offset_minutes=2)
    since = datetime.utcnow() - timedelta(hours=1)
    summary = reporter.summarise("cleanup", since)
    assert summary.last_exit_code == 2


def test_report_multiple_jobs(history: JobHistory, reporter: Reporter) -> None:
    _make_run(history, "job_a", exit_code=0)
    _make_run(history, "job_b", exit_code=1)
    summaries = reporter.report(["job_a", "job_b"], window_hours=1)
    assert len(summaries) == 2
    names = {s.job_name for s in summaries}
    assert names == {"job_a", "job_b"}


def test_summary_str_representation(reporter: Reporter) -> None:
    since = datetime.utcnow() - timedelta(hours=1)
    summary = reporter.summarise("noop", since)
    text = str(summary)
    assert "noop" in text
    assert "runs=0" in text
