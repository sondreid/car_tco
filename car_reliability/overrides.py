"""Manual override handling for per-car scenario values."""

from __future__ import annotations

import json
from pathlib import Path

from .pricing.finn import build_cache_key


_OVERRIDE_TEMPLATE = {
    "price_nok": None,
    "km": None,
    "year": None,
    "model_year": None,
    "url": None,
    "known_repairs_nok": None,
    "current_resale_value_nok": None,
    "scheduled_maintenance_nok": None,
    "residual_base": None,
    "resale_nok": None,
}

_PRICE_INPUT_FIELDS = {"price_nok", "km", "year", "model_year", "url"}


def ensure_overrides_file(path: Path, fleet: list[dict]) -> None:
    """Create or extend the overrides scaffold for the current fleet."""
    payload: dict = {"fleet_overrides": {}}
    if path.exists():
        try:
            payload = json.loads(path.read_text())
        except Exception:
            payload = {"fleet_overrides": {}}
    fleet_overrides = payload.get("fleet_overrides")
    if not isinstance(fleet_overrides, dict):
        fleet_overrides = {}
    merged = dict(fleet_overrides)
    for car in fleet:
        key = build_cache_key(car)
        existing = merged.get(key, {})
        merged[key] = {**_OVERRIDE_TEMPLATE, **existing}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fleet_overrides": merged}, indent=2, sort_keys=True))


def load_overrides(path: Path, fleet: list[dict]) -> dict[str, dict]:
    """Load the fleet override map, generating the scaffold if needed."""
    ensure_overrides_file(path, fleet)
    payload = json.loads(path.read_text())
    fleet_overrides = payload.get("fleet_overrides")
    if not isinstance(fleet_overrides, dict):
        raise ValueError("override file must contain a fleet_overrides object")
    return fleet_overrides


def apply_fleet_overrides(fleet: list[dict], fleet_overrides: dict[str, dict]) -> list[dict]:
    """Apply non-null overrides to the in-memory fleet."""
    for car in fleet:
        lookup_key = build_cache_key(car)
        overrides = fleet_overrides.get(lookup_key, {})
        if not isinstance(overrides, dict):
            continue

        if overrides.get("price_nok") is not None:
            car["price_nok"] = float(overrides["price_nok"])
        if overrides.get("km") is not None:
            car["km"] = float(overrides["km"])
        if overrides.get("year") is not None:
            car["year"] = int(overrides["year"])
        if overrides.get("model_year") is not None:
            car["model_year"] = int(overrides["model_year"])
        if overrides.get("url") is not None:
            car["url"] = str(overrides["url"])
        if overrides.get("known_repairs_nok") is not None:
            car["known_repairs_nok"] = float(overrides["known_repairs_nok"])
        if overrides.get("current_resale_value_nok") is not None:
            car["current_resale_value_nok"] = float(overrides["current_resale_value_nok"])
        if overrides.get("scheduled_maintenance_nok") is not None:
            car["scheduled_maintenance_nok_override"] = float(
                overrides["scheduled_maintenance_nok"]
            )
        if overrides.get("residual_base") is not None:
            car["residual_base_override"] = float(overrides["residual_base"])
        if overrides.get("resale_nok") is not None:
            car["resale_nok_override"] = float(overrides["resale_nok"])
    return fleet


def has_active_overrides(fleet_overrides: dict[str, dict]) -> bool:
    """Return True when any override field is explicitly set."""
    for entry in fleet_overrides.values():
        if not isinstance(entry, dict):
            continue
        if any(value is not None for value in entry.values()):
            return True
    return False


def has_price_input_overrides(fleet_overrides: dict[str, dict]) -> bool:
    """Return True when an override changes price-scrape input fields."""
    for entry in fleet_overrides.values():
        if not isinstance(entry, dict):
            continue
        for key in _PRICE_INPUT_FIELDS:
            if entry.get(key) is not None:
                return True
    return False
