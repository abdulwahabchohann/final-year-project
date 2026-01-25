"""Lightweight helpers for caching JSON payloads."""

from __future__ import annotations

import json
from typing import Any

from django.core.cache import cache


def get_cached_json(key: str) -> Any | None:
    """Return a JSON-deserialised payload from cache or ``None`` if missing/invalid."""
    raw = cache.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        cache.delete(key)
        return None


def set_cached_json(key: str, value: Any, timeout: int) -> None:
    """Serialise the given payload to JSON and store it in cache."""
    cache.set(key, json.dumps(value), timeout)


def delete_cached(key: str) -> None:
    """Remove a cached key if it exists."""
    cache.delete(key)
