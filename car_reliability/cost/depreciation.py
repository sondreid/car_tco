"""
Depreciation and capital (opportunity / financing) cost.

Residual value is modelled as:
    factor = residual_base
             + (reliability - 85) * residual_reliability_sensitivity
             - excess_km_at_end / 10 000 * residual_km_penalty_per_10k

Clamped to [residual_floor, residual_ceiling].
"""

from __future__ import annotations

from ..data.catalogue import CAR_CATALOGUE
from ..assumptions import Assumptions


def depreciation_cost(
    model: str,
    price_nok: float,
    km: float,
    reliability: dict[str, float],
    assumptions: Assumptions | None = None,
) -> dict[str, float]:
    """
    Compute resale value, depreciation, and capital cost.

    Parameters
    ----------
    model:
        Key matching ``CAR_CATALOGUE``.
    price_nok:
        Purchase price in NOK.
    km:
        Odometer at purchase (km).
    reliability:
        Reliability breakdown for this car instance.
    assumptions:
        ``Assumptions`` instance; defaults to ``Assumptions()`` if omitted.

    Returns
    -------
    dict with keys:
        resale_nok        – estimated resale price after ownership horizon
        depreciation_nok  – price - resale
        investment_nok    – capital cost on average capital tied up
    """
    if assumptions is None:
        assumptions = Assumptions()

    resid_base = CAR_CATALOGUE[model]["residual_base"]

    km_end = km + assumptions.annual_km * assumptions.horizon_years
    km_excess = max(km_end - 160_000, 0)

    factor = (
        resid_base
        + (reliability["reliability_score"] - 85) * assumptions.residual_reliability_sensitivity
        - reliability["technical_risk_penalty"] * assumptions.residual_technical_risk_penalty_per_point
        - max(75 - reliability["reliability_confidence"], 0)
        * assumptions.residual_low_confidence_penalty_per_point
        - (km_excess / 10_000) * assumptions.residual_km_penalty_per_10k
    )
    factor = max(assumptions.residual_floor, min(assumptions.residual_ceiling, factor))

    resale = round(price_nok * factor)
    depreciation = round(price_nok - resale)
    investment = round(
        (price_nok + resale) / 2 * assumptions.capital_rate * assumptions.horizon_years
    )

    return {
        "resale_nok": resale,
        "depreciation_nok": depreciation,
        "investment_nok": investment,
    }
