"""Tests for checked-in JSON-backed model data."""

from car_reliability.data.catalogue import CAR_CATALOGUE
from car_reliability.data.model_assumptions import PRICING_MODEL_PROFILES
from car_reliability.data.reference_fleet import build_reference_fleet
from car_reliability.data.reliability import RELIABILITY_PROFILES


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
    outlander = RELIABILITY_PROFILES["Mitsubishi Outlander PHEV"]
    assert len(outlander.sources) == 2
    assert "battery degradation" in outlander.known_failure_modes


def test_pricing_profiles_loaded_from_json_shape():
    rav4 = PRICING_MODEL_PROFILES["Toyota RAV4 Hybrid"]
    assert rav4.query == "toyota rav4 hybrid"
    assert ("rav4",) in rav4.required_groups
