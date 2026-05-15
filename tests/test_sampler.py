"""Tests for cronwatch.sampler and cronwatch.sampler_factory."""

from __future__ import annotations

import os
import time
import pytest

from cronwatch.sampler import MetricSample, MetricSampler
from cronwatch.sampler_factory import build_metric_sampler, _resolve_db_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "test_metrics.db")


@pytest.fixture()
def sampler(db_path):
    return MetricSampler(db_path=db_path)


def _sample(job: str = "backup", rate: float = 1.0, runs: int = 5, ts: float | None = None) -> MetricSample:
    return MetricSample(
        job_name=job,
        timestamp=ts if ts is not None else time.time(),
        success_rate=rate,
        run_count=runs,
    )


# ---------------------------------------------------------------------------
# MetricSample
# ---------------------------------------------------------------------------


def test_sample_str_contains_job_name():
    s = _sample(job="nightly")
    assert "nightly" in str(s)


def test_sample_str_contains_rate():
    s = _sample(rate=0.75)
    assert "75.00%" in str(s)


# ---------------------------------------------------------------------------
# MetricSampler — record & retrieve
# ---------------------------------------------------------------------------


def test_db_file_is_created(db_path):
    MetricSampler(db_path=db_path)
    assert os.path.exists(db_path)


def test_record_and_latest(sampler):
    s = _sample(job="sync", rate=0.9, runs=10)
    sampler.record(s)
    result = sampler.latest("sync")
    assert result is not None
    assert result.job_name == "sync"
    assert result.success_rate == pytest.approx(0.9)
    assert result.run_count == 10


def test_latest_returns_none_for_unknown_job(sampler):
    assert sampler.latest("ghost") is None


def test_recent_returns_oldest_first(sampler):
    now = time.time()
    for i in range(3):
        sampler.record(_sample(job="j", rate=i * 0.1, ts=now + i))
    samples = sampler.recent("j")
    timestamps = [s.timestamp for s in samples]
    assert timestamps == sorted(timestamps)


def test_recent_respects_limit(sampler):
    now = time.time()
    for i in range(10):
        sampler.record(_sample(job="k", ts=now + i))
    assert len(sampler.recent("k", limit=4)) == 4


def test_recent_returns_empty_for_unknown_job(sampler):
    assert sampler.recent("unknown") == []


def test_purge_before_removes_old_samples(sampler):
    now = time.time()
    sampler.record(_sample(job="p", ts=now - 200))
    sampler.record(_sample(job="p", ts=now - 100))
    sampler.record(_sample(job="p", ts=now))
    removed = sampler.purge_before(now - 50)
    assert removed == 2
    assert len(sampler.recent("p")) == 1


# ---------------------------------------------------------------------------
# sampler_factory
# ---------------------------------------------------------------------------


def test_factory_returns_sampler_instance(tmp_path, monkeypatch):
    monkeypatch.setenv("CRONWATCH_METRICS_DB", str(tmp_path / "env.db"))
    s = build_metric_sampler()
    assert isinstance(s, MetricSampler)


def test_factory_uses_env_var(tmp_path, monkeypatch):
    target = str(tmp_path / "env_metrics.db")
    monkeypatch.setenv("CRONWATCH_METRICS_DB", target)
    assert _resolve_db_path(None) == target


def test_factory_uses_config_attr(tmp_path, monkeypatch):
    monkeypatch.delenv("CRONWATCH_METRICS_DB", raising=False)

    class _FakeCfg:
        metrics_db = str(tmp_path / "cfg.db")

    assert _resolve_db_path(_FakeCfg()) == str(tmp_path / "cfg.db")


def test_factory_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("CRONWATCH_METRICS_DB", raising=False)
    assert _resolve_db_path(None) == "cronwatch_metrics.db"
