"""Tests for cronwatch.fingerprint."""

from datetime import datetime, timezone

import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.fingerprint import AlertFingerprint, FingerprintGenerator


UTC = timezone.utc


@pytest.fixture()
def generator() -> FingerprintGenerator:
    return FingerprintGenerator()


def _event(job_name: str = "backup", exit_code=1) -> AlertEvent:
    return AlertEvent(
        job_name=job_name,
        exit_code=exit_code,
        started_at=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        finished_at=datetime(2024, 6, 1, 12, 5, tzinfo=UTC),
    )


def _missed_event(job_name: str = "cleanup") -> AlertEvent:
    return AlertEvent(
        job_name=job_name,
        exit_code=None,
        started_at=None,
        finished_at=None,
    )


# ---------------------------------------------------------------------------
# AlertFingerprint
# ---------------------------------------------------------------------------

def test_str_returns_hex_digest(generator):
    fp = generator.generate(_event())
    assert str(fp) == fp.hex_digest


def test_short_is_12_chars(generator):
    fp = generator.generate(_event())
    assert len(fp.short()) == 12
    assert fp.hex_digest.startswith(fp.short())


# ---------------------------------------------------------------------------
# FingerprintGenerator
# ---------------------------------------------------------------------------

def test_same_event_same_fingerprint(generator):
    fp1 = generator.generate(_event())
    fp2 = generator.generate(_event())
    assert fp1.hex_digest == fp2.hex_digest


def test_different_job_different_fingerprint(generator):
    fp1 = generator.generate(_event(job_name="backup"))
    fp2 = generator.generate(_event(job_name="cleanup"))
    assert fp1.hex_digest != fp2.hex_digest


def test_different_exit_code_different_fingerprint(generator):
    fp1 = generator.generate(_event(exit_code=1))
    fp2 = generator.generate(_event(exit_code=2))
    assert fp1.hex_digest != fp2.hex_digest


def test_timestamp_does_not_affect_fingerprint(generator):
    e1 = AlertEvent(
        job_name="backup", exit_code=1,
        started_at=datetime(2024, 1, 1, tzinfo=UTC),
        finished_at=datetime(2024, 1, 1, 0, 5, tzinfo=UTC),
    )
    e2 = AlertEvent(
        job_name="backup", exit_code=1,
        started_at=datetime(2024, 6, 1, tzinfo=UTC),
        finished_at=datetime(2024, 6, 1, 0, 5, tzinfo=UTC),
    )
    assert generator.generate(e1).hex_digest == generator.generate(e2).hex_digest


def test_missed_event_classified_as_missed(generator):
    fp = generator.generate(_missed_event())
    assert fp.alert_type == "missed"
    assert fp.exit_code is None


def test_failure_event_classified_as_failure(generator):
    fp = generator.generate(_event(exit_code=127))
    assert fp.alert_type == "failure"


def test_missed_and_failure_different_fingerprints(generator):
    fp_miss = generator.generate(_missed_event(job_name="backup"))
    fp_fail = generator.generate(_event(job_name="backup", exit_code=1))
    assert fp_miss.hex_digest != fp_fail.hex_digest


def test_hex_digest_is_64_chars(generator):
    fp = generator.generate(_event())
    assert len(fp.hex_digest) == 64
