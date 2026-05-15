"""Tests for cronwatch.checkpoint.CheckpointStore."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from cronwatch.checkpoint import CheckpointStore


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "checkpoints.db"


@pytest.fixture()
def store(db_path: Path) -> CheckpointStore:
    s = CheckpointStore(db_path)
    yield s
    s.close()


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# DB creation
# ---------------------------------------------------------------------------

def test_db_file_is_created(db_path: Path, store: CheckpointStore) -> None:
    assert db_path.exists()


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------

def test_load_returns_none_for_unknown_job(store: CheckpointStore) -> None:
    assert store.load("nonexistent") is None


def test_save_and_load_round_trip(store: CheckpointStore) -> None:
    ts = _utc(2024, 6, 1, 12)
    store.save("backup", ts)
    result = store.load("backup")
    assert result == ts


def test_save_overwrites_previous_value(store: CheckpointStore) -> None:
    ts1 = _utc(2024, 1, 1)
    ts2 = _utc(2024, 6, 1)
    store.save("myjob", ts1)
    store.save("myjob", ts2)
    assert store.load("myjob") == ts2


def test_loaded_timestamp_is_utc(store: CheckpointStore) -> None:
    naive_utc = datetime(2024, 3, 15, 9, 30)  # no tzinfo
    aware_utc = naive_utc.replace(tzinfo=timezone.utc)
    store.save("job", aware_utc)
    result = store.load("job")
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_removes_entry(store: CheckpointStore) -> None:
    store.save("temp_job", _utc(2024, 1, 1))
    store.delete("temp_job")
    assert store.load("temp_job") is None


def test_delete_nonexistent_job_does_not_raise(store: CheckpointStore) -> None:
    store.delete("ghost")  # should be a no-op


# ---------------------------------------------------------------------------
# all_jobs
# ---------------------------------------------------------------------------

def test_all_jobs_empty_initially(store: CheckpointStore) -> None:
    assert store.all_jobs() == []


def test_all_jobs_returns_saved_names(store: CheckpointStore) -> None:
    store.save("alpha", _utc(2024, 1, 1))
    store.save("beta", _utc(2024, 1, 2))
    jobs = store.all_jobs()
    assert sorted(jobs) == ["alpha", "beta"]


def test_all_jobs_excludes_deleted(store: CheckpointStore) -> None:
    store.save("keep", _utc(2024, 1, 1))
    store.save("remove", _utc(2024, 1, 1))
    store.delete("remove")
    assert store.all_jobs() == ["keep"]
