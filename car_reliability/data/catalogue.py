"""Per-model catalogue data loaded from checked-in JSON."""

from __future__ import annotations

from typing import Any

from ._json import load_json_data


def _load_catalogue() -> dict[str, dict[str, Any]]:
    payload = load_json_data("catalogue.json")
    if not isinstance(payload, dict):
        raise ValueError("catalogue.json must contain an object keyed by model name")
    return payload


CAR_CATALOGUE: dict[str, dict[str, Any]] = _load_catalogue()
