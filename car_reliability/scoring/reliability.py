"""
Composite reliability score (0–100) for a specific car instance.

The score is a weighted blend of:
  - Evidence score (survey + owner-reported reliability)
  - Technical-risk score
  - Evidence confidence score

Penalised for:
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
    evidence_score = (
        assumptions.evidence_survey_weight * profile.survey_score
        + assumptions.evidence_owner_weight * profile.owner_score
    )
    complexity_penalty = profile.complexity_risk * assumptions.complexity_penalty_per_point
    failure_cost_penalty = (
        profile.failure_cost_risk * assumptions.failure_cost_penalty_per_point
    )
    technical_risk_penalty = complexity_penalty + failure_cost_penalty
    technical_risk_score = max(0.0, 100.0 - technical_risk_penalty)

    disagreement_penalty = (
        abs(profile.survey_score - profile.owner_score)
        * assumptions.disagreement_penalty_per_point
    )
    source_count_penalty = assumptions.single_source_penalty if len(profile.sources) < 2 else 0.0
    confidence_score = max(
        0.0,
        min(100.0, profile.evidence_confidence - disagreement_penalty - source_count_penalty),
    )

    age_years = reference_year - int(year)
    age_penalty = max(age_years - 4, 0) * assumptions.age_penalty_per_year

    km_excess = max(float(km) - 60_000, 0)
    km_penalty = (km_excess / 10_000) * assumptions.mileage_penalty_per_10k

    raw_score = (
        assumptions.weight_evidence * evidence_score
        + assumptions.weight_technical_risk * technical_risk_score
        + assumptions.weight_confidence * confidence_score
        - age_penalty
        - km_penalty
    )
    score = round(max(_SCORE_FLOOR, min(_SCORE_CEILING, raw_score)), 1)

    return {
        "reliability_evidence_score": round(evidence_score, 2),
        "technical_robustness": round(technical_risk_score, 2),
        "reliability_confidence": round(confidence_score, 2),
        "disagreement_penalty": round(disagreement_penalty, 2),
        "source_count_penalty": round(source_count_penalty, 2),
        "complexity_penalty": round(complexity_penalty, 2),
        "failure_cost_penalty": round(failure_cost_penalty, 2),
        "technical_risk_penalty": round(technical_risk_penalty, 2),
        "reliability_age_penalty": round(age_penalty, 2),
        "reliability_km_penalty": round(km_penalty, 2),
        "raw_score": round(raw_score, 2),
        "reliability_score": score,
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
    )["reliability_score"]
