"""Helpers for JSON caches stored under the output directory."""

from __future__ import annotations

import json
from pathlib import Path


def load_entries_cache(path: Path, label: str) -> dict[str, dict]:
    """Load one cache file with a top-level entries object."""
    if not path.exists():
        raise FileNotFoundError(f"{label} cache not found: {path}")
    payload = json.loads(path.read_text())
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        raise ValueError(f"{label} cache missing entries object")
    return entries


def save_entries_cache(path: Path, entries: dict[str, dict]) -> None:
    """Write entries into one JSON cache file, merging by key."""
    existing: dict[str, dict] = {}
    if path.exists():
        try:
            existing = load_entries_cache(path, path.stem)
        except Exception:
            existing = {}
    merged = dict(existing)
    merged.update(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"entries": merged}, indent=2, sort_keys=True))
