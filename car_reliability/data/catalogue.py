"""
Per-model static data catalogue.

Each entry under CAR_CATALOGUE contains:
  scheduled_maintenance_nok – estimated annual scheduled maintenance (NOK)
  residual_base          – fraction of purchase price retained after 3 yrs / ~160 k km
  consumption            – dict with ONE or MORE of:
                             petrol_l  – L/100 km petrol consumption
                             diesel_l  – L/100 km diesel consumption
                             kwh       – kWh/100 km electricity consumption

Consumption values for PHEVs / hybrids may be computed dynamically by the
assumptions module; the values stored here are the *fallback* figures used when
dynamic computation is disabled.
"""

from __future__ import annotations
from typing import Any

CAR_CATALOGUE: dict[str, dict[str, Any]] = {
    "Mercedes EQC": {
        "scheduled_maintenance_nok": 4000,
        "residual_base": 0.64,
        "consumption": {"kwh": 24.0},
    },
    "Mazda CX-5 diesel AWD": {
        "scheduled_maintenance_nok": 7000,
        "residual_base": 0.60,
        "consumption": {"diesel_l": 5.8},
    },
    "Peugeot 508 SW 2.0 BlueHDi": {
        "scheduled_maintenance_nok": 6500,
        "residual_base": 0.56,
        "consumption": {"diesel_l": 5.0},
    },
    "Skoda Kodiaq 2.0 TDI 4x4": {
        "scheduled_maintenance_nok": 7500,
        "residual_base": 0.65,
        "consumption": {"diesel_l": 6.6},
    },
    "Tesla Model Y": {
        "scheduled_maintenance_nok": 3000,
        "residual_base": 0.69,
        "consumption": {"kwh": 18.0},
    },
    "Toyota Avensis": {
        "scheduled_maintenance_nok": 7500,
        "residual_base": 0.55,
        "consumption": {"petrol_l": 6.8},
    },
    "Toyota RAV4 Hybrid": {
        "scheduled_maintenance_nok": 5500,
        "residual_base": 0.78,
        # Default: spec sheet L/100 km converted from 47.9 US mpg
        "consumption": {"petrol_l": 4.9105},
    },
    "Mitsubishi Outlander PHEV": {
        "scheduled_maintenance_nok": 6000,
        "residual_base": 0.72,
        # Fallback (pure ICE mode): override by phev_assumption in Assumptions
        "consumption": {"petrol_l": 5.2},
    },
    "Volkswagen Passat GTE": {
        "scheduled_maintenance_nok": 6500,
        "residual_base": 0.64,
        "consumption": {"petrol_l": 5.6, "kwh": 12.5},
    },
    "Skoda Superb 2.0 TDI 4x4": {
        "scheduled_maintenance_nok": 7000,
        "residual_base": 0.68,
        "consumption": {"diesel_l": 6.3},
    },
}
