"""Watcher: ties together tracker, scheduler, and alerter to monitor cron jobs."""

import logging
import time
from datetime import datetime, timezone
from typing import Dict

from cronwatch.alerter import AlertEvent, Alerter
from cronwatch.config import CronwatchConfig, JobConfig
from cronwatch.scheduler import MissedRunDetector
from cronwatch.tracker import JobRun, JobTracker

logger = logging.getLogger(__name__)


class JobWatcher:
    """Monitors a single job for missed runs and execution failures."""

    def __init__(self, job: JobConfig, tracker: JobTracker, alerter: Alerter) -> None:
        self.job = job
        self.tracker = tracker
        self.alerter = alerter
        self.detector = MissedRunDetector(job.schedule)
        self._alerted_missed: set = set()

    def check_missed(self, now: datetime | None = None) -> bool:
        """Check if the job has a missed run and alert if so. Returns True if missed."""
        now = now or datetime.now(timezone.utc)
        if self.detector.is_missed(now):
            expected = self.detector.last_expected_run(now)
            if expected and expected not in self._alerted_missed:
                logger.warning("Missed run detected for job '%s' at %s", self.job.name, expected)
                event = AlertEvent(
                    job_name=self.job.name,
                    kind="missed",
                    timestamp=expected,
                )
                self.alerter.send(event)
                self._alerted_missed.add(expected)
                return True
        return False

    def handle_finish(self, run: JobRun) -> None:
        """Called after a job run finishes; alerts on failure."""
        if run.failed:
            logger.error("Job '%s' failed with exit code %s", self.job.name, run.exit_code)
            event = AlertEvent(
                job_name=self.job.name,
                kind="failure",
                timestamp=run.started_at,
                exit_code=run.exit_code,
                duration=run.duration,
            )
            self.alerter.send(event)


class CronWatcher:
    """Top-level watcher that manages all configured jobs."""

    def __init__(self, config: CronwatchConfig) -> None:
        self.config = config
        self.alerter = Alerter(config.alerts)
        self._trackers: Dict[str, JobTracker] = {}
        self._watchers: Dict[str, JobWatcher] = {}
        for job in config.jobs:
            tracker = JobTracker()
            self._trackers[job.name] = tracker
            self._watchers[job.name] = JobWatcher(job, tracker, self.alerter)

    def get_tracker(self, job_name: str) -> JobTracker:
        return self._trackers[job_name]

    def get_watcher(self, job_name: str) -> JobWatcher:
        return self._watchers[job_name]

    def check_all_missed(self, now: datetime | None = None) -> None:
        """Check all jobs for missed runs."""
        now = now or datetime.now(timezone.utc)
        for watcher in self._watchers.values():
            watcher.check_missed(now)
