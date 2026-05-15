"""Tests for checked-in JSON-backed model data."""

from car_tco.data.catalogue import CAR_CATALOGUE
from car_tco.data.model_assumptions import PRICING_MODEL_PROFILES
from car_tco.data.reference_fleet import build_reference_fleet
from car_tco.data.reliability import (
    RELIABILITY_PROFILE_METADATA,
    RELIABILITY_PROFILES,
    RELIABILITY_YEAR_PROFILES,
)


def test_catalogue_loaded_from_json_shape():
    rav4 = CAR_CATALOGUE["Toyota RAV4 Hybrid"]
    assert rav4["scheduled_maintenance_nok"] == 5500
    assert rav4["consumption"]["petrol_l"] > 4


def test_reference_fleet_loaded_from_json_shape():
    fleet = build_reference_fleet()
    glc = next(car for car in fleet if car["model"] == "Mercedes GLC 300e 4MATIC")
    assert glc["year"] == 2020
    assert glc["url"].startswith("https://www.finn.no/")


def test_reliability_profiles_loaded_from_json_shape():
    audi = RELIABILITY_PROFILES["Audi e-tron"]
    outlander = RELIABILITY_PROFILES["Mitsubishi Outlander PHEV"]
    assert "charging system" in audi.known_failure_modes
    assert len(outlander.sources) == 2
    assert "battery degradation" in outlander.known_failure_modes


def test_reliability_profiles_expose_fillable_metadata():
    metadata = RELIABILITY_PROFILE_METADATA["Mitsubishi Outlander PHEV"]
    rav4_year_profile = RELIABILITY_YEAR_PROFILES["Toyota RAV4 Hybrid"][0]
    assert metadata.status == "draft"
    assert metadata.generated_by == "repo_migration"
    assert rav4_year_profile.metadata.status == "draft"


def test_pricing_profiles_loaded_from_json_shape():
    rav4 = PRICING_MODEL_PROFILES["Toyota RAV4 Hybrid"]
    assert rav4.query == "toyota rav4 hybrid"
    assert ("rav4",) in rav4.required_groups


def test_volvo_xc40_recharge_data_loaded_from_json_shape():
    xc40 = RELIABILITY_PROFILES["Volvo XC40 Recharge"]
    pricing = PRICING_MODEL_PROFILES["Volvo XC40 Recharge"]
    assert len(xc40.sources) == 3
    assert "battery management/charging" in xc40.known_failure_modes
    assert pricing.query == "volvo xc40 recharge"


def test_audi_e_tron_data_loaded_from_json_shape():
    audi = RELIABILITY_PROFILES["Audi e-tron"]
    pricing = PRICING_MODEL_PROFILES["Audi e-tron"]
    assert len(audi.sources) == 3
    assert "high-voltage battery/water ingress" in audi.known_failure_modes
    assert pricing.query == "audi e-tron"
