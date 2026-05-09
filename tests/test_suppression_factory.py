"""Tests for cronwatch.suppression_factory."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cronwatch.suppression_factory import build_suppression_registry


def _make_config(suppress=None):
    alert = SimpleNamespace(suppress=suppress)
    return SimpleNamespace(alert=alert)


def test_no_alert_config_returns_empty_registry():
    cfg = SimpleNamespace(alert=None)
    reg = build_suppression_registry(cfg)
    assert reg.rule_count() == 0


def test_empty_suppress_list_returns_empty_registry():
    reg = build_suppression_registry(_make_config(suppress=[]))
    assert reg.rule_count() == 0


def test_string_entry_creates_glob_rule():
    reg = build_suppression_registry(_make_config(suppress=["backup_*"]))
    assert reg.rule_count() == 1
    assert reg.is_suppressed("backup_daily")
    assert not reg.is_suppressed("nightly_run")


def test_dict_entry_creates_rule_with_reason():
    entry = {"pattern": "db_*", "reason": "planned maintenance"}
    reg = build_suppression_registry(_make_config(suppress=[entry]))
    rule = reg.matching_rule("db_sync")
    assert rule is not None
    assert rule.reason == "planned maintenance"


def test_dict_entry_regex_flag():
    entry = {"pattern": r"^report_\d+$", "regex": True}
    reg = build_suppression_registry(_make_config(suppress=[entry]))
    assert reg.is_suppressed("report_42")
    assert not reg.is_suppressed("report_abc")


def test_mixed_entries():
    entries = [
        "simple_*",
        {"pattern": r"^exact$", "regex": True},
    ]
    reg = build_suppression_registry(_make_config(suppress=entries))
    assert reg.rule_count() == 2
    assert reg.is_suppressed("simple_job")
    assert reg.is_suppressed("exact")
    assert not reg.is_suppressed("other")


def test_missing_suppress_attr_returns_empty_registry():
    alert = SimpleNamespace()  # no 'suppress' attribute
    cfg = SimpleNamespace(alert=alert)
    reg = build_suppression_registry(cfg)
    assert reg.rule_count() == 0
