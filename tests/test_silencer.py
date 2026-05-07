"""Tests for cronwatch.silencer."""

import time
import pytest

from cronwatch.silencer import AlertSilencer, SilenceWindow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def silencer() -> AlertSilencer:
    return AlertSilencer()


# ---------------------------------------------------------------------------
# SilenceWindow unit tests
# ---------------------------------------------------------------------------

def test_window_active_before_expiry():
    future = time.time() + 60
    w = SilenceWindow(job_name="backup", until=future)
    assert w.is_active() is True


def test_window_inactive_after_expiry():
    past = time.time() - 1
    w = SilenceWindow(job_name="backup", until=past)
    assert w.is_active() is False


def test_window_remaining_seconds_positive():
    future = time.time() + 30
    w = SilenceWindow(job_name="backup", until=future)
    assert w.remaining_seconds() > 0


def test_window_remaining_seconds_zero_when_expired():
    past = time.time() - 5
    w = SilenceWindow(job_name="backup", until=past)
    assert w.remaining_seconds() == 0.0


# ---------------------------------------------------------------------------
# AlertSilencer tests
# ---------------------------------------------------------------------------

def test_silence_creates_active_window(silencer):
    silencer.silence("nightly", duration_seconds=300)
    assert silencer.is_silenced("nightly") is True


def test_unknown_job_not_silenced(silencer):
    assert silencer.is_silenced("nonexistent") is False


def test_silence_expires(silencer):
    now = time.time()
    silencer.silence("nightly", duration_seconds=10)
    future_now = now + 20
    assert silencer.is_silenced("nightly", now=future_now) is False


def test_lift_removes_window(silencer):
    silencer.silence("nightly", duration_seconds=300)
    removed = silencer.lift("nightly")
    assert removed is True
    assert silencer.is_silenced("nightly") is False


def test_lift_returns_false_when_no_window(silencer):
    assert silencer.lift("ghost") is False


def test_active_windows_excludes_expired(silencer):
    now = time.time()
    silencer.silence("job_a", duration_seconds=100)
    silencer.silence("job_b", duration_seconds=100)
    # Simulate job_a expired
    silencer._windows["job_a"].until = now - 1
    active = silencer.active_windows(now=now)
    assert "job_a" not in active
    assert "job_b" in active


def test_purge_expired_removes_old_windows(silencer):
    now = time.time()
    silencer.silence("job_x", duration_seconds=100)
    silencer._windows["job_x"].until = now - 1
    silencer.silence("job_y", duration_seconds=100)
    removed = silencer.purge_expired(now=now)
    assert removed == 1
    assert "job_x" not in silencer._windows
    assert "job_y" in silencer._windows


def test_silence_reason_stored(silencer):
    silencer.silence("critical", duration_seconds=60, reason="maintenance window")
    window = silencer._windows["critical"]
    assert window.reason == "maintenance window"


def test_re_silence_overwrites_previous(silencer):
    now = time.time()
    silencer.silence("job", duration_seconds=10)
    silencer.silence("job", duration_seconds=600)
    assert silencer._windows["job"].remaining_seconds(now=now) > 500
