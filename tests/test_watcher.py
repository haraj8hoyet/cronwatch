"""Tests for cronwatch.watcher module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerter import AlertEvent, Alerter
from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.tracker import JobTracker
from cronwatch.watcher import CronWatcher, JobWatcher


@pytest.fixture
def job_config():
    return JobConfig(name="backup", schedule="0 2 * * *", command="/usr/bin/backup.sh")


@pytest.fixture
def alert_config():
    return AlertConfig(email="ops@example.com", smtp_host="localhost", smtp_port=25)


@pytest.fixture
def mock_alerter():
    return MagicMock(spec=Alerter)


@pytest.fixture
def tracker():
    return JobTracker()


@pytest.fixture
def watcher(job_config, tracker, mock_alerter):
    return JobWatcher(job=job_config, tracker=tracker, alerter=mock_alerter)


def test_no_alert_when_run_not_missed(watcher):
    """No alert sent when last run was recent enough."""
    # patch detector to say not missed
    watcher.detector.is_missed = MagicMock(return_value=False)
    result = watcher.check_missed(datetime.now(timezone.utc))
    assert result is False
    watcher.alerter.send.assert_not_called()


def test_alert_sent_when_run_missed(watcher):
    """Alert is sent when a missed run is detected."""
    expected_time = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
    watcher.detector.is_missed = MagicMock(return_value=True)
    watcher.detector.last_expected_run = MagicMock(return_value=expected_time)

    result = watcher.check_missed(datetime(2024, 1, 15, 3, 0, 0, tzinfo=timezone.utc))

    assert result is True
    watcher.alerter.send.assert_called_once()
    event: AlertEvent = watcher.alerter.send.call_args[0][0]
    assert event.kind == "missed"
    assert event.job_name == "backup"


def test_missed_alert_not_sent_twice(watcher):
    """The same missed run is not alerted twice."""
    expected_time = datetime(2024, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
    watcher.detector.is_missed = MagicMock(return_value=True)
    watcher.detector.last_expected_run = MagicMock(return_value=expected_time)

    now = datetime(2024, 1, 15, 3, 0, 0, tzinfo=timezone.utc)
    watcher.check_missed(now)
    watcher.check_missed(now)

    assert watcher.alerter.send.call_count == 1


def test_handle_finish_alerts_on_failure(watcher, tracker):
    """Alert is sent when a finished job run has failed."""
    tracker.start("backup")
    run = tracker.finish("backup", exit_code=1)

    watcher.handle_finish(run)

    watcher.alerter.send.assert_called_once()
    event: AlertEvent = watcher.alerter.send.call_args[0][0]
    assert event.kind == "failure"
    assert event.exit_code == 1


def test_handle_finish_no_alert_on_success(watcher, tracker):
    """No alert sent when a job run succeeds."""
    tracker.start("backup")
    run = tracker.finish("backup", exit_code=0)

    watcher.handle_finish(run)

    watcher.alerter.send.assert_not_called()


def test_cronwatcher_initializes_all_jobs(alert_config):
    """CronWatcher creates a watcher and tracker for every configured job."""
    jobs = [
        JobConfig(name="job1", schedule="* * * * *", command="echo 1"),
        JobConfig(name="job2", schedule="0 * * * *", command="echo 2"),
    ]
    config = CronwatchConfig(jobs=jobs, alerts=alert_config)

    with patch("cronwatch.watcher.Alerter"):
        cw = CronWatcher(config)

    assert "job1" in cw._trackers
    assert "job2" in cw._watchers
