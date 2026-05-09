"""Tests for cronwatch.tag_filter and cronwatch.tag_filter_factory."""
from __future__ import annotations

import pytest

from cronwatch.tag_filter import TagFilter, TagFilterRegistry
from cronwatch.tag_filter_factory import build_tag_filter_registry


# ---------------------------------------------------------------------------
# TagFilter unit tests
# ---------------------------------------------------------------------------

class TestTagFilter:
    def test_empty_filter_matches_any_tags(self):
        f = TagFilter()
        assert f.matches(["foo", "bar"]) is True

    def test_empty_filter_matches_empty_tags(self):
        f = TagFilter()
        assert f.matches([]) is True

    def test_include_exact_match(self):
        f = TagFilter(include=["critical"])
        assert f.matches(["critical", "prod"]) is True

    def test_include_no_match(self):
        f = TagFilter(include=["critical"])
        assert f.matches(["batch", "dev"]) is False

    def test_include_glob_wildcard(self):
        f = TagFilter(include=["prod-*"])
        assert f.matches(["prod-us", "staging"]) is True

    def test_exclude_takes_priority_over_include(self):
        f = TagFilter(include=["critical"], exclude=["test"])
        assert f.matches(["critical", "test"]) is False

    def test_exclude_without_include_blocks_tag(self):
        f = TagFilter(exclude=["batch"])
        assert f.matches(["batch"]) is False

    def test_exclude_without_include_allows_other_tags(self):
        f = TagFilter(exclude=["batch"])
        assert f.matches(["prod", "critical"]) is True

    def test_exclude_glob_wildcard(self):
        f = TagFilter(exclude=["dev-*"])
        assert f.matches(["dev-local"]) is False
        assert f.matches(["prod-us"]) is True


# ---------------------------------------------------------------------------
# TagFilterRegistry unit tests
# ---------------------------------------------------------------------------

class TestTagFilterRegistry:
    def test_empty_registry_any_match_false(self):
        reg = TagFilterRegistry()
        assert reg.any_match(["foo"]) is False

    def test_empty_registry_all_match_false(self):
        reg = TagFilterRegistry()
        assert reg.all_match(["foo"]) is False

    def test_register_and_get(self):
        reg = TagFilterRegistry()
        f = TagFilter(include=["prod"])
        reg.register("prod-only", f)
        assert reg.get("prod-only") is f

    def test_get_missing_returns_none(self):
        reg = TagFilterRegistry()
        assert reg.get("nonexistent") is None

    def test_any_match_true_when_one_filter_matches(self):
        reg = TagFilterRegistry()
        reg.register("a", TagFilter(include=["prod"]))
        reg.register("b", TagFilter(include=["staging"]))
        assert reg.any_match(["prod"]) is True

    def test_all_match_requires_every_filter(self):
        reg = TagFilterRegistry()
        reg.register("a", TagFilter(include=["prod"]))
        reg.register("b", TagFilter(include=["critical"]))
        assert reg.all_match(["prod"]) is False
        assert reg.all_match(["prod", "critical"]) is True

    def test_filter_count(self):
        reg = TagFilterRegistry()
        reg.register("x", TagFilter())
        reg.register("y", TagFilter())
        assert reg.filter_count == 2


# ---------------------------------------------------------------------------
# build_tag_filter_registry factory tests
# ---------------------------------------------------------------------------

class _FakeAlertConfig:
    def __init__(self, tag_filters=None):
        self.tag_filters = tag_filters


def test_factory_no_config_returns_empty():
    reg = build_tag_filter_registry(None)
    assert reg.filter_count == 0


def test_factory_no_tag_filters_attr_returns_empty():
    class _Cfg:
        pass
    reg = build_tag_filter_registry(_Cfg())
    assert reg.filter_count == 0


def test_factory_dict_entry_creates_filter():
    cfg = _FakeAlertConfig(tag_filters=[
        {"name": "prod", "include": ["prod-*"], "exclude": ["test"]}
    ])
    reg = build_tag_filter_registry(cfg)
    assert reg.filter_count == 1
    f = reg.get("prod")
    assert f is not None
    assert f.matches(["prod-us"]) is True
    assert f.matches(["prod-us", "test"]) is False


def test_factory_string_entry_creates_glob_filter():
    cfg = _FakeAlertConfig(tag_filters=["critical"])
    reg = build_tag_filter_registry(cfg)
    assert reg.filter_count == 1
    assert reg.get("critical") is not None
    assert reg.any_match(["critical"]) is True
    assert reg.any_match(["batch"]) is False


def test_factory_skips_entry_without_name():
    cfg = _FakeAlertConfig(tag_filters=[
        {"include": ["prod"]},  # missing 'name'
        {"name": "valid", "include": ["staging"]},
    ])
    reg = build_tag_filter_registry(cfg)
    assert reg.filter_count == 1
    assert reg.get("valid") is not None
