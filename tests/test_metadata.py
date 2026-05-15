"""Tests for cronwatch.metadata."""

from __future__ import annotations

import pytest

from cronwatch.metadata import JobMetadata, MetadataStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "meta.db")


@pytest.fixture
def store(db_path) -> MetadataStore:
    return MetadataStore(db_path)


# ---------------------------------------------------------------------------
# JobMetadata unit tests
# ---------------------------------------------------------------------------


def test_metadata_get_returns_default_when_missing():
    m = JobMetadata(job_name="backup")
    assert m.get("owner") is None
    assert m.get("owner", "ops") == "ops"


def test_metadata_set_and_get():
    m = JobMetadata(job_name="backup")
    m.set("owner", "alice")
    assert m.get("owner") == "alice"


def test_metadata_remove():
    m = JobMetadata(job_name="backup")
    m.set("owner", "alice")
    m.remove("owner")
    assert m.get("owner") is None


def test_metadata_remove_missing_key_is_noop():
    m = JobMetadata(job_name="backup")
    m.remove("nonexistent")  # should not raise


def test_metadata_len():
    m = JobMetadata(job_name="backup")
    assert len(m) == 0
    m.set("a", "1")
    m.set("b", "2")
    assert len(m) == 2


# ---------------------------------------------------------------------------
# MetadataStore persistence tests
# ---------------------------------------------------------------------------


def test_db_file_is_created(db_path):
    import os
    MetadataStore(db_path)
    assert os.path.exists(db_path)


def test_load_returns_empty_for_unknown_job(store):
    meta = store.load("no_such_job")
    assert meta.job_name == "no_such_job"
    assert len(meta) == 0


def test_save_and_load_roundtrip(store):
    meta = JobMetadata(job_name="cleanup", entries={"owner": "ops", "team": "infra"})
    store.save(meta)
    loaded = store.load("cleanup")
    assert loaded.get("owner") == "ops"
    assert loaded.get("team") == "infra"


def test_save_overwrites_existing_entries(store):
    meta = JobMetadata(job_name="cleanup", entries={"owner": "ops"})
    store.save(meta)
    meta.set("owner", "dev")
    meta.set("env", "prod")
    store.save(meta)
    loaded = store.load("cleanup")
    assert loaded.get("owner") == "dev"
    assert loaded.get("env") == "prod"
    assert len(loaded) == 2


def test_delete_removes_all_entries(store):
    meta = JobMetadata(job_name="cleanup", entries={"owner": "ops"})
    store.save(meta)
    store.delete("cleanup")
    loaded = store.load("cleanup")
    assert len(loaded) == 0


def test_all_job_names_empty_initially(store):
    assert store.all_job_names() == []


def test_all_job_names_returns_saved_jobs(store):
    store.save(JobMetadata(job_name="job_a", entries={"x": "1"}))
    store.save(JobMetadata(job_name="job_b", entries={"y": "2"}))
    names = store.all_job_names()
    assert "job_a" in names
    assert "job_b" in names


def test_delete_does_not_affect_other_jobs(store):
    store.save(JobMetadata(job_name="job_a", entries={"k": "v"}))
    store.save(JobMetadata(job_name="job_b", entries={"k": "v"}))
    store.delete("job_a")
    assert store.load("job_b").get("k") == "v"
    assert store.all_job_names() == ["job_b"]
