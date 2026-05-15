"""
Fuel / electricity cost over the ownership horizon.

Consumption figures come from the catalogue, with an optional override for
PHEV dynamic blending (controlled by ``Assumptions.phev_dynamic_consumption``).
"""

from __future__ import annotations

from ..data.catalogue import CAR_CATALOGUE
from ..assumptions import Assumptions

_PHEV_MODEL = "Mitsubishi Outlander PHEV"


def _effective_consumption(model: str, assumptions: Assumptions) -> dict[str, float]:
    """
    Return the effective consumption dict for *model*, applying PHEV blending
    when appropriate.
    """
    catalogue_consumption = dict(CAR_CATALOGUE[model]["consumption"])

    if model == _PHEV_MODEL and assumptions.phev_dynamic_consumption:
        petrol_eff, kwh_eff = assumptions.phev_effective_consumption()
        return {"petrol_l": petrol_eff, "kwh": kwh_eff}

    return catalogue_consumption


def energy_cost(
    model: str,
    assumptions: Assumptions | None = None,
) -> float:
    """
    Total energy cost (NOK) over ``assumptions.horizon_years``.

    Parameters
    ----------
    model:
        Key matching ``CAR_CATALOGUE``.
    assumptions:
        ``Assumptions`` instance; defaults to ``Assumptions()`` if omitted.

    Returns
    -------
    float
        Rounded total energy cost in NOK.
    """
    if assumptions is None:
        assumptions = Assumptions()

    consumption = _effective_consumption(model, assumptions)
    annual_nok = 0.0

    if "petrol_l" in consumption:
        annual_nok += (
            assumptions.annual_km / 100
            * consumption["petrol_l"]
            * assumptions.petrol_nok_per_l
        )
    if "diesel_l" in consumption:
        annual_nok += (
            assumptions.annual_km / 100
            * consumption["diesel_l"]
            * assumptions.diesel_nok_per_l
        )
    if "kwh" in consumption:
        annual_nok += (
            assumptions.annual_km / 100
            * consumption["kwh"]
            * assumptions.electricity_nok_per_kwh
        )

    return round(annual_nok * assumptions.horizon_years)
