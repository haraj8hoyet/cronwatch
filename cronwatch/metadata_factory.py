"""Factory for building a MetadataStore from CronwatchConfig."""

from __future__ import annotations

import os
from typing import Optional

from cronwatch.metadata import MetadataStore

_DEFAULT_DB_PATH = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "cronwatch",
    "metadata.db",
)


def build_metadata_store(config=None) -> MetadataStore:
    """Return a MetadataStore configured from *config*.

    Looks for ``config.storage.metadata_db``; falls back to a sensible
    XDG-compliant default when the key is absent or *config* is ``None``.
    """
    db_path = _resolve_db_path(config)
    return MetadataStore(db_path)


def _resolve_db_path(config) -> str:
    """Extract the metadata DB path from config, or return the default."""
    if config is None:
        return _DEFAULT_DB_PATH

    storage = getattr(config, "storage", None)
    if storage is None:
        return _DEFAULT_DB_PATH

    # Accept both dict-style and attribute-style storage configs.
    if isinstance(storage, dict):
        return storage.get("metadata_db", _DEFAULT_DB_PATH)

    return getattr(storage, "metadata_db", _DEFAULT_DB_PATH)
