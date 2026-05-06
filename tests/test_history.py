"""Tests for cronwatch.history.JobHistory."""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from cronwatch.history import JobHistory
from cronwatch.tracker import JobRun


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "cronwatch" / "history.db"


@pytest.fixture
def history(db_path: Path) -> JobHistory:
    return JobHistory(db_path=db_path)


def _make_run(
    exit_code: int = 0,
    started: datetime = None,
    finished: datetime = None,
) -> JobRun:
    run = JobRun()
    run.started_at = started or datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    run.finished_at = finished or datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
    run.exit_code = exit_code
    return run


def test_db_file_is_created(history: JobHistory, db_path: Path) -> None:
    assert db_path.exists()


def test_record_and_retrieve(history: JobHistory) -> None:
    run = _make_run(exit_code=0)
    history.record("backup", run)
    rows = history.recent("backup")
    assert len(rows) == 1
    assert rows[0]["job_name"] == "backup"
    assert rows[0]["exit_code"] == 0


def test_recent_respects_limit(history: JobHistory) -> None:
    for i in range(15):
        run = _make_run(
            exit_code=0,
            started=datetime(2024, 1, 1, 12, i, 0, tzinfo=timezone.utc),
            finished=datetime(2024, 1, 1, 12, i, 5, tzinfo=timezone.utc),
        )
        history.record("cleanup", run)
    rows = history.recent("cleanup", limit=5)
    assert len(rows) == 5


def test_recent_ordered_newest_first(history: JobHistory) -> None:
    for minute in [1, 3, 2]:
        run = _make_run(
            started=datetime(2024, 1, 1, 12, minute, 0, tzinfo=timezone.utc),
            finished=datetime(2024, 1, 1, 12, minute, 5, tzinfo=timezone.utc),
        )
        history.record("sync", run)
    rows = history.recent("sync")
    timestamps = [r["started_at"] for r in rows]
    assert timestamps == sorted(timestamps, reverse=True)


def test_last_success_returns_none_when_no_runs(history: JobHistory) -> None:
    assert history.last_success("nonexistent") is None


def test_last_success_returns_none_when_only_failures(history: JobHistory) -> None:
    history.record("deploy", _make_run(exit_code=1))
    assert history.last_success("deploy") is None


def test_last_success_returns_latest_success(history: JobHistory) -> None:
    history.record("deploy", _make_run(exit_code=1))
    success_time = datetime(2024, 6, 1, 8, 0, 5, tzinfo=timezone.utc)
    history.record(
        "deploy",
        _make_run(
            exit_code=0,
            started=datetime(2024, 6, 1, 8, 0, 0, tzinfo=timezone.utc),
            finished=success_time,
        ),
    )
    result = history.last_success("deploy")
    assert result == success_time


def test_record_in_progress_run(history: JobHistory) -> None:
    run = JobRun()
    run.started_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    run.finished_at = None
    run.exit_code = None
    history.record("long_job", run)
    rows = history.recent("long_job")
    assert len(rows) == 1
    assert rows[0]["finished_at"] is None
    assert rows[0]["exit_code"] is None
