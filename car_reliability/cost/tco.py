"""
TCO pipeline — assembles one complete result row for a single car.
"""

from __future__ import annotations

from ..assumptions import Assumptions
from ..scoring.reliability import reliability_score
from .energy import energy_cost
from .maintenance import maintenance_cost
from .depreciation import depreciation_cost


def compute_tco(
    car: dict,
    assumptions: Assumptions | None = None,
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
    km = float(car["km"])
    known_repairs = round(float(car.get("known_repairs_nok", 0)))

    rel = reliability_score(model, year, km, assumptions)
    maint = maintenance_cost(model, rel, assumptions) + known_repairs
    energy = energy_cost(model, assumptions)
    dep = depreciation_cost(model, price, km, rel, assumptions)

    total = (
        dep["depreciation_nok"]
        + dep["investment_nok"]
        + energy
        + maint
    )

    return {
        "model": model,
        "reference_name": car.get("name", model),
        "reference_desc": car.get("description", ""),
        "reference_price_nok": round(price),
        "price_source": car.get("price_source", "manual"),
        "price_match_count": int(car.get("price_match_count", 0)),
        "price_fallback_used": bool(car.get("price_fallback_used", False)),
        "price_note": car.get("price_note", ""),
        "reference_year": year,
        "reference_km": round(km),
        "reliability_score": rel,
        "known_repairs_nok": known_repairs,
        "maintenance_nok": maint,
        "energy_nok": energy,
        "depreciation_nok": dep["depreciation_nok"],
        "investment_cost_nok": dep["investment_nok"],
        "resale_nok": dep["resale_nok"],
        "total_cost_nok": total,
        "cost_per_month_nok": round(total / (assumptions.horizon_years * 12)),
        "url": car.get("url", ""),
    }
