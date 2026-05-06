"""Alert dispatching module for cronwatch."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from cronwatch.config import AlertConfig

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    job_name: str
    event_type: str  # 'failure' | 'missed'
    timestamp: datetime
    exit_code: Optional[int] = None
    message: Optional[str] = None

    def subject(self) -> str:
        return f"[cronwatch] {self.event_type.upper()}: {self.job_name}"

    def body(self) -> str:
        lines = [
            f"Job:       {self.job_name}",
            f"Event:     {self.event_type}",
            f"Timestamp: {self.timestamp.isoformat()}",
        ]
        if self.exit_code is not None:
            lines.append(f"Exit code: {self.exit_code}")
        if self.message:
            lines.append(f"Details:   {self.message}")
        return "\n".join(lines)


class Alerter:
    """Sends alerts via configured channels."""

    def __init__(self, config: AlertConfig) -> None:
        self.config = config

    def send(self, event: AlertEvent) -> None:
        if self.config.email:
            try:
                self._send_email(event)
            except Exception as exc:  # pragma: no cover
                logger.error("Failed to send email alert: %s", exc)
        else:
            logger.warning("No alert channel configured; logging event only.")
        logger.info("Alert dispatched: %s", event.subject())

    def _send_email(self, event: AlertEvent) -> None:
        cfg = self.config.email
        msg = MIMEMultipart()
        msg["From"] = cfg["from"]
        msg["To"] = ", ".join(cfg["to"])
        msg["Subject"] = event.subject()
        msg.attach(MIMEText(event.body(), "plain"))

        with smtplib.SMTP(cfg.get("host", "localhost"), cfg.get("port", 25)) as server:
            if cfg.get("tls"):
                server.starttls()
            if cfg.get("username"):
                server.login(cfg["username"], cfg["password"])
            server.sendmail(cfg["from"], cfg["to"], msg.as_string())
        logger.debug("Email alert sent to %s", cfg["to"])
