"""Tests for cronwatch.escalation."""
from datetime import datetime, timezone

import pytest

from cronwatch.escalation import EscalationEntry, EscalationPolicy


# ---------------------------------------------------------------------------
# EscalationEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_initial_state():
    e = EscalationEntry(job_name="backup")
    assert e.consecutive_failures == 0
    assert e.escalated is False
    assert e.last_failure is None


def test_entry_record_failure_increments():
    e = EscalationEntry(job_name="backup")
    e.record_failure()
    e.record_failure()
    assert e.consecutive_failures == 2


def test_entry_record_failure_stores_timestamp():
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    e = EscalationEntry(job_name="backup")
    e.record_failure(when=now)
    assert e.last_failure == now


def test_entry_record_success_resets():
    e = EscalationEntry(job_name="backup")
    e.record_failure()
    e.record_failure()
    e.escalated = True
    e.record_success()
    assert e.consecutive_failures == 0
    assert e.escalated is False
    assert e.last_failure is None


def test_entry_should_escalate_at_threshold():
    e = EscalationEntry(job_name="backup", consecutive_failures=3)
    assert e.should_escalate(threshold=3) is True


def test_entry_should_not_escalate_below_threshold():
    e = EscalationEntry(job_name="backup", consecutive_failures=2)
    assert e.should_escalate(threshold=3) is False


def test_entry_should_not_escalate_when_already_escalated():
    e = EscalationEntry(job_name="backup", consecutive_failures=5, escalated=True)
    assert e.should_escalate(threshold=3) is False


# ---------------------------------------------------------------------------
# EscalationPolicy tests
# ---------------------------------------------------------------------------

@pytest.fixture
def policy():
    return EscalationPolicy(threshold=3)


def test_policy_invalid_threshold():
    with pytest.raises(ValueError):
        EscalationPolicy(threshold=0)


def test_policy_no_escalation_before_threshold(policy):
    assert policy.record_failure("job_a") is False
    assert policy.record_failure("job_a") is False


def test_policy_escalates_at_threshold(policy):
    policy.record_failure("job_a")
    policy.record_failure("job_a")
    result = policy.record_failure("job_a")
    assert result is True
    assert policy.is_escalated("job_a") is True


def test_policy_no_double_escalation(policy):
    for _ in range(5):
        policy.record_failure("job_a")
    # Only the 3rd call should have returned True; subsequent ones return False
    assert policy.record_failure("job_a") is False


def test_policy_success_resets_escalation(policy):
    for _ in range(3):
        policy.record_failure("job_a")
    assert policy.is_escalated("job_a") is True
    policy.record_success("job_a")
    assert policy.is_escalated("job_a") is False
    assert policy.consecutive_failures("job_a") == 0


def test_policy_independent_jobs(policy):
    policy.record_failure("job_a")
    policy.record_failure("job_a")
    policy.record_failure("job_a")
    assert policy.is_escalated("job_a") is True
    assert policy.is_escalated("job_b") is False


def test_policy_reset_removes_entry(policy):
    policy.record_failure("job_a")
    policy.reset("job_a")
    assert policy.consecutive_failures("job_a") == 0
