"""Tests for cronwatch.digest — DigestReport and DigestBuilder."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwatch.digest import DigestBuilder, DigestReport
from cronwatch.reporter import JobSummary


def _summary(name: str, total: int, successes: int) -> JobSummary:
    s = JobSummary(job_name=name)
    s.total_runs = total
    s.successful_runs = successes
    s.failed_runs = total - successes
    return s


@pytest.fixture()
def mixed_report() -> DigestReport:
    return DigestReport(
        summaries=[
            _summary("backup", 10, 10),
            _summary("cleanup", 5, 3),
            _summary("idle-job", 0, 0),
        ]
    )


def test_total_jobs(mixed_report: DigestReport) -> None:
    assert mixed_report.total_jobs == 3


def test_healthy_jobs(mixed_report: DigestReport) -> None:
    assert [s.job_name for s in mixed_report.healthy_jobs] == ["backup"]


def test_failing_jobs(mixed_report: DigestReport) -> None:
    assert [s.job_name for s in mixed_report.failing_jobs] == ["cleanup"]


def test_idle_jobs(mixed_report: DigestReport) -> None:
    assert [s.job_name for s in mixed_report.idle_jobs] == ["idle-job"]


def test_subject_with_failures(mixed_report: DigestReport) -> None:
    assert "1 job(s) with failures" in mixed_report.subject()


def test_subject_all_healthy() -> None:
    report = DigestReport(summaries=[_summary("job", 4, 4)])
    assert "all jobs healthy" in report.subject()


def test_body_contains_job_names(mixed_report: DigestReport) -> None:
    body = mixed_report.body()
    assert "backup" in body
    assert "cleanup" in body
    assert "idle-job" in body


def test_body_contains_failing_section(mixed_report: DigestReport) -> None:
    body = mixed_report.body()
    assert "FAILING JOBS" in body
    assert "60%" in body


def test_body_contains_healthy_section(mixed_report: DigestReport) -> None:
    body = mixed_report.body()
    assert "Healthy jobs" in body


def test_body_contains_idle_section(mixed_report: DigestReport) -> None:
    body = mixed_report.body()
    assert "No runs recorded" in body


def test_body_contains_timestamp(mixed_report: DigestReport) -> None:
    body = mixed_report.body()
    assert "UTC" in body


def test_digest_builder_calls_reporter() -> None:
    mock_reporter = MagicMock()
    mock_reporter.summary.side_effect = lambda name, hours: _summary(name, 2, 2)
    builder = DigestBuilder(mock_reporter)
    report = builder.build(["job-a", "job-b"], hours=12)
    assert report.total_jobs == 2
    mock_reporter.summary.assert_any_call("job-a", hours=12)
    mock_reporter.summary.assert_any_call("job-b", hours=12)


def test_digest_builder_empty_list() -> None:
    mock_reporter = MagicMock()
    builder = DigestBuilder(mock_reporter)
    report = builder.build([])
    assert report.total_jobs == 0
    assert "all jobs healthy" in report.subject()
