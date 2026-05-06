"""Tests for the JobTracker and JobRun classes."""

import time

import pytest

from cronwatch.tracker import JobRun, JobTracker


@pytest.fixture
def tracker():
    return JobTracker(max_history=10)


def test_start_run_creates_record(tracker):
    run = tracker.start_run("backup")
    assert run.job_name == "backup"
    assert run.started_at <= time.time()
    assert run.is_running
    assert run.exit_code is None


def test_finish_run_records_exit_code(tracker):
    run = tracker.start_run("backup")
    tracker.finish_run(run, exit_code=0, output="done")
    assert not run.is_running
    assert run.exit_code == 0
    assert run.output == "done"
    assert run.succeeded
    assert not run.failed


def test_failed_run(tracker):
    run = tracker.start_run("backup")
    tracker.finish_run(run, exit_code=1)
    assert run.failed
    assert not run.succeeded


def test_run_duration(tracker):
    run = tracker.start_run("backup")
    time.sleep(0.05)
    tracker.finish_run(run, exit_code=0)
    assert run.duration is not None
    assert run.duration >= 0.05


def test_duration_none_while_running(tracker):
    run = tracker.start_run("backup")
    assert run.duration is None


def test_last_run_returns_most_recent_completed(tracker):
    run1 = tracker.start_run("backup")
    tracker.finish_run(run1, exit_code=0)
    run2 = tracker.start_run("backup")
    tracker.finish_run(run2, exit_code=1)
    last = tracker.last_run("backup")
    assert last is run2


def test_last_run_excludes_running(tracker):
    run1 = tracker.start_run("backup")
    tracker.finish_run(run1, exit_code=0)
    _run2 = tracker.start_run("backup")  # still running
    last = tracker.last_run("backup")
    assert last is run1


def test_last_run_unknown_job_returns_none(tracker):
    assert tracker.last_run("nonexistent") is None


def test_failure_streak_consecutive(tracker):
    for code in [0, 1, 1, 1]:
        run = tracker.start_run("job")
        tracker.finish_run(run, exit_code=code)
    assert tracker.failure_streak("job") == 3


def test_failure_streak_reset_on_success(tracker):
    for code in [1, 1, 0]:
        run = tracker.start_run("job")
        tracker.finish_run(run, exit_code=code)
    assert tracker.failure_streak("job") == 0


def test_max_history_evicts_oldest(tracker):
    for i in range(12):
        run = tracker.start_run("job")
        tracker.finish_run(run, exit_code=0)
    assert len(tracker.recent_runs("job", limit=20)) == 10


def test_recent_runs_limit(tracker):
    for _ in range(8):
        run = tracker.start_run("job")
        tracker.finish_run(run, exit_code=0)
    assert len(tracker.recent_runs("job", limit=3)) == 3
