"""
Estimated maintenance cost over the ownership horizon.
"""

from __future__ import annotations

from ..data.catalogue import CAR_CATALOGUE
from ..assumptions import Assumptions


def maintenance_cost(
    model: str,
    reliability: dict[str, float],
    assumptions: Assumptions | None = None,
) -> dict[str, float]:
    """
    Total maintenance cost (NOK) over ``assumptions.horizon_years``.

    Parameters
    ----------
    model:
        Key matching ``CAR_CATALOGUE``.
    reliability:
        Reliability breakdown for this specific car instance.
    assumptions:
        ``Assumptions`` instance; defaults to ``Assumptions()`` if omitted.

    Returns
    -------
    dict with keys:
        scheduled_maintenance_nok
        failure_risk_cost_nok
        maintenance_nok
    """
    if assumptions is None:
        assumptions = Assumptions()

    scheduled = (
        CAR_CATALOGUE[model]["scheduled_maintenance_nok"] * assumptions.horizon_years
    )
    technical_penalty = reliability["technical_risk_penalty"]
    score_shortfall = max(85 - reliability["reliability_score"], 0)
    low_confidence = max(75 - reliability["reliability_confidence"], 0)
    failure_risk_cost = round(
        assumptions.horizon_years
        * (
            technical_penalty * assumptions.failure_risk_cost_per_point
            + score_shortfall * assumptions.reliability_shortfall_cost_per_point
            + low_confidence * assumptions.low_confidence_cost_per_point
        )
    )
    scheduled = round(scheduled)
    return {
        "scheduled_maintenance_nok": scheduled,
        "failure_risk_cost_nok": failure_risk_cost,
        "maintenance_nok": scheduled + failure_risk_cost,
    }
