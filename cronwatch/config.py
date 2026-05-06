"""Configuration loader for cronwatch."""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobConfig:
    name: str
    schedule: str
    command: str
    timeout: int = 300
    alert_on_failure: bool = True
    alert_on_missed: bool = True
    max_retries: int = 0


@dataclass
class AlertConfig:
    email: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_address: str = "cronwatch@localhost"


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    log_file: str = "/var/log/cronwatch.log"
    state_file: str = "/var/lib/cronwatch/state.json"
    check_interval: int = 60


def load_config(path: str) -> CronwatchConfig:
    """Load and parse the YAML configuration file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raise ValueError("Config file is empty or invalid.")

    alert_data = raw.get("alert", {})
    alert = AlertConfig(**{k: v for k, v in alert_data.items() if k in AlertConfig.__dataclass_fields__})

    jobs = []
    for job_data in raw.get("jobs", []):
        jobs.append(JobConfig(**{k: v for k, v in job_data.items() if k in JobConfig.__dataclass_fields__}))

    global_keys = {"log_file", "state_file", "check_interval"}
    global_data = {k: v for k, v in raw.items() if k in global_keys}

    return CronwatchConfig(jobs=jobs, alert=alert, **global_data)
