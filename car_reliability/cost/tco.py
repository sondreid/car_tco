"""
TCO pipeline — assembles one complete result row for a single car.
"""

from __future__ import annotations

from ..assumptions import Assumptions
from ..scoring.reliability import reliability_breakdown
from .energy import energy_cost
from .maintenance import maintenance_cost
from .depreciation import depreciation_cost


def compute_tco(
    car: dict,
    assumptions: Assumptions | None = None,
    reliability: dict | None = None,
) -> dict:
    """
    Compute the full TCO breakdown for a single car dict.

    Parameters
    ----------
    car:
        Dict with at least: model, price_nok, year, km.
        Optional keys: name, description, url.
    assumptions:
        ``Assumptions`` instance; defaults to ``Assumptions()`` if omitted.

    Returns
    -------
    dict
        Flat result row ready to append to a DataFrame.
    """
    if assumptions is None:
        assumptions = Assumptions()

    model = car["model"]
    price = float(car["price_nok"])
    year = int(car["year"])
    model_year = int(car.get("model_year", year))
    km = float(car["km"])
    known_repairs = round(float(car.get("known_repairs_nok", 0)))
    existing_car = bool(car.get("existing_car") or car.get("EXISTING_CAR"))
    current_resale_value = round(float(car.get("current_resale_value_nok", 0)))
    foregone_resale = current_resale_value if existing_car else 0

    rel = reliability or reliability_breakdown(
        model,
        year,
        km,
        model_year=model_year,
        assumptions=assumptions,
    )
    maint = maintenance_cost(
        model,
        rel,
        assumptions,
        scheduled_maintenance_override_nok=car.get("scheduled_maintenance_nok_override"),
    )
    energy = energy_cost(model, assumptions)
    dep = depreciation_cost(
        model,
        price,
        km,
        rel,
        assumptions,
        residual_base_override=car.get("residual_base_override"),
        resale_override_nok=car.get("resale_nok_override"),
    )
    maintenance_total = maint["maintenance_nok"] + known_repairs
    foregone_resale_opportunity = round(
        foregone_resale * assumptions.capital_rate * assumptions.horizon_years
    )
    known_repairs_opportunity = round(
        known_repairs * assumptions.capital_rate * assumptions.horizon_years
    )
    opportunity_total = (
        dep["opportunity_nok"] + foregone_resale_opportunity + known_repairs_opportunity
    )

    total = (
        dep["depreciation_nok"]
        + opportunity_total
        + energy
        + maintenance_total
        + foregone_resale
    )

    return {
        "model": model,
        "reference_name": car.get("name", model),
        "reference_desc": car.get("description", ""),
        "reference_price_nok": round(price),
        "existing_car": existing_car,
        "foregone_resale_value_nok": foregone_resale,
        "price_source": car.get("price_source", "manual"),
        "price_match_count": int(car.get("price_match_count", 0)),
        "price_fallback_used": bool(car.get("price_fallback_used", False)),
        "price_note": car.get("price_note", ""),
        "reference_year": year,
        "reference_model_year": model_year,
        "reference_km": round(km),
        **rel,
        "known_repairs_nok": known_repairs,
        "scheduled_maintenance_nok": maint["scheduled_maintenance_nok"],
        "failure_risk_cost_nok": maint["failure_risk_cost_nok"],
        "maintenance_nok": maintenance_total,
        "energy_nok": energy,
        "depreciation_nok": dep["depreciation_nok"],
        "opportunity_cost_nok": opportunity_total,
        "resale_nok": dep["resale_nok"],
        "total_cost_nok": total,
        "cost_per_month_nok": round(total / (assumptions.horizon_years * 12)),
        "url": car.get("url", ""),
    }
