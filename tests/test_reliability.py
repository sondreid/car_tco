"""Tests for the reliability scoring module."""

from car_reliability.assumptions import Assumptions
from car_reliability.data.reliability import RELIABILITY_PROFILES
from car_reliability.scoring.reliability import reliability_breakdown, reliability_score


def test_score_in_bounds():
    score = reliability_score("Toyota RAV4 Hybrid", 2019, 120_000)
    assert 60 <= score <= 98


def test_rav4_baseline_close_to_original():
    """Baseline stays in a sensible upper range after methodology changes."""
    score = reliability_score("Toyota RAV4 Hybrid", 2019, 120_000)
    assert 80 <= score <= 95


def test_age_penalty_applied():
    old = reliability_score("Toyota RAV4 Hybrid", 2010, 60_000)
    new = reliability_score("Toyota RAV4 Hybrid", 2022, 60_000)
    assert old < new


def test_mileage_penalty_applied():
    low = reliability_score("Toyota RAV4 Hybrid", 2022, 50_000)
    high = reliability_score("Toyota RAV4 Hybrid", 2022, 200_000)
    assert high < low


def test_custom_weights():
    a = Assumptions(
        weight_evidence=1.0,
        weight_technical_risk=0.0,
        weight_confidence=0.0,
        evidence_survey_weight=1.0,
        evidence_owner_weight=0.0,
    )
    score = reliability_score("Toyota RAV4 Hybrid", 2022, 50_000, assumptions=a)
    assert 90 <= score <= 98


def test_passat_scores_below_rav4():
    rav4 = reliability_score("Toyota RAV4 Hybrid", 2020, 80_000)
    passat = reliability_score("Volkswagen Passat GTE", 2020, 80_000)
    assert passat < rav4


def test_outlander_has_multiple_sources():
    profile = RELIABILITY_PROFILES["Mitsubishi Outlander PHEV"]
    assert len(profile.sources) >= 2


def test_failure_cost_penalty_hurts_passat_more_than_rav4():
    rav4 = reliability_breakdown("Toyota RAV4 Hybrid", 2020, 80_000)
    passat = reliability_breakdown("Volkswagen Passat GTE", 2020, 80_000)
    assert passat["failure_cost_penalty"] > rav4["failure_cost_penalty"]


def test_confidence_penalty_applies_to_outlander():
    outlander = reliability_breakdown("Mitsubishi Outlander PHEV", 2020, 60_000)
    assert outlander["reliability_confidence"] < 75


def test_removing_risk_penalties_improves_score():
    penalized = reliability_score("Volkswagen Passat GTE", 2020, 90_000)
    unpenalized = reliability_score(
        "Volkswagen Passat GTE",
        2020,
        90_000,
        assumptions=Assumptions(
            failure_cost_penalty_per_point=0.0,
            disagreement_penalty_per_point=0.0,
            single_source_penalty=0.0,
        ),
    )
    assert unpenalized > penalized


def test_single_source_penalty_applies_to_avensis():
    avensis = reliability_breakdown("Toyota Avensis", 2012, 182_000)
    assert avensis["source_count_penalty"] > 0


def test_score_floor():
    # Very old, very high km car should hit the floor
    score = reliability_score("Skoda Superb 2.0 TDI 4x4", 2005, 400_000)
    assert score == 60.0
