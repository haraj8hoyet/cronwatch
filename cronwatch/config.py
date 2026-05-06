"""Configuration loading and dataclasses for cronwatch."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml
from jsonschema import validate, ValidationError

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "config_schema.yaml")


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout: int = 3600
    grace_period: int = 60


@dataclass
class AlertConfig:
    email: Optional[Dict[str, Any]] = None


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    log_level: str = "INFO"


def _load_schema() -> dict:
    with open(_SCHEMA_PATH) as fh:
        return yaml.safe_load(fh)


def load_config(path: str) -> CronwatchConfig:
    """Load and validate a cronwatch YAML config file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as fh:
        raw = yaml.safe_load(fh)

    if raw is None:
        raise ValueError("Config file is empty")

    schema = _load_schema()
    try:
        validate(instance=raw, schema=schema)
    except ValidationError as exc:
        raise ValueError(f"Invalid config: {exc.message}") from exc

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            command=j["command"],
            timeout=j.get("timeout", 3600),
            grace_period=j.get("grace_period", 60),
        )
        for j in raw.get("jobs", [])
    ]

    alert_raw = raw.get("alert", {})
    alert = AlertConfig(email=alert_raw.get("email"))

    return CronwatchConfig(
        jobs=jobs,
        alert=alert,
        log_level=raw.get("log_level", "INFO"),
    )
