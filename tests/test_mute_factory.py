"""Tests for cronwatch.mute_factory."""
import pytest

from cronwatch.mute import AlertMuter
from cronwatch.mute_factory import build_alert_muter


# ---------------------------------------------------------------------------
# Fake config helpers
# ---------------------------------------------------------------------------

class _FakeAlertCfg:
    def __init__(self, mute=None):
        self.mute = mute


class _FakeCfg:
    def __init__(self, alert=None):
        self.alert = alert


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_alert_config_returns_empty_muter():
    cfg = _FakeCfg(alert=None)
    muter = build_alert_muter(cfg)
    assert isinstance(muter, AlertMuter)
    assert muter.active_mutes() == {}


def test_empty_mute_list_returns_empty_muter():
    cfg = _FakeCfg(alert=_FakeAlertCfg(mute=[]))
    muter = build_alert_muter(cfg)
    assert muter.active_mutes() == {}


def test_string_entry_mutes_with_default_duration():
    cfg = _FakeCfg(alert=_FakeAlertCfg(mute=["backup_job"]))
    muter = build_alert_muter(cfg)
    assert muter.is_muted("backup_job") is True
    entry = muter.get_entry("backup_job")
    assert entry.remaining_seconds() == pytest.approx(3600, abs=5)


def test_dict_entry_mutes_with_custom_duration():
    cfg = _FakeCfg(alert=_FakeAlertCfg(mute=[
        {"job": "nightly", "duration_seconds": 7200, "reason": "deploy"}
    ]))
    muter = build_alert_muter(cfg)
    assert muter.is_muted("nightly") is True
    entry = muter.get_entry("nightly")
    assert entry.remaining_seconds() == pytest.approx(7200, abs=5)
    assert entry.reason == "deploy"


def test_dict_entry_without_job_key_is_skipped():
    cfg = _FakeCfg(alert=_FakeAlertCfg(mute=[
        {"duration_seconds": 60}
    ]))
    muter = build_alert_muter(cfg)
    assert muter.active_mutes() == {}


def test_mixed_entries_all_registered():
    cfg = _FakeCfg(alert=_FakeAlertCfg(mute=[
        "job_a",
        {"job": "job_b", "duration_seconds": 120},
    ]))
    muter = build_alert_muter(cfg)
    assert muter.is_muted("job_a") is True
    assert muter.is_muted("job_b") is True
