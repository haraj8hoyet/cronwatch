"""Tests for cronwatch.backoff and cronwatch.backoff_factory."""
from __future__ import annotations

import pytest

from cronwatch.backoff import BackoffEntry, BackoffRegistry
from cronwatch.backoff_factory import build_backoff_registry


# ---------------------------------------------------------------------------
# BackoffEntry
# ---------------------------------------------------------------------------

def test_current_delay_zero_before_first_attempt():
    entry = BackoffEntry(base_delay=30.0)
    assert entry.current_delay() == 0.0


def test_current_delay_base_after_first_attempt():
    entry = BackoffEntry(base_delay=30.0, multiplier=2.0)
    entry.record_attempt(now=0.0)
    assert entry.current_delay() == 30.0


def test_current_delay_doubles_each_attempt():
    entry = BackoffEntry(base_delay=10.0, multiplier=2.0, max_delay=1000.0)
    entry.record_attempt(now=0.0)
    entry.record_attempt(now=10.0)
    assert entry.current_delay() == 20.0


def test_current_delay_capped_at_max():
    entry = BackoffEntry(base_delay=60.0, multiplier=10.0, max_delay=100.0)
    for i in range(5):
        entry.record_attempt(now=float(i))
    assert entry.current_delay() == 100.0


def test_is_ready_true_before_first_attempt():
    entry = BackoffEntry(base_delay=30.0)
    assert entry.is_ready(now=0.0) is True


def test_is_ready_false_immediately_after_attempt():
    entry = BackoffEntry(base_delay=30.0)
    entry.record_attempt(now=0.0)
    assert entry.is_ready(now=1.0) is False


def test_is_ready_true_after_delay_elapsed():
    entry = BackoffEntry(base_delay=30.0)
    entry.record_attempt(now=0.0)
    assert entry.is_ready(now=30.0) is True


def test_reset_clears_state():
    entry = BackoffEntry(base_delay=30.0)
    entry.record_attempt(now=0.0)
    entry.record_attempt(now=30.0)
    entry.reset()
    assert entry.attempt == 0
    assert entry.last_attempt_at is None
    assert entry.current_delay() == 0.0


# ---------------------------------------------------------------------------
# BackoffRegistry
# ---------------------------------------------------------------------------

@pytest.fixture
def registry() -> BackoffRegistry:
    return BackoffRegistry(base_delay=10.0, max_delay=300.0, multiplier=2.0)


def test_registry_is_ready_for_unknown_key(registry):
    assert registry.is_ready("job_a", now=0.0) is True


def test_registry_blocks_after_attempt(registry):
    registry.record_attempt("job_a", now=0.0)
    assert registry.is_ready("job_a", now=5.0) is False


def test_registry_allows_after_delay(registry):
    registry.record_attempt("job_a", now=0.0)
    assert registry.is_ready("job_a", now=10.0) is True


def test_registry_attempt_count(registry):
    registry.record_attempt("job_b", now=0.0)
    registry.record_attempt("job_b", now=10.0)
    assert registry.attempt_count("job_b") == 2


def test_registry_reset(registry):
    registry.record_attempt("job_c", now=0.0)
    registry.reset("job_c")
    assert registry.attempt_count("job_c") == 0
    assert registry.is_ready("job_c", now=0.0) is True


def test_registry_independent_keys(registry):
    registry.record_attempt("key1", now=0.0)
    assert registry.is_ready("key2", now=0.0) is True


# ---------------------------------------------------------------------------
# build_backoff_registry
# ---------------------------------------------------------------------------

class _FakeAlertConfig:
    def __init__(self, backoff=None):
        self.backoff = backoff


def test_factory_none_returns_defaults():
    reg = build_backoff_registry(None)
    assert isinstance(reg, BackoffRegistry)
    assert reg._base_delay == 30.0


def test_factory_no_backoff_key_returns_defaults():
    reg = build_backoff_registry(_FakeAlertConfig(backoff=None))
    assert reg._max_delay == 3600.0


def test_factory_custom_values():
    cfg = _FakeAlertConfig(backoff={"base_delay": 60, "max_delay": 600, "multiplier": 3})
    reg = build_backoff_registry(cfg)
    assert reg._base_delay == 60.0
    assert reg._max_delay == 600.0
    assert reg._multiplier == 3.0


def test_factory_partial_override_keeps_defaults():
    cfg = _FakeAlertConfig(backoff={"base_delay": 15})
    reg = build_backoff_registry(cfg)
    assert reg._base_delay == 15.0
    assert reg._max_delay == 3600.0
    assert reg._multiplier == 2.0
