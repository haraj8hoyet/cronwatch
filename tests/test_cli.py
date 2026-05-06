"""Tests for cronwatch.cli module."""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli import build_arg_parser, main


@pytest.fixture
def minimal_config(tmp_path) -> Path:
    cfg = tmp_path / "cronwatch.yaml"
    cfg.write_text(
        textwrap.dedent("""\
            jobs:
              - name: heartbeat
                schedule: "* * * * *"
                command: echo ok
            alerts:
              email: admin@example.com
              smtp_host: localhost
              smtp_port: 25
        """)
    )
    return cfg


def test_arg_parser_defaults():
    parser = build_arg_parser()
    args = parser.parse_args([])
    assert args.config == "/etc/cronwatch/config.yaml"
    assert args.interval == 60
    assert args.verbose is False


def test_arg_parser_custom_values():
    parser = build_arg_parser()
    args = parser.parse_args(["-c", "/tmp/cw.yaml", "--interval", "30", "-v"])
    assert args.config == "/tmp/cw.yaml"
    assert args.interval == 30
    assert args.verbose is True


def test_main_returns_1_when_config_missing(tmp_path):
    result = main(["-c", str(tmp_path / "nonexistent.yaml")])
    assert result == 1


def test_main_runs_daemon_then_exits(minimal_config):
    """main() starts daemon and returns 0 after clean shutdown."""
    with patch("cronwatch.cli.run_daemon") as mock_run:
        result = main(["-c", str(minimal_config), "--interval", "5"])
    mock_run.assert_called_once_with(str(minimal_config), 5)
    assert result == 0


def test_run_daemon_calls_check_all_missed(minimal_config):
    """run_daemon loops and calls check_all_missed until shutdown."""
    import cronwatch.cli as cli_mod

    call_count = 0

    def fake_sleep(n):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            cli_mod._SHUTDOWN = True

    with patch("cronwatch.cli.time.sleep", side_effect=fake_sleep), \
         patch("cronwatch.watcher.Alerter"):
        cli_mod._SHUTDOWN = False
        from cronwatch.cli import run_daemon
        run_daemon(str(minimal_config), interval=1)

    assert call_count == 2
    cli_mod._SHUTDOWN = False  # reset for other tests
