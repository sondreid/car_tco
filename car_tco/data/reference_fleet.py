"""
Reference fleet builder.

The fleet to analyse comes from a user-provided fleet JSON file, falling back
to the small checked-in example fleet. ``build_reference_fleet`` returns a
list of car dicts representing the cars that will be analysed.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from ._json import load_json_data


def _normalize_fleet(payload: object, source: str) -> list[dict]:
    if not isinstance(payload, list):
        raise ValueError(f"{source} must contain a list of car dicts")
    fleet: list[dict] = []
    for car in payload:
        if not isinstance(car, dict):
            raise ValueError(f"{source} entries must be objects")
        normalized = copy.deepcopy(car)
        if "model_year" not in normalized:
            normalized["model_year"] = int(normalized["year"])
        fleet.append(normalized)
    return fleet


def load_fleet_file(path: str | Path) -> list[dict]:
    """Load a fleet JSON file into a normalized list of car dicts."""
    path = Path(path)
    return _normalize_fleet(json.loads(path.read_text()), str(path))


_EXAMPLE_FLEET: list[dict] = _normalize_fleet(
    load_json_data("example_fleet.json"), "example_fleet.json"
)
_DEFAULT_BY_MODEL: dict[str, dict] = {car["model"]: car for car in _EXAMPLE_FLEET}


def build_car(model: str, **overrides) -> dict:
    """
    Build one car instance from a known model.

    Two modes are supported:
    - model only: copy the example instance for that model
    - model + overrides: copy the example instance, then patch specific fields
    """
    if model in _DEFAULT_BY_MODEL:
        car = copy.deepcopy(_DEFAULT_BY_MODEL[model])
    else:
        required = {"price_nok", "year", "km"}
        missing = sorted(required.difference(overrides))
        if missing:
            missing_str = ", ".join(missing)
            raise KeyError(
                f"Unknown reference model {model!r}; overrides must include {missing_str}"
            )
        car = {"model": model}

    car.update(overrides)
    car["model"] = model
    if "model_year" not in car:
        car["model_year"] = int(car["year"])
    return car


def build_reference_fleet(
    price_overrides: dict[str, float] | None = None,
    extra_cars: list[dict] | None = None,
    fleet_path: str | Path | None = None,
) -> list[dict]:
    """Return the fleet as a list of car dicts, from a file or the example fleet."""
    if fleet_path is not None:
        fleet = load_fleet_file(fleet_path)
    else:
        fleet = copy.deepcopy(_EXAMPLE_FLEET)

    if price_overrides:
        for car in fleet:
            if car["model"] in price_overrides:
                car["price_nok"] = float(price_overrides[car["model"]])

    if extra_cars:
        fleet.extend(copy.deepcopy(extra_cars))

    for car in fleet:
        if "model_year" not in car:
            car["model_year"] = int(car["year"])

    return fleet
