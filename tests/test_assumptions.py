"""Tests for assumption toggles and PHEV blend computation."""

from car_reliability.assumptions import Assumptions


def test_default_phev_blend():
    a = Assumptions()
    petrol, kwh = a.phev_effective_consumption()
    # 50% charge share, 54 km range, 60 km trip → 27 km EV, 33 km ICE
    # petrol eff ≈ 33/60 * 5.2 ≈ 2.86
    assert abs(petrol - (33 / 60 * 5.2)) < 0.01
    # kwh eff ≈ 0.5 * 13.8 / 60 * 100 ≈ 11.5
    assert abs(kwh - (0.5 * 13.8 / 60 * 100)) < 0.01


def test_full_charge_share():
    a = Assumptions(charge_share=1.0, trip_km=40, ev_range_km=54)
    petrol, kwh = a.phev_effective_consumption()
    # All EV, petrol should be 0
    assert abs(petrol) < 0.001


def test_zero_charge_share():
    a = Assumptions(charge_share=0.0)
    petrol, kwh = a.phev_effective_consumption()
    # All petrol
    assert abs(petrol - a.outlander_petrol_l_per_100) < 0.001
    assert abs(kwh) < 0.001


def test_assumptions_immutable_between_instances():
    a1 = Assumptions(annual_km=10_000)
    a2 = Assumptions()
    assert a1.annual_km == 10_000
    assert a2.annual_km == 15_000
