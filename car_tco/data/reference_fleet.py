"""
Reference fleet builder backed by checked-in JSON.

``build_reference_fleet`` returns a list of car dicts representing the cars
that will be analysed.
"""

from __future__ import annotations

import copy

from ._json import load_json_data


def _load_default_fleet() -> list[dict]:
    payload = load_json_data("reference_fleet.json")
    if not isinstance(payload, list):
        raise ValueError("reference_fleet.json must contain a list of car dicts")
    fleet: list[dict] = []
    for car in payload:
        if not isinstance(car, dict):
            raise ValueError("reference_fleet.json entries must be objects")
        normalized = copy.deepcopy(car)
        if "model_year" not in normalized:
            normalized["model_year"] = int(normalized["year"])
        fleet.append(normalized)
    return fleet


_DEFAULT_FLEET: list[dict] = _load_default_fleet()
_DEFAULT_BY_MODEL: dict[str, dict] = {car["model"]: car for car in _DEFAULT_FLEET}


def build_car(model: str, **overrides) -> dict:
    """
    Build one car instance from a known model.

    Two modes are supported:
    - model only: copy the repo's default reference instance for that model
    - model + overrides: copy the default instance, then patch specific fields
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
) -> list[dict]:
    """Return the reference fleet as a list of car dicts."""
    fleet = copy.deepcopy(_DEFAULT_FLEET)

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
