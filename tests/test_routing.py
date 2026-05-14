"""Tests for cronwatch.routing (AlertRouter / RoutingRule)."""

from unittest.mock import MagicMock, patch
import pytest

from cronwatch.alerter import AlertEvent
from cronwatch.dispatch import Dispatcher
from cronwatch.routing import AlertRouter, RoutingRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(job_name: str, kind: str = "failure") -> AlertEvent:
    return AlertEvent(job_name=job_name, kind=kind, exit_code=1, detail="")


def _mock_dispatcher(accept: bool = True) -> Dispatcher:
    d = MagicMock(spec=Dispatcher)
    d.dispatch.return_value = accept
    return d


# ---------------------------------------------------------------------------
# RoutingRule
# ---------------------------------------------------------------------------

class TestRoutingRule:
    def test_exact_match(self):
        rule = RoutingRule(pattern="backup_db", channel_group="ops")
        assert rule.matches("backup_db") is True

    def test_glob_wildcard(self):
        rule = RoutingRule(pattern="backup_*", channel_group="ops")
        assert rule.matches("backup_daily") is True
        assert rule.matches("backup_weekly") is True

    def test_glob_no_match(self):
        rule = RoutingRule(pattern="backup_*", channel_group="ops")
        assert rule.matches("report_daily") is False

    def test_default_priority_is_zero(self):
        rule = RoutingRule(pattern="*", channel_group="default")
        assert rule.priority == 0


# ---------------------------------------------------------------------------
# AlertRouter
# ---------------------------------------------------------------------------

@pytest.fixture
def default_dispatcher():
    return _mock_dispatcher()


@pytest.fixture
def router(default_dispatcher):
    return AlertRouter(default=default_dispatcher)


class TestAlertRouter:
    def test_no_rules_uses_default(self, router, default_dispatcher):
        event = _make_event("any_job")
        resolved = router.resolve(event)
        assert resolved is default_dispatcher

    def test_matching_rule_returns_group_dispatcher(self, router):
        ops = _mock_dispatcher()
        router.register_group("ops", ops)
        router.add_rule(RoutingRule(pattern="backup_*", channel_group="ops"))
        event = _make_event("backup_daily")
        assert router.resolve(event) is ops

    def test_non_matching_rule_falls_back_to_default(self, router, default_dispatcher):
        ops = _mock_dispatcher()
        router.register_group("ops", ops)
        router.add_rule(RoutingRule(pattern="backup_*", channel_group="ops"))
        event = _make_event("report_daily")
        assert router.resolve(event) is default_dispatcher

    def test_higher_priority_rule_wins(self, router):
        low = _mock_dispatcher()
        high = _mock_dispatcher()
        router.register_group("low", low)
        router.register_group("high", high)
        router.add_rule(RoutingRule(pattern="*", channel_group="low", priority=1))
        router.add_rule(RoutingRule(pattern="backup_*", channel_group="high", priority=10))
        event = _make_event("backup_daily")
        assert router.resolve(event) is high

    def test_route_calls_dispatch_and_returns_result(self, router, default_dispatcher):
        default_dispatcher.dispatch.return_value = True
        event = _make_event("any_job")
        result = router.route(event)
        default_dispatcher.dispatch.assert_called_once_with(event)
        assert result is True

    def test_rule_count(self, router):
        assert router.rule_count == 0
        router.add_rule(RoutingRule(pattern="*", channel_group="x"))
        assert router.rule_count == 1

    def test_unknown_channel_group_falls_back_to_default(self, router, default_dispatcher):
        router.add_rule(RoutingRule(pattern="*", channel_group="nonexistent"))
        event = _make_event("any_job")
        assert router.resolve(event) is default_dispatcher
