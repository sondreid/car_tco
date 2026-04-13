"""
Assumptions — all toggleable model parameters live here.

``Assumptions`` is a plain dataclass; every field has a sensible default that
reproduces the original script's results.  Override individual fields to
explore alternative scenarios:

    base = Assumptions()
    pessimistic = Assumptions(charge_share=0.25, capital_rate=0.06)

PHEV blend computation
----------------------
When ``phev_dynamic_consumption`` is True (default), the Outlander's effective
petrol and electricity consumption are derived from the PHEV parameters
(trip_km, charge_share, ev_range_km, battery_kwh_full).  Set it to False to
use the raw catalogue value instead.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Assumptions:
    # ── Driving pattern ──────────────────────────────────────────────────────
    annual_km: float = 15_000
    """Kilometres driven per year (all models)."""

    horizon_years: int = 3
    """Ownership horizon used for TCO calculation."""

    # ── Energy prices (NOK) ──────────────────────────────────────────────────
    petrol_nok_per_l: float = 23.0
    """Pump price of 95-octane petrol per litre (NOK)."""

    diesel_nok_per_l: float = 22.0
    """Pump price of diesel per litre (NOK)."""

    electricity_nok_per_kwh: float = 1.5
    """Home-charging electricity tariff per kWh (NOK)."""

    # ── Capital cost ─────────────────────────────────────────────────────────
    capital_rate: float = 0.04
    """Annual opportunity cost / financing rate applied to tied-up capital."""

    # ── PHEV-specific (Outlander) ─────────────────────────────────────────────
    phev_dynamic_consumption: bool = True
    """If True, derive PHEV consumption from the parameters below."""

    trip_km: float = 60.0
    """Representative round-trip / daily trip length (km) for PHEV blend."""

    charge_share: float = 0.50
    """
    Fraction of trips that start with a full battery charge.
    0.0 → always runs on petrol.
    1.0 → always starts fully charged.
    """

    ev_range_km: float = 54.0
    """Usable EV range on a full charge (km)."""

    battery_kwh_full: float = 13.8
    """Usable battery capacity (kWh)."""

    outlander_petrol_l_per_100: float = 5.2
    """Petrol consumption when the ICE is running (L/100 km)."""

    # ── Reliability score weights ─────────────────────────────────────────────
    weight_published: float = 0.55
    """Weight of published reliability index in composite score."""

    weight_owner: float = 0.20
    """Weight of owner-reported reliability in composite score."""

    weight_complexity: float = 0.25
    """Weight of inverse mechanical complexity in composite score."""

    reliability_disagreement_penalty: float = 0.15
    """Penalty applied to the gap between published and owner reliability."""

    failure_cost_penalty_per_point: float = 0.9
    """Penalty per failure-cost-risk point."""

    evidence_uncertainty_penalty_per_point: float = 0.6
    """Penalty per evidence-uncertainty point."""

    # Age / mileage penalty toggles
    age_penalty_per_year: float = 1.5
    """Score penalty per year of age beyond a 4-year grace period."""

    mileage_penalty_per_10k: float = 0.8
    """Score penalty per 10 000 km driven beyond 60 000 km."""

    # ── Maintenance ───────────────────────────────────────────────────────────
    maintenance_reliability_sensitivity: float = 1 / 60
    """
    How much maintenance cost scales with reliability shortfall.
    Formula: base_maint * (1 + (100 - rel) * sensitivity) * years
    """

    # ── Residual value ────────────────────────────────────────────────────────
    residual_reliability_sensitivity: float = 0.003
    """
    Residual value adjustment per point of reliability above/below 85.
    """

    residual_km_penalty_per_10k: float = 0.01
    """
    Residual value penalty per 10 000 km beyond 160 000 km at end of
    ownership (purchase km + annual_km * horizon_years).
    """

    residual_floor: float = 0.45
    residual_ceiling: float = 0.85

    def phev_effective_consumption(self) -> tuple[float, float]:
        """
        Return (petrol_l_per_100, kwh_per_100) for the PHEV blend.

        Uses the Outlander-specific PHEV parameters stored on this instance.
        """
        trip_km = self.trip_km
        km_ev = self.charge_share * min(self.ev_range_km, trip_km)
        km_petrol = trip_km - km_ev
        effective_kwh = self.charge_share * self.battery_kwh_full / trip_km * 100
        effective_petrol = km_petrol / trip_km * self.outlander_petrol_l_per_100
        return effective_petrol, effective_kwh
