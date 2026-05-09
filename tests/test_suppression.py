"""Tests for cronwatch.suppression."""

from __future__ import annotations

import pytest

from cronwatch.suppression import SuppressionRegistry, SuppressionRule


# ---------------------------------------------------------------------------
# SuppressionRule
# ---------------------------------------------------------------------------

class TestSuppressionRule:
    def test_glob_matches_exact(self):
        rule = SuppressionRule(pattern="backup")
        assert rule.matches("backup")

    def test_glob_wildcard(self):
        rule = SuppressionRule(pattern="backup_*")
        assert rule.matches("backup_daily")
        assert not rule.matches("nightly_backup")

    def test_regex_matches(self):
        rule = SuppressionRule(pattern=r"^db_.*_sync$", use_regex=True)
        assert rule.matches("db_prod_sync")
        assert not rule.matches("db_prod_sync_extra")

    def test_reason_stored(self):
        rule = SuppressionRule(pattern="*", reason="maintenance window")
        assert rule.reason == "maintenance window"

    def test_glob_no_match(self):
        rule = SuppressionRule(pattern="foo")
        assert not rule.matches("bar")


# ---------------------------------------------------------------------------
# SuppressionRegistry
# ---------------------------------------------------------------------------

@pytest.fixture
def registry() -> SuppressionRegistry:
    return SuppressionRegistry()


def test_empty_registry_not_suppressed(registry):
    assert not registry.is_suppressed("any_job")


def test_add_rule_increments_count(registry):
    registry.add_rule(SuppressionRule(pattern="job_*"))
    assert registry.rule_count() == 1


def test_is_suppressed_with_matching_rule(registry):
    registry.add_rule(SuppressionRule(pattern="nightly_*"))
    assert registry.is_suppressed("nightly_backup")


def test_is_suppressed_no_match(registry):
    registry.add_rule(SuppressionRule(pattern="nightly_*"))
    assert not registry.is_suppressed("daily_backup")


def test_matching_rule_returns_first_match(registry):
    r1 = SuppressionRule(pattern="a_*")
    r2 = SuppressionRule(pattern="a_b*")
    registry.add_rule(r1)
    registry.add_rule(r2)
    assert registry.matching_rule("a_backup") is r1


def test_matching_rule_returns_none_when_no_match(registry):
    registry.add_rule(SuppressionRule(pattern="x_*"))
    assert registry.matching_rule("y_job") is None


def test_clear_removes_all_rules(registry):
    registry.add_rule(SuppressionRule(pattern="*"))
    registry.clear()
    assert registry.rule_count() == 0
    assert not registry.is_suppressed("anything")


def test_multiple_rules_any_match_suppresses(registry):
    registry.add_rule(SuppressionRule(pattern="alpha"))
    registry.add_rule(SuppressionRule(pattern="beta"))
    assert registry.is_suppressed("beta")
