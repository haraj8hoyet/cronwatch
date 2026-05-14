"""Tests for cronwatch.routing_factory.build_alert_router."""

from unittest.mock import MagicMock, patch
import pytest

from cronwatch.routing_factory import build_alert_router
from cronwatch.routing import AlertRouter


# ---------------------------------------------------------------------------
# Minimal fake config helpers
# ---------------------------------------------------------------------------

class _FakeAlertCfg:
    def __init__(self, routing=None, channel_groups=None, channels=None):
        self.routing = routing
        self.channel_groups = channel_groups
        self.channels = channels or []
        self.smtp_host = None
        self.smtp_port = 587
        self.smtp_user = None
        self.smtp_password = None
        self.from_addr = None
        self.to = []
        self.webhooks = None


class _FakeCfg:
    def __init__(self, alert=None):
        self.jobs = []
        self.alert = alert


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("cronwatch.routing_factory.build_dispatcher")
def test_no_alert_config_returns_router(mock_build):
    mock_build.return_value = MagicMock()
    cfg = _FakeCfg(alert=None)
    router = build_alert_router(cfg)
    assert isinstance(router, AlertRouter)
    assert router.rule_count == 0


@patch("cronwatch.routing_factory.build_dispatcher")
def test_routing_rules_are_added(mock_build):
    mock_build.return_value = MagicMock()
    alert_cfg = _FakeAlertCfg(
        routing=[
            {"pattern": "backup_*", "channel_group": "ops", "priority": 5},
            {"pattern": "report_*", "channel_group": "reports"},
        ]
    )
    cfg = _FakeCfg(alert=alert_cfg)
    router = build_alert_router(cfg)
    assert router.rule_count == 2


@patch("cronwatch.routing_factory.build_dispatcher")
def test_empty_routing_list_produces_no_rules(mock_build):
    mock_build.return_value = MagicMock()
    alert_cfg = _FakeAlertCfg(routing=[])
    cfg = _FakeCfg(alert=alert_cfg)
    router = build_alert_router(cfg)
    assert router.rule_count == 0


@patch("cronwatch.routing_factory.build_dispatcher")
def test_channel_groups_registered(mock_build):
    default_disp = MagicMock()
    group_disp = MagicMock()
    mock_build.side_effect = [default_disp, group_disp]

    ops_alert = _FakeAlertCfg()
    alert_cfg = _FakeAlertCfg(
        routing=[{"pattern": "backup_*", "channel_group": "ops"}],
        channel_groups={"ops": ops_alert},
    )
    cfg = _FakeCfg(alert=alert_cfg)
    router = build_alert_router(cfg)
    # build_dispatcher called twice: once for default, once for ops group
    assert mock_build.call_count == 2
    assert router.rule_count == 1


@patch("cronwatch.routing_factory.build_dispatcher")
def test_rule_default_priority_zero(mock_build):
    mock_build.return_value = MagicMock()
    alert_cfg = _FakeAlertCfg(
        routing=[{"pattern": "*", "channel_group": "x"}]
    )
    cfg = _FakeCfg(alert=alert_cfg)
    router = build_alert_router(cfg)
    assert router._rules[0].priority == 0
