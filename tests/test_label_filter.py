"""Tests for cronwatch.label_filter."""

import pytest

from cronwatch.label_filter import LabelFilter, LabelFilterRegistry


# ---------------------------------------------------------------------------
# LabelFilter
# ---------------------------------------------------------------------------

class TestLabelFilter:
    def test_empty_filter_matches_any_labels(self):
        f = LabelFilter()
        assert f.matches({"env": "prod", "team": "ops"}) is True

    def test_empty_filter_matches_empty_labels(self):
        f = LabelFilter()
        assert f.matches({}) is True

    def test_exact_match_succeeds(self):
        f = LabelFilter(required={"env": "prod"})
        assert f.matches({"env": "prod"}) is True

    def test_exact_match_fails_wrong_value(self):
        f = LabelFilter(required={"env": "prod"})
        assert f.matches({"env": "staging"}) is False

    def test_missing_key_fails(self):
        f = LabelFilter(required={"env": "prod"})
        assert f.matches({"team": "ops"}) is False

    def test_glob_pattern_matches(self):
        f = LabelFilter(required={"env": "prod-*"})
        assert f.matches({"env": "prod-web"}) is True

    def test_glob_pattern_no_match(self):
        f = LabelFilter(required={"env": "prod-*"})
        assert f.matches({"env": "staging-web"}) is False

    def test_multiple_required_all_must_match(self):
        f = LabelFilter(required={"env": "prod", "team": "ops"})
        assert f.matches({"env": "prod", "team": "ops"}) is True

    def test_multiple_required_partial_match_fails(self):
        f = LabelFilter(required={"env": "prod", "team": "ops"})
        assert f.matches({"env": "prod", "team": "dev"}) is False


# ---------------------------------------------------------------------------
# LabelFilterRegistry
# ---------------------------------------------------------------------------

@pytest.fixture
def registry() -> LabelFilterRegistry:
    return LabelFilterRegistry()


def test_empty_registry_matches_any(registry):
    assert registry.matches_any({"env": "prod"}) is True


def test_empty_registry_matches_empty_labels(registry):
    assert registry.matches_any({}) is True


def test_register_increases_len(registry):
    registry.register("prod", LabelFilter(required={"env": "prod"}))
    assert len(registry) == 1


def test_get_returns_registered_filter(registry):
    f = LabelFilter(required={"env": "prod"})
    registry.register("prod", f)
    assert registry.get("prod") is f


def test_get_unknown_group_returns_none(registry):
    assert registry.get("missing") is None


def test_matches_any_true_when_one_group_matches(registry):
    registry.register("prod", LabelFilter(required={"env": "prod"}))
    registry.register("staging", LabelFilter(required={"env": "staging"}))
    assert registry.matches_any({"env": "prod"}) is True


def test_matches_any_false_when_no_group_matches(registry):
    registry.register("prod", LabelFilter(required={"env": "prod"}))
    assert registry.matches_any({"env": "dev"}) is False


def test_matching_groups_returns_correct_names(registry):
    registry.register("prod", LabelFilter(required={"env": "prod"}))
    registry.register("ops", LabelFilter(required={"team": "ops"}))
    labels = {"env": "prod", "team": "ops"}
    groups = registry.matching_groups(labels)
    assert set(groups) == {"prod", "ops"}


def test_matching_groups_empty_when_none_match(registry):
    registry.register("prod", LabelFilter(required={"env": "prod"}))
    assert registry.matching_groups({"env": "dev"}) == []
