"""Notification channel abstraction for cronwatch alerts."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from cronwatch.alerter import AlertEvent

logger = logging.getLogger(__name__)


class NotificationChannel(Protocol):
    """Protocol that all notification channels must satisfy."""

    def send(self, event: AlertEvent) -> bool:
        """Send an alert event. Returns True on success."""
        ...


class EmailChannel:
    """Sends alert notifications via SMTP email."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        recipients: list[str],
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send(self, event: AlertEvent) -> bool:
        msg = EmailMessage()
        msg["Subject"] = event.subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(event.body)
        try:
            cls = smtplib.SMTP_SSL if self.use_tls else smtplib.SMTP
            with cls(self.smtp_host, self.smtp_port) as smtp:
                if self.username and self.password:
                    smtp.login(self.username, self.password)
                smtp.send_message(msg)
            logger.info("Email alert sent for job '%s'", event.job_name)
            return True
        except smtplib.SMTPException as exc:
            logger.error("Failed to send email alert: %s", exc)
            return False


class LogChannel:
    """Writes alert notifications to the Python logger (useful for testing)."""

    def __init__(self, level: int = logging.WARNING) -> None:
        self.level = level

    def send(self, event: AlertEvent) -> bool:
        logger.log(self.level, "[cronwatch] %s\n%s", event.subject, event.body)
        return True
