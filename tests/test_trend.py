"""Tests for cronwatch.trend."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import List

import pytest

from cronwatch.trend import TrendAnalyzer, TrendPoint, TrendResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@dataclass
class _FakeRun:
    started_at: datetime
    succeeded: bool


def _run(hours_ago: float, ok: bool) -> _FakeRun:
    return _FakeRun(started_at=_NOW - timedelta(hours=hours_ago), succeeded=ok)


# ---------------------------------------------------------------------------
# TrendResult
# ---------------------------------------------------------------------------

class TestTrendResult:
    def test_is_degrading_false_with_fewer_than_two_points(self):
        tr = TrendResult(job_name="j", points=[
            TrendPoint(timestamp=_NOW, success_rate=0.5, sample_size=2)
        ])
        assert tr.is_degrading is False

    def test_is_degrading_true_when_rate_drops(self):
        tr = TrendResult(job_name="j", points=[
            TrendPoint(timestamp=_NOW - timedelta(hours=6), success_rate=1.0, sample_size=5),
            TrendPoint(timestamp=_NOW, success_rate=0.5, sample_size=5),
        ])
        assert tr.is_degrading is True

    def test_is_degrading_false_when_rate_improves(self):
        tr = TrendResult(job_name="j", points=[
            TrendPoint(timestamp=_NOW - timedelta(hours=6), success_rate=0.4, sample_size=5),
            TrendPoint(timestamp=_NOW, success_rate=0.9, sample_size=5),
        ])
        assert tr.is_degrading is False

    def test_latest_rate_none_when_no_points(self):
        assert TrendResult(job_name="j").latest_rate is None

    def test_latest_rate_returns_last_point(self):
        tr = TrendResult(job_name="j", points=[
            TrendPoint(timestamp=_NOW - timedelta(hours=6), success_rate=0.8, sample_size=3),
            TrendPoint(timestamp=_NOW, success_rate=0.6, sample_size=3),
        ])
        assert tr.latest_rate == pytest.approx(0.6)

    def test_delta_none_with_single_point(self):
        tr = TrendResult(job_name="j", points=[
            TrendPoint(timestamp=_NOW, success_rate=0.9, sample_size=2)
        ])
        assert tr.delta is None

    def test_delta_negative_when_degrading(self):
        tr = TrendResult(job_name="j", points=[
            TrendPoint(timestamp=_NOW - timedelta(hours=6), success_rate=1.0, sample_size=4),
            TrendPoint(timestamp=_NOW, success_rate=0.75, sample_size=4),
        ])
        assert tr.delta == pytest.approx(-0.25)

    def test_str_contains_job_name(self):
        tr = TrendResult(job_name="backup", points=[])
        assert "backup" in str(tr)


# ---------------------------------------------------------------------------
# TrendAnalyzer
# ---------------------------------------------------------------------------

class TestTrendAnalyzer:
    def test_invalid_bucket_hours_raises(self):
        with pytest.raises(ValueError):
            TrendAnalyzer(bucket_hours=0)

    def test_invalid_max_buckets_raises(self):
        with pytest.raises(ValueError):
            TrendAnalyzer(max_buckets=0)

    def test_empty_runs_returns_no_points(self, freezer=None):
        analyzer = TrendAnalyzer(bucket_hours=6, max_buckets=4)
        result = analyzer.analyze("myjob", [])
        assert result.job_name == "myjob"
        assert result.points == []

    def test_all_success_rate_is_one(self, monkeypatch):
        import cronwatch.trend as _mod
        monkeypatch.setattr(_mod, "datetime", _patched_datetime(_NOW))
        analyzer = TrendAnalyzer(bucket_hours=6, max_buckets=4)
        runs = [_run(1, True), _run(2, True), _run(3, True)]
        result = analyzer.analyze("j", runs)
        assert len(result.points) == 1
        assert result.points[0].success_rate == pytest.approx(1.0)
        assert result.points[0].sample_size == 3

    def test_mixed_runs_correct_rate(self, monkeypatch):
        import cronwatch.trend as _mod
        monkeypatch.setattr(_mod, "datetime", _patched_datetime(_NOW))
        analyzer = TrendAnalyzer(bucket_hours=6, max_buckets=4)
        runs = [_run(1, True), _run(2, False), _run(3, True), _run(4, False)]
        result = analyzer.analyze("j", runs)
        assert len(result.points) == 1
        assert result.points[0].success_rate == pytest.approx(0.5)

    def test_runs_beyond_max_buckets_ignored(self, monkeypatch):
        import cronwatch.trend as _mod
        monkeypatch.setattr(_mod, "datetime", _patched_datetime(_NOW))
        analyzer = TrendAnalyzer(bucket_hours=6, max_buckets=2)
        # bucket 0: 1–6 h ago, bucket 1: 6–12 h ago, bucket 2+: ignored
        runs = [
            _run(3, True),   # bucket 0
            _run(9, False),  # bucket 1
            _run(15, True),  # bucket 2 – should be ignored
        ]
        result = analyzer.analyze("j", runs)
        assert len(result.points) == 2


# ---------------------------------------------------------------------------
# Monkeypatch helper
# ---------------------------------------------------------------------------

def _patched_datetime(fixed_now: datetime):
    """Return a datetime replacement whose now() returns fixed_now."""
    from datetime import datetime as _real_dt, timezone as _tz

    class _FakeDatetime(_real_dt):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    return _FakeDatetime
