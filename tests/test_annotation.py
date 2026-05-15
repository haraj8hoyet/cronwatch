"""Tests for cronwatch.annotation."""
import pytest

from cronwatch.annotation import Annotation, AnnotationSet, AnnotationRegistry


# ---------------------------------------------------------------------------
# Annotation
# ---------------------------------------------------------------------------

def test_annotation_str_contains_key_and_value():
    ann = Annotation(key="env", value="prod", source="user")
    s = str(ann)
    assert "env" in s
    assert "prod" in s


def test_annotation_default_source_is_user():
    ann = Annotation(key="k", value="v")
    assert ann.source == "user"


# ---------------------------------------------------------------------------
# AnnotationSet
# ---------------------------------------------------------------------------

@pytest.fixture
def aset() -> AnnotationSet:
    return AnnotationSet()


def test_empty_set_has_length_zero(aset):
    assert len(aset) == 0


def test_add_increases_length(aset):
    aset.add("env", "prod")
    assert len(aset) == 1


def test_get_returns_value(aset):
    aset.add("team", "platform")
    assert aset.get("team") == "platform"


def test_get_missing_key_returns_none(aset):
    assert aset.get("missing") is None


def test_add_overwrites_existing_key(aset):
    aset.add("env", "staging")
    aset.add("env", "prod")
    assert aset.get("env") == "prod"
    assert len(aset) == 1


def test_remove_existing_key_returns_true(aset):
    aset.add("x", "1")
    assert aset.remove("x") is True
    assert len(aset) == 0


def test_remove_missing_key_returns_false(aset):
    assert aset.remove("ghost") is False


def test_contains_key(aset):
    aset.add("k", "v")
    assert "k" in aset
    assert "z" not in aset


def test_as_dict_returns_plain_mapping(aset):
    aset.add("a", "1", source="system")
    aset.add("b", "2")
    d = aset.as_dict()
    assert d == {"a": "1", "b": "2"}


def test_all_returns_annotation_objects(aset):
    aset.add("p", "q")
    items = aset.all()
    assert len(items) == 1
    assert isinstance(items[0], Annotation)


# ---------------------------------------------------------------------------
# AnnotationRegistry
# ---------------------------------------------------------------------------

@pytest.fixture
def registry() -> AnnotationRegistry:
    return AnnotationRegistry()


def test_for_job_creates_empty_set(registry):
    s = registry.for_job("backup")
    assert len(s) == 0


def test_for_job_same_instance_on_second_call(registry):
    s1 = registry.for_job("job-a")
    s2 = registry.for_job("job-a")
    assert s1 is s2


def test_annotate_stores_value(registry):
    registry.annotate("deploy", "owner", "alice")
    assert registry.for_job("deploy").get("owner") == "alice"


def test_job_names_lists_all_annotated_jobs(registry):
    registry.annotate("job-x", "k", "v")
    registry.annotate("job-y", "k", "v")
    assert set(registry.job_names()) == {"job-x", "job-y"}


def test_job_names_empty_when_no_annotations(registry):
    assert registry.job_names() == []
