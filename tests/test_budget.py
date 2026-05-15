"""Tests for cronwatch.budget and cronwatch.budget_factory."""

from __future__ import annotations

import time
import types

import pytest

from cronwatch.budget import AlertBudget, BudgetEntry
from cronwatch.budget_factory import build_alert_budget


# ---------------------------------------------------------------------------
# BudgetEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_within_budget_initially():
    entry = BudgetEntry(window_seconds=60, max_alerts=3)
    assert entry.is_within_budget(now=0.0) is True


def test_entry_blocks_after_max_reached():
    entry = BudgetEntry(window_seconds=60, max_alerts=2)
    entry.record(now=1.0)
    entry.record(now=2.0)
    assert entry.is_within_budget(now=3.0) is False


def test_entry_allows_after_window_expires():
    entry = BudgetEntry(window_seconds=60, max_alerts=2)
    entry.record(now=0.0)
    entry.record(now=1.0)
    # Both timestamps are now outside the window
    assert entry.is_within_budget(now=62.0) is True


def test_entry_partial_expiry():
    entry = BudgetEntry(window_seconds=60, max_alerts=2)
    entry.record(now=0.0)   # will expire
    entry.record(now=50.0)  # still active at t=61
    assert entry.is_within_budget(now=61.0) is True
    assert entry.current_count(now=61.0) == 1


def test_entry_current_count():
    entry = BudgetEntry(window_seconds=60, max_alerts=5)
    for i in range(3):
        entry.record(now=float(i))
    assert entry.current_count(now=3.0) == 3


def test_entry_remaining_decrements():
    entry = BudgetEntry(window_seconds=60, max_alerts=5)
    assert entry.remaining(now=0.0) == 5
    entry.record(now=1.0)
    entry.record(now=2.0)
    assert entry.remaining(now=3.0) == 3


def test_entry_remaining_never_negative():
    entry = BudgetEntry(window_seconds=60, max_alerts=1)
    entry.record(now=0.0)
    entry.record(now=0.5)  # over budget
    assert entry.remaining(now=1.0) == 0


# ---------------------------------------------------------------------------
# AlertBudget integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def budget():
    return AlertBudget(window_seconds=60, max_alerts=3)


def test_budget_allows_first_alert(budget):
    assert budget.is_within_budget("job_a", now=0.0) is True


def test_budget_tracks_per_key(budget):
    budget.record("job_a", now=1.0)
    budget.record("job_a", now=2.0)
    budget.record("job_a", now=3.0)
    assert budget.is_within_budget("job_a", now=4.0) is False
    assert budget.is_within_budget("job_b", now=4.0) is True


def test_budget_reset_clears_history(budget):
    budget.record("job_a", now=1.0)
    budget.record("job_a", now=2.0)
    budget.record("job_a", now=3.0)
    budget.reset("job_a")
    assert budget.is_within_budget("job_a", now=4.0) is True


def test_budget_remaining(budget):
    budget.record("job_a", now=1.0)
    assert budget.remaining("job_a", now=2.0) == 2


# ---------------------------------------------------------------------------
# build_alert_budget factory tests
# ---------------------------------------------------------------------------

def test_factory_defaults_when_config_none():
    b = build_alert_budget(None)
    assert b._window == 3600
    assert b._max == 10


def test_factory_defaults_when_no_alert_attr():
    cfg = types.SimpleNamespace()
    b = build_alert_budget(cfg)
    assert b._window == 3600


def test_factory_reads_dict_budget():
    budget_dict = {"window_seconds": 1800, "max_alerts": 5}
    alert_cfg = types.SimpleNamespace(budget=budget_dict)
    cfg = types.SimpleNamespace(alert=alert_cfg)
    b = build_alert_budget(cfg)
    assert b._window == 1800
    assert b._max == 5


def test_factory_reads_object_budget():
    budget_obj = types.SimpleNamespace(window_seconds=7200, max_alerts=20)
    alert_cfg = types.SimpleNamespace(budget=budget_obj)
    cfg = types.SimpleNamespace(alert=alert_cfg)
    b = build_alert_budget(cfg)
    assert b._window == 7200
    assert b._max == 20
