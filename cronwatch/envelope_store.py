"""In-memory store for recent AlertEnvelopes, useful for status reporting."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Deque, Iterator, List, Optional

from cronwatch.envelope import AlertEnvelope

_DEFAULT_MAX_SIZE = 500


class EnvelopeStore:
    """Thread-safe ring buffer of recent AlertEnvelopes."""

    def __init__(self, max_size: int = _DEFAULT_MAX_SIZE) -> None:
        self._max_size = max_size
        self._store: Deque[AlertEnvelope] = deque(maxlen=max_size)
        self._lock = Lock()

    def put(self, envelope: AlertEnvelope) -> None:
        """Add an envelope to the store."""
        with self._lock:
            self._store.append(envelope)

    def all(self) -> List[AlertEnvelope]:
        """Return a snapshot of all stored envelopes, oldest first."""
        with self._lock:
            return list(self._store)

    def for_job(self, job_name: str) -> List[AlertEnvelope]:
        """Return envelopes for a specific job, oldest first."""
        with self._lock:
            return [e for e in self._store if e.event.job_name == job_name]

    def pending(self) -> List[AlertEnvelope]:
        """Return envelopes that have not yet been delivered or suppressed."""
        with self._lock:
            return [e for e in self._store if not e.delivered and not e.suppressed]

    def suppressed(self) -> List[AlertEnvelope]:
        """Return suppressed envelopes."""
        with self._lock:
            return [e for e in self._store if e.suppressed]

    def count(self) -> int:
        """Return the total number of stored envelopes."""
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        """Remove all envelopes from the store."""
        with self._lock:
            self._store.clear()
