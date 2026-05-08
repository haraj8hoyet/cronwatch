"""Tests for cronwatch.escalation_config."""
import pytest

from cronwatch.escalation_config import (
    EscalationSettings,
    build_escalation_policy_from_config,
    _DEFAULT_THRESHOLD,
    _DEFAULT_COOLDOWN_MINUTES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeAlertConfig:
    """Minimal stand-in for AlertConfig with an optional 'extra' dict."""
    def __init__(self, extra=None):
        self.extra = extra or {}


# ---------------------------------------------------------------------------
# EscalationSettings.from_alert_config
# ---------------------------------------------------------------------------

def test_defaults_when_cfg_is_none():
    s = EscalationSettings.from_alert_config(None)
    assert s.threshold == _DEFAULT_THRESHOLD
    assert s.cooldown_minutes == _DEFAULT_COOLDOWN_MINUTES
    assert s.notify_on_recovery is True


def test_defaults_when_no_escalation_key():
    cfg = _FakeAlertConfig(extra={})
    s = EscalationSettings.from_alert_config(cfg)
    assert s.threshold == _DEFAULT_THRESHOLD


def test_custom_threshold():
    cfg = _FakeAlertConfig(extra={"escalation": {"threshold": 5}})
    s = EscalationSettings.from_alert_config(cfg)
    assert s.threshold == 5


def test_custom_cooldown():
    cfg = _FakeAlertConfig(extra={"escalation": {"cooldown_minutes": 30}})
    s = EscalationSettings.from_alert_config(cfg)
    assert s.cooldown_minutes == 30


def test_notify_on_recovery_false():
    cfg = _FakeAlertConfig(extra={"escalation": {"notify_on_recovery": False}})
    s = EscalationSettings.from_alert_config(cfg)
    assert s.notify_on_recovery is False


def test_invalid_threshold_raises():
    cfg = _FakeAlertConfig(extra={"escalation": {"threshold": 0}})
    with pytest.raises(ValueError, match="threshold"):
        EscalationSettings.from_alert_config(cfg)


def test_negative_cooldown_raises():
    cfg = _FakeAlertConfig(extra={"escalation": {"cooldown_minutes": -1}})
    with pytest.raises(ValueError, match="cooldown_minutes"):
        EscalationSettings.from_alert_config(cfg)


def test_settings_are_frozen():
    s = EscalationSettings.from_alert_config(None)
    with pytest.raises((AttributeError, TypeError)):
        s.threshold = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# build_escalation_policy_from_config convenience wrapper
# ---------------------------------------------------------------------------

def test_convenience_wrapper_returns_settings():
    result = build_escalation_policy_from_config(None)
    assert isinstance(result, EscalationSettings)


def test_convenience_wrapper_passes_cfg():
    cfg = _FakeAlertConfig(extra={"escalation": {"threshold": 7}})
    result = build_escalation_policy_from_config(cfg)
    assert result.threshold == 7
