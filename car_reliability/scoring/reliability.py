"""
Composite reliability score (0–100) for a specific car instance.

The score is a weighted blend of:
  - Published/source-backed reliability rating
  - Owner-reported reliability
  - Inverse mechanical complexity (100 - complexity)

Penalised for:
  - Disagreement between published and owner evidence
  - Failure-cost asymmetry
  - Evidence uncertainty / mixed signals
  - Age beyond a 4-year grace period
  - High mileage beyond 60 000 km at purchase

All weights and penalty rates are read from the ``Assumptions`` object so
they can be toggled freely without touching this module.
"""

from __future__ import annotations

from ..assumptions import Assumptions
from ..data.reliability import RELIABILITY_PROFILES

_SCORE_FLOOR = 60.0
_SCORE_CEILING = 98.0


def reliability_breakdown(
    model: str,
    year: int,
    km: float,
    assumptions: Assumptions | None = None,
    reference_year: int = 2026,
) -> dict[str, float]:
    """
    Return the reliability score components for a specific car instance.
    """
    if assumptions is None:
        assumptions = Assumptions()

    profile = RELIABILITY_PROFILES[model]
    base = (
        assumptions.weight_published * profile.published_reliability
        + assumptions.weight_owner * profile.owner_reliability
        + assumptions.weight_complexity * (100 - profile.complexity)
    )

    disagreement_penalty = (
        abs(profile.published_reliability - profile.owner_reliability)
        * assumptions.reliability_disagreement_penalty
    )
    failure_cost_penalty = (
        profile.failure_cost_risk * assumptions.failure_cost_penalty_per_point
    )
    uncertainty_penalty = (
        profile.evidence_uncertainty * assumptions.evidence_uncertainty_penalty_per_point
    )

    age_years = reference_year - int(year)
    age_penalty = max(age_years - 4, 0) * assumptions.age_penalty_per_year

    km_excess = max(float(km) - 60_000, 0)
    km_penalty = (km_excess / 10_000) * assumptions.mileage_penalty_per_10k

    raw_score = (
        base
        - disagreement_penalty
        - failure_cost_penalty
        - uncertainty_penalty
        - age_penalty
        - km_penalty
    )
    score = round(max(_SCORE_FLOOR, min(_SCORE_CEILING, raw_score)), 1)

    return {
        "base": round(base, 2),
        "disagreement_penalty": round(disagreement_penalty, 2),
        "failure_cost_penalty": round(failure_cost_penalty, 2),
        "uncertainty_penalty": round(uncertainty_penalty, 2),
        "age_penalty": round(age_penalty, 2),
        "km_penalty": round(km_penalty, 2),
        "raw_score": round(raw_score, 2),
        "score": score,
    }


def reliability_score(
    model: str,
    year: int,
    km: float,
    assumptions: Assumptions | None = None,
    reference_year: int = 2026,
) -> float:
    """
    Compute and return the composite reliability score for *model* given its
    registration *year* and current odometer *km*.

    Parameters
    ----------
    model:
        Key matching ``CAR_CATALOGUE``.
    year:
        Registration / model year.
    km:
        Current odometer reading (km).
    assumptions:
        ``Assumptions`` instance; defaults to ``Assumptions()`` if omitted.
    reference_year:
        The year used to compute vehicle age (defaults to 2026).

    Returns
    -------
    float
        Reliability score clamped to [60, 98].
    """
    return reliability_breakdown(
        model=model,
        year=year,
        km=km,
        assumptions=assumptions,
        reference_year=reference_year,
    )["score"]
