"""
Depreciation and purchase opportunity cost.

Two-layer residual model:
    base(age, km)  – continuous age and banded-km decay from new
    adj(reliability, risk, confidence) – bounded multiplier (±adj_cap)
    resale = price_nok * (base_end * adj) / base_now
"""

from __future__ import annotations

from datetime import datetime

from ..assumptions import Assumptions


def _age_curve(age_years: float, a: Assumptions) -> float:
    """Piecewise exponential age decay, fraction of new."""
    remaining = 1.0
    prev = 0.0
    for upper, rate in (
        (1.0, a.age_decay_year_1),
        (3.0, a.age_decay_years_2_3),
        (6.0, a.age_decay_years_4_6),
    ):
        span = max(0.0, min(age_years, upper) - prev)
        if span > 0:
            remaining *= (1.0 - rate) ** span
        prev = upper
    if age_years > prev:
        remaining *= (1.0 - a.age_decay_year_7_plus) ** (age_years - prev)
    return remaining


def _km_curve(km: float, a: Assumptions) -> float:
    """Banded km decay, fraction of new."""
    remaining = 1.0
    prev = 0.0
    for upper, per_10k in (
        (60_000.0, a.km_penalty_per_10k_band_1),
        (120_000.0, a.km_penalty_per_10k_band_2),
        (180_000.0, a.km_penalty_per_10k_band_3),
    ):
        span = max(0.0, min(km, upper) - prev)
        remaining -= (span / 10_000.0) * per_10k
        prev = upper
    if km > prev:
        remaining -= ((km - prev) / 10_000.0) * a.km_penalty_per_10k_band_4
    return max(remaining, 0.0)


def depreciation_cost(
    model: str,
    price_nok: float,
    km: float,
    reliability: dict[str, float],
    assumptions: Assumptions | None = None,
    model_year: int | None = None,
    resale_override_nok: float | None = None,
) -> dict[str, float]:
    """Compute resale value, depreciation, and purchase opportunity cost."""
    if assumptions is None:
        assumptions = Assumptions()

    ref_year = assumptions.reference_year or datetime.now().year
    age_now = max(float(ref_year - int(model_year)), 0.0) if model_year else 0.0
    age_end = age_now + float(assumptions.horizon_years)
    km_end = float(km) + assumptions.annual_km * assumptions.horizon_years

    base_now = _age_curve(age_now, assumptions) * _km_curve(float(km), assumptions)
    base_end = _age_curve(age_end, assumptions) * _km_curve(km_end, assumptions)

    adj_net = (
        (reliability["reliability_score"] - 85)
        * assumptions.residual_reliability_sensitivity
        - reliability["technical_risk_penalty"]
        * assumptions.residual_technical_risk_penalty_per_point
        - max(75 - reliability["reliability_confidence"], 0)
        * assumptions.residual_low_confidence_penalty_per_point
    )
    cap = assumptions.residual_adj_cap
    adj = 1.0 + max(-cap, min(cap, adj_net))

    end_fraction_of_new = max(assumptions.residual_floor, base_end * adj)
    factor = (
        end_fraction_of_new / base_now
        if base_now > 0
        else assumptions.residual_floor
    )
    factor = min(factor, assumptions.residual_ceiling)

    resale = (
        round(float(resale_override_nok))
        if resale_override_nok is not None
        else round(price_nok * factor)
    )
    depreciation = round(price_nok - resale)
    opportunity = round(
        (price_nok + resale) / 2 * assumptions.capital_rate * assumptions.horizon_years
    )

    return {
        "resale_nok": resale,
        "depreciation_nok": depreciation,
        "opportunity_nok": opportunity,
    }
