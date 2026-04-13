"""
Estimated maintenance cost over the ownership horizon.

Higher reliability → lower maintenance spend.
The sensitivity of maintenance cost to reliability shortfall is tunable via
``Assumptions.maintenance_reliability_sensitivity``.
"""

from __future__ import annotations

from ..data.catalogue import CAR_CATALOGUE
from ..assumptions import Assumptions


def maintenance_cost(
    model: str,
    reliability_score: float,
    assumptions: Assumptions | None = None,
) -> float:
    """
    Total maintenance cost (NOK) over ``assumptions.horizon_years``.

    Parameters
    ----------
    model:
        Key matching ``CAR_CATALOGUE``.
    reliability_score:
        Composite reliability score for this specific car instance (0–100).
    assumptions:
        ``Assumptions`` instance; defaults to ``Assumptions()`` if omitted.

    Returns
    -------
    float
        Rounded maintenance cost in NOK.
    """
    if assumptions is None:
        assumptions = Assumptions()

    base = CAR_CATALOGUE[model]["base_maintenance_nok"]
    shortfall = 100 - reliability_score
    multiplier = 1 + shortfall * assumptions.maintenance_reliability_sensitivity
    return round(base * multiplier * assumptions.horizon_years)
