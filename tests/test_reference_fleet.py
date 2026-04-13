"""Tests for reference fleet helpers."""

from car_reliability.data.reference_fleet import build_car


def test_build_car_uses_default_reference():
    car = build_car("Toyota RAV4 Hybrid")
    assert car["model"] == "Toyota RAV4 Hybrid"
    assert car["price_nok"] == 280_000
    assert car["year"] == 2019


def test_build_car_applies_overrides():
    car = build_car("Toyota RAV4 Hybrid", price_nok=255_000, km=95_000)
    assert car["model"] == "Toyota RAV4 Hybrid"
    assert car["price_nok"] == 255_000
    assert car["km"] == 95_000
    assert car["year"] == 2019


def test_build_car_requires_core_fields_for_unknown_model():
    try:
        build_car("Unknown Model")
    except KeyError:
        return
    raise AssertionError("Expected KeyError for unknown model without overrides")
