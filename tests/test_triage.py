"""Tests for cronwatch.triage."""
import pytest

from cronwatch.triage import AlertTriager, Severity, TriagePolicy, TriageResult


@pytest.fixture()
def triager() -> AlertTriager:
    return AlertTriager()


@pytest.fixture()
def strict_policy() -> TriagePolicy:
    return TriagePolicy(
        warning_threshold=2,
        critical_threshold=5,
        missed_run_severity=Severity.CRITICAL,
    )


def test_single_failure_is_info(triager: AlertTriager) -> None:
    result = triager.triage("backup", consecutive_failures=1)
    assert result.severity == Severity.INFO


def test_warning_at_default_threshold(triager: AlertTriager) -> None:
    result = triager.triage("backup", consecutive_failures=1)
    # default warning_threshold=1, so 1 failure => WARNING? No — INFO path fires first.
    # With default thresholds (warning=1, critical=3):
    # 1 failure => warning (>= 1 but < 3)
    policy = TriagePolicy(warning_threshold=1, critical_threshold=3)
    t = AlertTriager(policy)
    r = t.triage("backup", consecutive_failures=1)
    assert r.severity == Severity.WARNING


def test_critical_at_default_threshold(triager: AlertTriager) -> None:
    policy = TriagePolicy(warning_threshold=1, critical_threshold=3)
    t = AlertTriager(policy)
    result = t.triage("backup", consecutive_failures=3)
    assert result.severity == Severity.CRITICAL


def test_missed_run_returns_warning_by_default(triager: AlertTriager) -> None:
    result = triager.triage("nightly", consecutive_failures=0, is_missed=True)
    assert result.severity == Severity.WARNING
    assert result.is_missed is True


def test_missed_run_severity_overridden_by_policy(
    strict_policy: TriagePolicy,
) -> None:
    t = AlertTriager(strict_policy)
    result = t.triage("nightly", consecutive_failures=0, is_missed=True)
    assert result.severity == Severity.CRITICAL


def test_result_stores_job_name(triager: AlertTriager) -> None:
    result = triager.triage("my-job", consecutive_failures=2)
    assert result.job_name == "my-job"


def test_result_stores_consecutive_failures(triager: AlertTriager) -> None:
    result = triager.triage("job", consecutive_failures=7)
    assert result.consecutive_failures == 7


def test_str_contains_severity_and_job(triager: AlertTriager) -> None:
    policy = TriagePolicy(warning_threshold=1, critical_threshold=3)
    t = AlertTriager(policy)
    result = t.triage("deploy", consecutive_failures=4)
    text = str(result)
    assert "CRITICAL" in text
    assert "deploy" in text


def test_below_warning_threshold_is_info() -> None:
    policy = TriagePolicy(warning_threshold=3, critical_threshold=6)
    t = AlertTriager(policy)
    result = t.triage("job", consecutive_failures=2)
    assert result.severity == Severity.INFO


def test_custom_policy_warning_range() -> None:
    policy = TriagePolicy(warning_threshold=2, critical_threshold=5)
    t = AlertTriager(policy)
    result = t.triage("job", consecutive_failures=3)
    assert result.severity == Severity.WARNING


def test_default_policy_used_when_none_passed() -> None:
    t = AlertTriager(policy=None)
    # With default policy (warning=1, critical=3), 0 failures => INFO
    result = t.triage("job", consecutive_failures=0)
    assert result.severity == Severity.INFO
