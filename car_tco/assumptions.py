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
from dataclasses import dataclass


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
    weight_evidence: float = 0.55
    """Weight of evidence score in composite reliability."""

    weight_technical_risk: float = 0.30
    """Weight of technical-risk score in composite reliability."""

    weight_confidence: float = 0.15
    """Weight of evidence confidence score in composite reliability."""

    evidence_survey_weight: float = 0.60
    """Survey/source-backed weight inside evidence score."""

    evidence_owner_weight: float = 0.40
    """Owner-reported weight inside evidence score."""

    complexity_penalty_per_point: float = 1.6
    """Penalty per complexity-risk point when building technical-risk score."""

    failure_cost_penalty_per_point: float = 2.2
    """Penalty per failure-cost-risk point when building technical-risk score."""

    disagreement_penalty_per_point: float = 0.25
    """Confidence penalty per point of disagreement between survey and owner evidence."""

    single_source_penalty: float = 8.0
    """Confidence penalty when only one external source is available."""

    # Age / mileage penalty toggles
    age_penalty_per_year: float = 1.5
    """Score penalty per year of age beyond a 4-year grace period."""

    mileage_penalty_per_10k: float = 0.8
    """Score penalty per 10 000 km driven beyond 60 000 km."""

    # ── Maintenance ───────────────────────────────────────────────────────────
    failure_risk_cost_per_point: float = 220.0
    """Annual failure-risk cost per technical-risk penalty point."""

    reliability_shortfall_cost_per_point: float = 45.0
    """Annual failure-risk cost per reliability point below 85."""

    low_confidence_cost_per_point: float = 35.0
    """Annual failure-risk cost per confidence point below 75."""

    # ── Residual value ────────────────────────────────────────────────────────
    reference_year: int | None = None
    """Calendar year used as 'now' for age computation; None uses system clock."""

    residual_reliability_sensitivity: float = 0.002
    """Residual adjustment per point of reliability above/below 85."""

    residual_technical_risk_penalty_per_point: float = 0.0025
    """Residual penalty per point of technical-risk penalty."""

    residual_low_confidence_penalty_per_point: float = 0.0015
    """Residual penalty per point of confidence below 75."""

    residual_adj_cap: float = 0.10
    """Symmetric cap on net reliability/risk/confidence adjustment."""

    age_decay_year_1: float = 0.15
    age_decay_years_2_3: float = 0.10
    age_decay_years_4_6: float = 0.07
    age_decay_year_7_plus: float = 0.05

    km_penalty_per_10k_band_1: float = 0.005
    km_penalty_per_10k_band_2: float = 0.010
    km_penalty_per_10k_band_3: float = 0.015
    km_penalty_per_10k_band_4: float = 0.020

    residual_floor: float = 0.10
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
