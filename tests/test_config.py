"""Tests for the cronwatch configuration loader."""

import os
import pytest
import tempfile
import yaml

from cronwatch.config import load_config, CronwatchConfig, JobConfig, AlertConfig


MINIMAL_CONFIG = {
    "jobs": [
        {"name": "test_job", "schedule": "* * * * *", "command": "echo hello"}
    ]
}

FULL_CONFIG = {
    "log_file": "/tmp/cronwatch.log",
    "state_file": "/tmp/cronwatch_state.json",
    "check_interval": 30,
    "alert": {
        "email": "admin@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "from_address": "cw@example.com",
    },
    "jobs": [
        {
            "name": "backup",
            "schedule": "0 1 * * *",
            "command": "/bin/backup.sh",
            "timeout": 900,
            "alert_on_failure": True,
            "alert_on_missed": False,
            "max_retries": 3,
        }
    ],
}


def write_temp_config(data: dict) -> str:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, tmp)
    tmp.close()
    return tmp.name


def test_load_minimal_config():
    path = write_temp_config(MINIMAL_CONFIG)
    try:
        cfg = load_config(path)
        assert isinstance(cfg, CronwatchConfig)
        assert len(cfg.jobs) == 1
        assert cfg.jobs[0].name == "test_job"
        assert cfg.jobs[0].timeout == 300  # default
    finally:
        os.unlink(path)


def test_load_full_config():
    path = write_temp_config(FULL_CONFIG)
    try:
        cfg = load_config(path)
        assert cfg.check_interval == 30
        assert cfg.alert.email == "admin@example.com"
        assert cfg.alert.smtp_port == 465
        assert cfg.jobs[0].max_retries == 3
        assert cfg.jobs[0].alert_on_missed is False
    finally:
        os.unlink(path)


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.yaml")


def test_empty_config_file():
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    tmp.close()
    try:
        with pytest.raises(ValueError, match="empty or invalid"):
            load_config(tmp.name)
    finally:
        os.unlink(tmp.name)


def test_default_alert_config():
    path = write_temp_config(MINIMAL_CONFIG)
    try:
        cfg = load_config(path)
        assert cfg.alert.smtp_host == "localhost"
        assert cfg.alert.smtp_port == 25
        assert cfg.alert.email is None
    finally:
        os.unlink(path)
