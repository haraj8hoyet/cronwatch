"""Tests for cronwatch.window_filter and cronwatch.window_filter_factory."""
from __future__ import annotations

from datetime import datetime, time
from unittest.mock import MagicMock

import pytest

from cronwatch.window_filter import ActiveWindow, WindowFilterRegistry, _parse_time
from cronwatch.window_filter_factory import build_window_filter_registry


# ---------------------------------------------------------------------------
# _parse_time
# ---------------------------------------------------------------------------

def test_parse_time_valid():
    assert _parse_time("08:30") == time(8, 30)


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError):
        _parse_time("8am")


# ---------------------------------------------------------------------------
# ActiveWindow.is_active
# ---------------------------------------------------------------------------

def _dt(hour: int, minute: int = 0, weekday: int = 1) -> datetime:
    """Create a datetime with the given hour/minute on a specific ISO weekday."""
    # Find a date whose isoweekday() == weekday (1=Mon)
    base = datetime(2024, 1, 1)  # Monday
    delta = (weekday - 1) % 7
    from datetime import timedelta
    d = base + timedelta(days=delta)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


def test_window_active_inside_range():
    w = ActiveWindow("biz", time(9, 0), time(17, 0))
    assert w.is_active(_dt(12, 0))


def test_window_inactive_before_start():
    w = ActiveWindow("biz", time(9, 0), time(17, 0))
    assert not w.is_active(_dt(8, 59))


def test_window_inactive_after_end():
    w = ActiveWindow("biz", time(9, 0), time(17, 0))
    assert not w.is_active(_dt(17, 1))


def test_overnight_window_active_after_start():
    w = ActiveWindow("night", time(22, 0), time(6, 0))
    assert w.is_active(_dt(23, 0))


def test_overnight_window_active_before_end():
    w = ActiveWindow("night", time(22, 0), time(6, 0))
    assert w.is_active(_dt(5, 0))


def test_overnight_window_inactive_midday():
    w = ActiveWindow("night", time(22, 0), time(6, 0))
    assert not w.is_active(_dt(12, 0))


def test_weekday_filter_blocks_wrong_day():
    # window only on Monday (1); test on Tuesday (2)
    w = ActiveWindow("biz", time(9, 0), time(17, 0), weekdays=[1])
    assert not w.is_active(_dt(12, 0, weekday=2))


def test_weekday_filter_allows_correct_day():
    w = ActiveWindow("biz", time(9, 0), time(17, 0), weekdays=[1, 2, 3, 4, 5])
    assert w.is_active(_dt(12, 0, weekday=3))


# ---------------------------------------------------------------------------
# WindowFilterRegistry
# ---------------------------------------------------------------------------

def test_empty_registry_always_allows():
    reg = WindowFilterRegistry()
    assert reg.is_allowed()


def test_registry_allows_when_one_window_active():
    reg = WindowFilterRegistry()
    reg.add_window(ActiveWindow("a", time(0, 0), time(23, 59)))
    assert reg.is_allowed(_dt(10, 0))


def test_registry_blocks_when_no_window_active():
    reg = WindowFilterRegistry()
    reg.add_window(ActiveWindow("biz", time(9, 0), time(17, 0)))
    assert not reg.is_allowed(_dt(3, 0))


def test_registry_window_count():
    reg = WindowFilterRegistry()
    reg.add_window(ActiveWindow("a", time(9, 0), time(12, 0)))
    reg.add_window(ActiveWindow("b", time(13, 0), time(18, 0)))
    assert reg.window_count == 2


# ---------------------------------------------------------------------------
# build_window_filter_registry
# ---------------------------------------------------------------------------

def _make_config(windows):
    alert_cfg = MagicMock()
    alert_cfg.active_windows = windows
    cfg = MagicMock()
    cfg.alert = alert_cfg
    return cfg


def test_factory_no_alert_config_returns_empty():
    cfg = MagicMock()
    cfg.alert = None
    reg = build_window_filter_registry(cfg)
    assert reg.window_count == 0


def test_factory_empty_windows_returns_empty():
    reg = build_window_filter_registry(_make_config([]))
    assert reg.window_count == 0


def test_factory_dict_entry_creates_window():
    entry = {"name": "biz", "start": "09:00", "end": "17:00", "weekdays": ["mon", "fri"]}
    reg = build_window_filter_registry(_make_config([entry]))
    assert reg.window_count == 1


def test_factory_string_shorthand_creates_window():
    reg = build_window_filter_registry(_make_config(["09:00-17:00"]))
    assert reg.window_count == 1


def test_factory_weekday_string_mapping():
    entry = {"name": "w", "start": "08:00", "end": "18:00", "weekdays": ["tue", "thu"]}
    reg = build_window_filter_registry(_make_config([entry]))
    # Window should block on Monday (1)
    assert not reg.is_allowed(_dt(12, 0, weekday=1))
    # Window should allow on Tuesday (2)
    assert reg.is_allowed(_dt(12, 0, weekday=2))
