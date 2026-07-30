"""Validate car_tco/data/models.json by loading it through the package."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from car_tco.data.models import (
    CAR_CATALOGUE,
    PRICING_MODEL_PROFILES,
    RELIABILITY_PROFILES,
    RELIABILITY_YEAR_PROFILES,
)

year_count = sum(len(observations) for observations in RELIABILITY_YEAR_PROFILES.values())

print(f"Validated {len(CAR_CATALOGUE)} models")
print(f"Validated {len(PRICING_MODEL_PROFILES)} pricing profiles")
print(f"Validated {len(RELIABILITY_PROFILES)} reliability profiles")
print(f"Validated {year_count} year-specific reliability profiles")
