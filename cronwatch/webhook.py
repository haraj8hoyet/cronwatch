"""Webhook notification channel for cronwatch alerts."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from cronwatch.alerter import AlertEvent
from cronwatch.notifier import NotificationChannel

logger = logging.getLogger(__name__)


@dataclass
class WebhookChannel(NotificationChannel):
    """Sends alert events as JSON POST requests to a configured URL."""

    url: str
    timeout: int = 10
    extra_headers: Dict[str, str] = field(default_factory=dict)
    secret_header: Optional[str] = None
    secret_value: Optional[str] = None

    def send(self, event: AlertEvent) -> bool:
        payload = _build_payload(event)
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self.secret_header and self.secret_value:
            headers[self.secret_header] = self.secret_value
        req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
            logger.debug("Webhook delivered to %s (HTTP %s)", self.url, status)
            return 200 <= status < 300
        except urllib.error.HTTPError as exc:
            logger.warning("Webhook HTTP error %s for %s", exc.code, self.url)
        except urllib.error.URLError as exc:
            logger.warning("Webhook URL error for %s: %s", self.url, exc.reason)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected webhook error for %s: %s", self.url, exc)
        return False


def _build_payload(event: AlertEvent) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "job": event.job_name,
        "kind": event.kind,
        "subject": event.subject,
        "body": event.body,
    }
    if event.exit_code is not None:
        payload["exit_code"] = event.exit_code
    if event.timestamp is not None:
        payload["timestamp"] = event.timestamp.isoformat()
    return payload
