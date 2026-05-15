"""Alert annotation: attach structured metadata to alert events for downstream enrichment."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Annotation:
    """A single key/value annotation attached to an alert."""

    key: str
    value: str
    source: str = "user"  # 'user' | 'system' | 'rule'

    def __str__(self) -> str:
        return f"{self.key}={self.value} (source={self.source})"


class AnnotationSet:
    """Ordered collection of annotations for one alert event."""

    def __init__(self) -> None:
        self._annotations: Dict[str, Annotation] = {}

    def add(self, key: str, value: str, source: str = "user") -> None:
        """Add or overwrite an annotation by key."""
        self._annotations[key] = Annotation(key=key, value=value, source=source)

    def get(self, key: str) -> Optional[str]:
        """Return the value for *key*, or None if absent."""
        ann = self._annotations.get(key)
        return ann.value if ann is not None else None

    def remove(self, key: str) -> bool:
        """Remove annotation by key; return True if it existed."""
        return self._annotations.pop(key, None) is not None

    def all(self) -> list[Annotation]:
        """Return all annotations in insertion order."""
        return list(self._annotations.values())

    def as_dict(self) -> Dict[str, str]:
        """Return a plain key→value mapping."""
        return {k: v.value for k, v in self._annotations.items()}

    def __len__(self) -> int:
        return len(self._annotations)

    def __contains__(self, key: str) -> bool:
        return key in self._annotations


class AnnotationRegistry:
    """Per-job annotation store keyed by job name."""

    def __init__(self) -> None:
        self._store: Dict[str, AnnotationSet] = {}

    def for_job(self, job_name: str) -> AnnotationSet:
        """Return (creating if needed) the AnnotationSet for *job_name*."""
        if job_name not in self._store:
            self._store[job_name] = AnnotationSet()
        return self._store[job_name]

    def annotate(self, job_name: str, key: str, value: str, source: str = "user") -> None:
        """Convenience: add/overwrite a single annotation for *job_name*."""
        self.for_job(job_name).add(key, value, source)

    def job_names(self) -> list[str]:
        """Return all job names that have annotations."""
        return list(self._store.keys())
