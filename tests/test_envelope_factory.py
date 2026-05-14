"""Tests for build_envelope factory."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.config import JobConfig
from cronwatch.envelope import AlertEnvelope
from cronwatch.envelope_factory import build_envelope


@pytest.fixture()
def event() -> AlertEvent:
    ev = MagicMock(spec=AlertEvent)
    ev.job_name = "nightly_backup"
    ev.kind = "failure"
    return ev


@pytest.fixture()
def job_cfg() -> JobConfig:
    cfg = MagicMock(spec=JobConfig)
    cfg.tags = ["env:prod", "team:ops"]
    cfg.labels = {"owner": "alice"}
    return cfg


def test_returns_envelope_instance(event: AlertEvent) -> None:
    result = build_envelope(event)
    assert isinstance(result, AlertEnvelope)


def test_event_stored_on_envelope(event: AlertEvent) -> None:
    result = build_envelope(event)
    assert result.event is event


def test_kind_tag_added_without_job_cfg(event: AlertEvent) -> None:
    result = build_envelope(event)
    assert "kind:failure" in result.tags


def test_job_cfg_tags_included(event: AlertEvent, job_cfg: JobConfig) -> None:
    result = build_envelope(event, job_cfg=job_cfg)
    assert "env:prod" in result.tags
    assert "team:ops" in result.tags


def test_job_cfg_labels_included(event: AlertEvent, job_cfg: JobConfig) -> None:
    result = build_envelope(event, job_cfg=job_cfg)
    assert result.labels["owner"] == "alice"


def test_kind_tag_not_duplicated(event: AlertEvent, job_cfg: JobConfig) -> None:
    job_cfg.tags = ["kind:failure"]
    result = build_envelope(event, job_cfg=job_cfg)
    assert result.tags.count("kind:failure") == 1


def test_no_job_cfg_empty_labels(event: AlertEvent) -> None:
    result = build_envelope(event)
    assert result.labels == {}


def test_job_cfg_none_tags_handled(event: AlertEvent) -> None:
    cfg = MagicMock(spec=JobConfig)
    cfg.tags = None
    cfg.labels = None
    result = build_envelope(event, job_cfg=cfg)
    assert "kind:failure" in result.tags
    assert result.labels == {}
