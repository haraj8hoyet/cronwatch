"""Command-line entry point for cronwatch daemon."""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from cronwatch.config import load_config
from cronwatch.watcher import CronWatcher

logger = logging.getLogger(__name__)

_SHUTDOWN = False


def _handle_signal(signum, frame):
    global _SHUTDOWN
    logger.info("Received signal %s, shutting down.", signum)
    _SHUTDOWN = True


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor cron job execution and send alerts on failures or missed runs.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="/etc/cronwatch/config.yaml",
        help="Path to cronwatch configuration file (default: /etc/cronwatch/config.yaml)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds (default: 60)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    return parser


def run_daemon(config_path: str, interval: int) -> None:
    """Main daemon loop."""
    config = load_config(config_path)
    cw = CronWatcher(config)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info(
        "cronwatch started — monitoring %d job(s) every %ds", len(config.jobs), interval
    )

    while not _SHUTDOWN:
        now = datetime.now(timezone.utc)
        cw.check_all_missed(now)
        time.sleep(interval)

    logger.info("cronwatch stopped.")


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not Path(args.config).exists():
        logger.error("Config file not found: %s", args.config)
        return 1

    try:
        run_daemon(args.config, args.interval)
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected error: %s", exc)
        return 2

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
