"""Integration-level TCO tests."""

from car_reliability.assumptions import Assumptions
from car_reliability.cost.tco import compute_tco
from car_reliability.pipeline import run
from car_reliability.pricing import FinnPriceEstimator, PriceEstimatorConfig


_RAV4 = {
    "model": "Toyota RAV4 Hybrid",
    "name": "RAV4 test",
    "description": "",
    "price_nok": 300_000,
    "year": 2020,
    "model_year": 2020,
    "km": 120_000,
    "url": "",
}


def test_tco_keys():
    result = compute_tco(_RAV4)
    expected_keys = {
        "model", "reliability_score", "maintenance_nok", "energy_nok",
        "depreciation_nok", "investment_cost_nok", "resale_nok",
        "total_cost_nok", "cost_per_month_nok", "scheduled_maintenance_nok",
        "failure_risk_cost_nok", "reliability_evidence_score",
        "technical_robustness", "reliability_confidence",
    }
    assert expected_keys.issubset(result.keys())


def test_total_equals_components():
    r = compute_tco(_RAV4)
    expected_total = (
        r["depreciation_nok"]
        + r["investment_cost_nok"]
        + r["energy_nok"]
        + r["maintenance_nok"]
    )
    assert r["total_cost_nok"] == expected_total


def test_higher_price_increases_total():
    cheap = compute_tco({**_RAV4, "price_nok": 200_000})
    expensive = compute_tco({**_RAV4, "price_nok": 350_000})
    assert expensive["total_cost_nok"] > cheap["total_cost_nok"]


def test_price_override_in_pipeline(tmp_path):
    df = run(
        price_overrides={"Toyota RAV4 Hybrid": 200_000},
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[df["model"] == "Toyota RAV4 Hybrid"].iloc[0]
    assert rav4_row["reference_price_nok"] == 200_000


def test_pipeline_returns_sorted(tmp_path):
    df = run(output_dir=tmp_path, verbose=False)
    costs = df["total_cost_nok"].tolist()
    assert costs == sorted(costs)


def test_pipeline_writes_csvs(tmp_path):
    run(output_dir=tmp_path, output_prefix="test", verbose=False)
    assert (tmp_path / "test_full.csv").exists()
    assert (tmp_path / "test_summary.csv").exists()


def test_no_phev_blend_uses_catalogue():
    """With phev_dynamic_consumption=False, Outlander uses raw catalogue value."""
    a_blend = Assumptions(phev_dynamic_consumption=True)
    a_raw = Assumptions(phev_dynamic_consumption=False)
    outlander = {
        "model": "Mitsubishi Outlander PHEV",
        "price_nok": 220_000, "year": 2020, "km": 60_000,
    }
    e_blend = compute_tco(outlander, a_blend)["energy_nok"]
    e_raw = compute_tco(outlander, a_raw)["energy_nok"]
    # Raw (ICE-only) should be more expensive than blended
    assert e_raw > e_blend


def test_scraped_price_in_pipeline(tmp_path):
    class StubEstimator(FinnPriceEstimator):
        def estimate_price(self, car: dict):
            from car_reliability.pricing.finn import FinnPriceEstimate

            if car["model"] == "Toyota RAV4 Hybrid":
                return FinnPriceEstimate(255_000, "finn_typical", 3, 3, False, "stub")
            return FinnPriceEstimate(int(car["price_nok"]), "manual", 0, 0, True, "stub")

    df = run(
        price_estimation=True,
        price_estimator=StubEstimator(config=PriceEstimatorConfig()),
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[df["model"] == "Toyota RAV4 Hybrid"].iloc[0]
    assert rav4_row["reference_price_nok"] == 255_000
    assert rav4_row["price_source"] == "finn_typical"


def test_price_override_is_ignored_when_scraping(tmp_path):
    class StubEstimator(FinnPriceEstimator):
        def estimate_price(self, car: dict):
            from car_reliability.pricing.finn import FinnPriceEstimate

            if car["model"] == "Toyota RAV4 Hybrid":
                return FinnPriceEstimate(255_000, "finn_typical", 3, 3, False, "stub")
            return FinnPriceEstimate(int(car["price_nok"]), "manual", 0, 0, True, "stub")

    df = run(
        price_estimation=True,
        price_estimator=StubEstimator(config=PriceEstimatorConfig()),
        price_overrides={"Toyota RAV4 Hybrid": 200_000},
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[df["model"] == "Toyota RAV4 Hybrid"].iloc[0]
    assert rav4_row["reference_price_nok"] == 255_000
    assert rav4_row["price_source"] == "finn_typical"


def test_cached_scraped_price_in_pipeline(tmp_path):
    cache_file = tmp_path / "finn_price_cache.json"
    cache_file.write_text(
        """{
  "entries": {
    "Toyota RAV4 Hybrid::2018::120000": {
      "model": "Toyota RAV4 Hybrid",
      "cache_key": "Toyota RAV4 Hybrid::2018::120000",
      "estimated_price_nok": 250000,
      "price_source": "finn_typical",
      "match_count": 4,
      "comparable_count": 4,
      "price_note": "cached",
      "reference_year": 2018,
      "reference_model_year": 2018,
      "reference_km": 120000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Toyota RAV4 Hybrid::2020::120000": {
      "model": "Toyota RAV4 Hybrid",
      "cache_key": "Toyota RAV4 Hybrid::2020::120000",
      "estimated_price_nok": 250000,
      "price_source": "finn_typical",
      "match_count": 4,
      "comparable_count": 4,
      "price_note": "cached",
      "reference_year": 2020,
      "reference_model_year": 2020,
      "reference_km": 120000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Toyota Avensis": {
      "model": "Toyota Avensis",
      "estimated_price_nok": 0,
      "price_source": "existing_car",
      "match_count": 0,
      "comparable_count": 0,
      "price_note": "excluded",
      "reference_year": 2012,
      "reference_km": 182000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Mitsubishi Outlander PHEV": {
      "model": "Mitsubishi Outlander PHEV",
      "estimated_price_nok": 220000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2020,
      "reference_km": 60000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Volkswagen Passat GTE": {
      "model": "Volkswagen Passat GTE",
      "estimated_price_nok": 200000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2020,
      "reference_km": 90000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Skoda Kodiaq 2.0 TDI 4x4": {
      "model": "Skoda Kodiaq 2.0 TDI 4x4",
      "estimated_price_nok": 269000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2018,
      "reference_km": 132700,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Mazda CX-5 diesel AWD": {
      "model": "Mazda CX-5 diesel AWD",
      "estimated_price_nok": 179532,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2016,
      "reference_km": 112200,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Peugeot 508 SW 2.0 BlueHDi": {
      "model": "Peugeot 508 SW 2.0 BlueHDi",
      "estimated_price_nok": 139532,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2015,
      "reference_km": 132500,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Tesla Model Y": {
      "model": "Tesla Model Y",
      "estimated_price_nok": 264532,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2021,
      "reference_km": 68901,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Mercedes EQC": {
      "model": "Mercedes EQC",
      "estimated_price_nok": 260000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2020,
      "reference_km": 126000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Skoda Superb 2.0 TDI 4x4": {
      "model": "Skoda Superb 2.0 TDI 4x4",
      "estimated_price_nok": 180000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2018,
      "reference_km": 140000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    }
  }
}"""
    )
    df = run(
        price_estimation=True,
        use_cached_scraped_prices=True,
        price_cache_file=cache_file,
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[df["model"] == "Toyota RAV4 Hybrid"].iloc[0]
    assert rav4_row["reference_price_nok"] == 250_000
    assert rav4_row["price_source"] == "finn_cached"


def test_price_override_is_ignored_with_cached_scraped_prices(tmp_path):
    cache_file = tmp_path / "finn_price_cache.json"
    cache_file.write_text(
        """{
  "entries": {
    "Toyota RAV4 Hybrid::2018::120000": {
      "model": "Toyota RAV4 Hybrid",
      "cache_key": "Toyota RAV4 Hybrid::2018::120000",
      "estimated_price_nok": 250000,
      "price_source": "finn_typical",
      "match_count": 4,
      "comparable_count": 4,
      "price_note": "cached",
      "reference_year": 2018,
      "reference_model_year": 2018,
      "reference_km": 120000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Toyota RAV4 Hybrid::2020::120000": {
      "model": "Toyota RAV4 Hybrid",
      "cache_key": "Toyota RAV4 Hybrid::2020::120000",
      "estimated_price_nok": 250000,
      "price_source": "finn_typical",
      "match_count": 4,
      "comparable_count": 4,
      "price_note": "cached",
      "reference_year": 2020,
      "reference_model_year": 2020,
      "reference_km": 120000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Mitsubishi Outlander PHEV": {
      "model": "Mitsubishi Outlander PHEV",
      "estimated_price_nok": 220000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2020,
      "reference_km": 60000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Volkswagen Passat GTE": {
      "model": "Volkswagen Passat GTE",
      "estimated_price_nok": 200000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2020,
      "reference_km": 90000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Skoda Kodiaq 2.0 TDI 4x4": {
      "model": "Skoda Kodiaq 2.0 TDI 4x4",
      "estimated_price_nok": 269000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2018,
      "reference_km": 132700,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Mazda CX-5 diesel AWD": {
      "model": "Mazda CX-5 diesel AWD",
      "estimated_price_nok": 179532,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2016,
      "reference_km": 112200,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Peugeot 508 SW 2.0 BlueHDi": {
      "model": "Peugeot 508 SW 2.0 BlueHDi",
      "estimated_price_nok": 139532,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2015,
      "reference_km": 132500,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Tesla Model Y": {
      "model": "Tesla Model Y",
      "estimated_price_nok": 264532,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2021,
      "reference_km": 68901,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Mercedes EQC": {
      "model": "Mercedes EQC",
      "estimated_price_nok": 260000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2020,
      "reference_km": 126000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    },
    "Skoda Superb 2.0 TDI 4x4": {
      "model": "Skoda Superb 2.0 TDI 4x4",
      "estimated_price_nok": 180000,
      "price_source": "finn_typical",
      "match_count": 2,
      "comparable_count": 2,
      "price_note": "cached",
      "reference_year": 2018,
      "reference_km": 140000,
      "scraped_at": "2026-04-13T00:00:00+00:00"
    }
  }
}"""
    )
    df = run(
        price_estimation=True,
        use_cached_scraped_prices=True,
        price_cache_file=cache_file,
        price_overrides={"Toyota RAV4 Hybrid": 200_000},
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[df["model"] == "Toyota RAV4 Hybrid"].iloc[0]
    assert rav4_row["reference_price_nok"] == 250_000
    assert rav4_row["price_source"] == "finn_cached"


def test_existing_car_known_repairs_and_no_investment():
    avensis = compute_tco(
        {
            "model": "Toyota Avensis",
            "existing_car": True,
            "price_nok": 0,
            "current_resale_value_nok": 20_000,
            "year": 2012,
            "km": 182_000,
            "known_repairs_nok": 50_000,
        }
    )
    assert avensis["known_repairs_nok"] == 50_000
    assert avensis["investment_cost_nok"] == 0
    assert avensis["foregone_resale_value_nok"] == 20_000
    assert avensis["maintenance_nok"] == (
        avensis["scheduled_maintenance_nok"]
        + avensis["failure_risk_cost_nok"]
        + avensis["known_repairs_nok"]
    )
    assert avensis["total_cost_nok"] == (
        avensis["maintenance_nok"]
        + avensis["energy_nok"]
        + avensis["depreciation_nok"]
        + avensis["investment_cost_nok"]
        + avensis["foregone_resale_value_nok"]
    )


def test_new_models_compute_tco():
    for car in (
        {"model": "Skoda Kodiaq 2.0 TDI 4x4", "price_nok": 269_000, "year": 2018, "km": 132_700},
        {"model": "Mazda CX-5 diesel AWD", "price_nok": 179_532, "year": 2016, "km": 112_200},
        {"model": "Peugeot 508 SW 2.0 BlueHDi", "price_nok": 139_532, "year": 2015, "km": 132_500},
        {"model": "Tesla Model Y", "price_nok": 264_532, "year": 2021, "km": 68_901},
        {"model": "Mercedes EQC", "price_nok": 260_000, "year": 2020, "km": 126_000},
    ):
        result = compute_tco(car)
        assert result["total_cost_nok"] > 0


def test_tco_exposes_model_year_override():
    result = compute_tco(
        {"model": "Toyota RAV4 Hybrid", "price_nok": 240_000, "year": 2018, "model_year": 2018, "km": 120_000}
    )
    assert result["reference_year"] == 2018
    assert result["reference_model_year"] == 2018


def test_default_fleet_contains_two_rav4_years(tmp_path):
    df = run(output_dir=tmp_path, verbose=False)
    rav4_rows = df[df["model"] == "Toyota RAV4 Hybrid"]
    assert set(rav4_rows["reference_model_year"].tolist()) == {2018, 2020}


def test_model_y_failure_risk_cost_visible():
    model_y = compute_tco(
        {"model": "Tesla Model Y", "price_nok": 264_532, "year": 2021, "km": 68_901}
    )
    rav4 = compute_tco(_RAV4)
    assert model_y["failure_risk_cost_nok"] > 0
    assert model_y["scheduled_maintenance_nok"] < rav4["scheduled_maintenance_nok"]
