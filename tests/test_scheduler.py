"""Tests for cronwatch.scheduler."""

from datetime import datetime, timedelta

import pytest

from cronwatch.config import JobConfig
from cronwatch.scheduler import MissedRunDetector, validate_schedule


@pytest.fixture()
def every_minute_job() -> JobConfig:
    return JobConfig(name="heartbeat", schedule="* * * * *", grace_period=60)


@pytest.fixture()
def hourly_job() -> JobConfig:
    return JobConfig(name="hourly-report", schedule="0 * * * *", grace_period=120)


# ---------------------------------------------------------------------------
# validate_schedule
# ---------------------------------------------------------------------------

def test_valid_schedule_passes():
    assert validate_schedule("*/5 * * * *") is True


def test_invalid_schedule_fails():
    assert validate_schedule("not-a-cron") is False


def test_invalid_schedule_too_many_fields():
    assert validate_schedule("* * * * * * *") is False


# ---------------------------------------------------------------------------
# MissedRunDetector.last_expected_run / next_expected_run
# ---------------------------------------------------------------------------

def test_last_expected_run(every_minute_job):
    now = datetime(2024, 6, 1, 12, 30, 45)
    detector = MissedRunDetector(every_minute_job)
    last = detector.last_expected_run(now)
    assert last == datetime(2024, 6, 1, 12, 30, 0)


def test_next_expected_run(every_minute_job):
    now = datetime(2024, 6, 1, 12, 30, 45)
    detector = MissedRunDetector(every_minute_job)
    nxt = detector.next_expected_run(now)
    assert nxt == datetime(2024, 6, 1, 12, 31, 0)


# ---------------------------------------------------------------------------
# MissedRunDetector.is_missed
# ---------------------------------------------------------------------------

def test_never_ran_after_grace_is_missed(hourly_job):
    # 3 minutes past the hour — beyond the 2-minute grace period.
    now = datetime(2024, 6, 1, 12, 3, 0)
    detector = MissedRunDetector(hourly_job)
    assert detector.is_missed(last_seen=None, now=now) is True


def test_never_ran_within_grace_not_missed(hourly_job):
    # 1 minute past the hour — still within the 2-minute grace period.
    now = datetime(2024, 6, 1, 12, 1, 0)
    detector = MissedRunDetector(hourly_job)
    assert detector.is_missed(last_seen=None, now=now) is False


def test_ran_on_time_not_missed(hourly_job):
    now = datetime(2024, 6, 1, 12, 3, 0)
    last_seen = datetime(2024, 6, 1, 12, 0, 5)  # ran just after noon
    detector = MissedRunDetector(hourly_job)
    assert detector.is_missed(last_seen=last_seen, now=now) is False


def test_ran_previous_hour_is_missed(hourly_job):
    now = datetime(2024, 6, 1, 12, 5, 0)
    last_seen = datetime(2024, 6, 1, 11, 0, 10)  # ran at 11:00, missed 12:00
    detector = MissedRunDetector(hourly_job)
    assert detector.is_missed(last_seen=last_seen, now=now) is True


def test_still_within_grace_not_missed(hourly_job):
    now = datetime(2024, 6, 1, 12, 0, 30)  # 30 s after the hour
    detector = MissedRunDetector(hourly_job)
    # Even without a last_seen, we're inside the grace window.
    assert detector.is_missed(last_seen=None, now=now) is False
