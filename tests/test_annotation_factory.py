"""Tests for cronwatch.annotation_factory."""
import pytest

from cronwatch.annotation_factory import build_annotation_registry


class _FakeJob:
    def __init__(self, name: str, annotations=None):
        self.name = name
        self.annotations = annotations


class _FakeCfg:
    def __init__(self, jobs):
        self.jobs = jobs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_none_config_returns_empty_registry():
    reg = build_annotation_registry(None)
    assert reg.job_names() == []


def test_jobs_without_annotations_returns_empty_registry():
    cfg = _FakeCfg(jobs=[_FakeJob("backup"), _FakeJob("report")])
    reg = build_annotation_registry(cfg)
    assert reg.job_names() == []


def test_job_with_annotations_populated():
    job = _FakeJob("deploy", annotations={"owner": "alice", "env": "prod"})
    cfg = _FakeCfg(jobs=[job])
    reg = build_annotation_registry(cfg)
    aset = reg.for_job("deploy")
    assert aset.get("owner") == "alice"
    assert aset.get("env") == "prod"


def test_annotation_source_is_config():
    job = _FakeJob("sync", annotations={"team": "platform"})
    cfg = _FakeCfg(jobs=[job])
    reg = build_annotation_registry(cfg)
    items = reg.for_job("sync").all()
    assert all(a.source == "config" for a in items)


def test_multiple_jobs_each_get_own_set():
    jobs = [
        _FakeJob("job-a", annotations={"k": "1"}),
        _FakeJob("job-b", annotations={"k": "2"}),
    ]
    cfg = _FakeCfg(jobs=jobs)
    reg = build_annotation_registry(cfg)
    assert reg.for_job("job-a").get("k") == "1"
    assert reg.for_job("job-b").get("k") == "2"


def test_non_dict_annotations_ignored():
    job = _FakeJob("misc", annotations="not-a-dict")
    cfg = _FakeCfg(jobs=[job])
    reg = build_annotation_registry(cfg)
    assert len(reg.for_job("misc")) == 0


def test_empty_annotations_dict_ignored():
    job = _FakeJob("empty", annotations={})
    cfg = _FakeCfg(jobs=[job])
    reg = build_annotation_registry(cfg)
    assert len(reg.for_job("empty")) == 0
