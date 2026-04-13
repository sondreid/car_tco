"""
Reference fleet builder.

``build_reference_fleet`` returns a list of car dicts representing the cars
that will be analysed.  Each entry has the shape expected by the pipeline:

    {
        "model": str,          # must match a key in CAR_CATALOGUE
        "name": str,
        "description": str,
        "price_nok": float,
        "year": int,
        "km": float,
        "url": str,
    }

Adding a new car only requires appending an entry here (or passing overrides
at runtime via ``extra_cars``).  Prices can be patched at runtime via
``price_overrides`` so CLI/notebooks don't have to touch this file.

This module supports two ways of creating a car instance:
1. ``build_car("Model Name")`` → copy the repo's default reference instance
2. ``build_car("Model Name", price_nok=..., year=..., km=...)`` → copy the
   default reference instance and override the specific fields
"""

from __future__ import annotations

import copy


_DEFAULT_FLEET: list[dict] = [
    {
        "model": "Toyota Avensis",
        "name": "Toyota Avensis existing car",
        "description": "existing car, assumed 2012 petrol, known repairs required",
        "existing_car": True,
        "price_nok": 0,
        "current_resale_value_nok": 20_000,
        "year": 2012,
        "km": 182_000,
        "known_repairs_nok": 60_000,
        "exclude_from_price_estimation": True,
        "url": "",
    },
    {
        "model": "Toyota RAV4 Hybrid",
        "name": "Toyota RAV4 Hybrid reference",
        "description": "manual reference with updated spec fuel consumption",
        "price_nok": 280_000,
        "year": 2019,
        "km": 120_000,
        "url": "",
    },
    {
        "model": "Mitsubishi Outlander PHEV",
        "name": "Mitsubishi Outlander PHEV reference",
        "description": "manual reference with 50% full-charge 60 km trip assumption",
        "price_nok": 220_000,
        "year": 2020,
        "km": 60_000,
        "url": "",
    },
    {
        "model": "Volkswagen Passat GTE",
        "name": "Volkswagen Passat GTE reference",
        "description": "manual reference plug-in hybrid estate",
        "price_nok": 200_000,
        "year": 2020,
        "km": 90_000,
        "url": "",
    },
    {
        "model": "Skoda Kodiaq 2.0 TDI 4x4",
        "name": "Skoda Kodiaq 2.0 TDI 4x4 reference",
        "description": "FINN reference within current price/km comparison window",
        "price_nok": 269_000,
        "year": 2018,
        "km": 132_700,
        "url": "https://www.finn.no/mobility/item/459341833",
    },
    {
        "model": "Mazda CX-5 diesel AWD",
        "name": "Mazda CX-5 diesel AWD reference",
        "description": "FINN reference within current price/km comparison window",
        "price_nok": 179_532,
        "year": 2016,
        "km": 112_200,
        "url": "https://www.finn.no/mobility/item/448852607",
    },
    {
        "model": "Peugeot 508 SW 2.0 BlueHDi",
        "name": "Peugeot 508 SW 2.0 BlueHDi reference",
        "description": "FINN reference within current price/km comparison window",
        "price_nok": 139_532,
        "year": 2015,
        "km": 132_500,
        "url": "https://www.finn.no/mobility/item/449340768",
    },
    {
        "model": "Tesla Model Y",
        "name": "Tesla Model Y reference",
        "description": "FINN reference within current price/km comparison window",
        "price_nok": 264_532,
        "year": 2021,
        "km": 68_901,
        "url": "https://www.finn.no/mobility/item/459624653",
    },
    {
        "model": "Mercedes EQC",
        "name": "Mercedes EQC reference",
        "description": "FINN reference within current price/km comparison window",
        "price_nok": 260_000,
        "year": 2020,
        "km": 126_000,
        "url": "https://www.finn.no/mobility/item/435035902",
    },
    {
        "model": "Skoda Superb 2.0 TDI 4x4",
        "name": "Skoda Superb 2.0 TDI 4x4 reference",
        "description": "manual reference conventional diesel",
        "price_nok": 180_000,
        "year": 2018,
        "km": 140_000,
        "url": "",
    },
]

_DEFAULT_BY_MODEL: dict[str, dict] = {car["model"]: car for car in _DEFAULT_FLEET}


def build_car(model: str, **overrides) -> dict:
    """
    Build one car instance from a known model.

    Two modes are supported:
    - model only: copy the repo's default reference instance for that model
    - model + overrides: copy the default instance, then patch fields such as
      ``price_nok``, ``year``, ``km``, ``known_repairs_nok``,
      ``current_resale_value_nok`` or ``url``

    If the model has no default reference instance, the caller must supply at
    least ``price_nok``, ``year`` and ``km`` in overrides.
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
    return car


def build_reference_fleet(
    price_overrides: dict[str, float] | None = None,
    extra_cars: list[dict] | None = None,
) -> list[dict]:
    """
    Return the reference fleet as a list of car dicts.

    Parameters
    ----------
    price_overrides:
        Map of {model_name: new_price_nok}.  Useful for updating a single
        car's purchase price without touching source code.
    extra_cars:
        Additional car dicts appended after the default fleet.  Must contain
        at least ``model``, ``price_nok``, ``year``, ``km``.
    """
    fleet = copy.deepcopy(_DEFAULT_FLEET)

    if price_overrides:
        for car in fleet:
            if car["model"] in price_overrides:
                car["price_nok"] = float(price_overrides[car["model"]])

    if extra_cars:
        fleet.extend(extra_cars)

    return fleet
