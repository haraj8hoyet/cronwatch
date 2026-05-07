"""Tests for cronwatch.retry — AlertRetryPolicy and RetryEntry."""

import pytest
from cronwatch.retry import RetryEntry, AlertRetryPolicy


BASE = 60.0
BACKOFF = 2.0
MAX = 3


# ---------------------------------------------------------------------------
# RetryEntry unit tests
# ---------------------------------------------------------------------------

def test_next_delay_zero_before_first_attempt():
    e = RetryEntry(job_name="job")
    assert e.next_delay(BASE, BACKOFF) == 0.0


def test_next_delay_after_first_attempt():
    e = RetryEntry(job_name="job", attempts=1, last_attempt_at=0.0)
    assert e.next_delay(BASE, BACKOFF) == 60.0


def test_next_delay_exponential():
    e = RetryEntry(job_name="job", attempts=2, last_attempt_at=0.0)
    assert e.next_delay(BASE, BACKOFF) == 120.0


def test_is_ready_first_attempt():
    e = RetryEntry(job_name="job")
    assert e.is_ready(now=0.0, base_delay=BASE, backoff=BACKOFF, max_attempts=MAX)


def test_is_ready_false_when_max_reached():
    e = RetryEntry(job_name="job", attempts=3, last_attempt_at=0.0)
    assert not e.is_ready(now=999.0, base_delay=BASE, backoff=BACKOFF, max_attempts=MAX)


def test_is_ready_false_within_delay():
    e = RetryEntry(job_name="job", attempts=1, last_attempt_at=1000.0)
    # only 30 s elapsed, need 60
    assert not e.is_ready(now=1030.0, base_delay=BASE, backoff=BACKOFF, max_attempts=MAX)


def test_is_ready_true_after_delay():
    e = RetryEntry(job_name="job", attempts=1, last_attempt_at=1000.0)
    assert e.is_ready(now=1061.0, base_delay=BASE, backoff=BACKOFF, max_attempts=MAX)


def test_record_attempt_increments():
    e = RetryEntry(job_name="job")
    e.record_attempt(now=100.0)
    assert e.attempts == 1
    assert e.last_attempt_at == 100.0


def test_mark_success_sets_timestamp():
    e = RetryEntry(job_name="job", attempts=2, last_attempt_at=50.0)
    e.mark_success(now=200.0)
    assert e.succeeded_at == 200.0


# ---------------------------------------------------------------------------
# AlertRetryPolicy integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def policy():
    return AlertRetryPolicy(max_attempts=MAX, base_delay=BASE, backoff=BACKOFF)


def test_should_retry_true_for_new_job(policy):
    assert policy.should_retry("backup", now=0.0)


def test_attempts_zero_for_unknown_job(policy):
    assert policy.attempts("unknown") == 0


def test_record_attempt_increments_count(policy):
    policy.record_attempt("backup", now=0.0)
    assert policy.attempts("backup") == 1


def test_should_retry_false_immediately_after_attempt(policy):
    policy.record_attempt("backup", now=0.0)
    # 0 s elapsed — still within 60 s delay
    assert not policy.should_retry("backup", now=0.0)


def test_should_retry_true_after_delay(policy):
    policy.record_attempt("backup", now=0.0)
    assert policy.should_retry("backup", now=61.0)


def test_should_retry_false_after_max_attempts(policy):
    for i in range(MAX):
        policy.record_attempt("backup", now=float(i * 1000))
    assert not policy.should_retry("backup", now=99999.0)


def test_mark_success_resets_state(policy):
    policy.record_attempt("backup", now=0.0)
    policy.record_attempt("backup", now=61.0)
    policy.mark_success("backup", now=200.0)
    # attempts reset — should be ready again immediately
    assert policy.should_retry("backup", now=200.0)
    assert policy.attempts("backup") == 0


def test_clear_removes_entry(policy):
    policy.record_attempt("backup", now=0.0)
    policy.clear("backup")
    assert policy.attempts("backup") == 0
