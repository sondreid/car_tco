"""Integration-level TCO tests."""

from __future__ import annotations

import json

from car_tco.assumptions import Assumptions
from car_tco.cost.tco import compute_tco
from car_tco.pipeline import RunMode, run
from car_tco.pricing import FinnPriceEstimator, PriceEstimatorConfig
from car_tco.pricing.finn import FinnPriceEstimate


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


class StubEstimator(FinnPriceEstimator):
    def __init__(
        self,
        prices: dict[str, int] | None = None,
        kms: dict[str, int] | None = None,
    ) -> None:
        super().__init__(config=PriceEstimatorConfig())
        self._prices = prices or {}
        self._kms = kms or {}

    def estimate_price(self, car: dict) -> FinnPriceEstimate:
        estimate = self._prices.get(car["model"], int(float(car["price_nok"])))
        km = self._kms.get(car["model"])
        return FinnPriceEstimate(estimate, km, "finn_typical", 3, 3, False, "stub")


def _load_entries(path) -> dict[str, dict]:
    return json.loads(path.read_text())["entries"]


def test_tco_keys():
    result = compute_tco(_RAV4)
    expected_keys = {
        "model",
        "reliability_score",
        "maintenance_nok",
        "energy_nok",
        "depreciation_nok",
        "opportunity_cost_nok",
        "resale_nok",
        "total_cost_nok",
        "cost_per_month_nok",
        "scheduled_maintenance_nok",
        "failure_risk_cost_nok",
        "reliability_evidence_score",
        "technical_robustness",
        "reliability_confidence",
    }
    assert expected_keys.issubset(result.keys())


def test_total_equals_components():
    r = compute_tco(_RAV4)
    expected_total = (
        r["depreciation_nok"]
        + r["opportunity_cost_nok"]
        + r["energy_nok"]
        + r["maintenance_nok"]
    )
    assert r["total_cost_nok"] == expected_total


def test_known_repairs_add_financing_cost():
    assumptions = Assumptions()
    base = compute_tco(_RAV4, assumptions)
    with_repairs = compute_tco({**_RAV4, "known_repairs_nok": 10_000}, assumptions)
    expected_extra = round(
        10_000 + 10_000 * assumptions.capital_rate * assumptions.horizon_years
    )

    assert with_repairs["foregone_resale_value_nok"] == 0
    assert with_repairs["opportunity_cost_nok"] == (
        base["opportunity_cost_nok"]
        + round(10_000 * assumptions.capital_rate * assumptions.horizon_years)
    )
    assert with_repairs["total_cost_nok"] == base["total_cost_nok"] + expected_extra


def test_higher_price_increases_total():
    cheap = compute_tco({**_RAV4, "price_nok": 200_000})
    expensive = compute_tco({**_RAV4, "price_nok": 350_000})
    assert expensive["total_cost_nok"] > cheap["total_cost_nok"]


def test_price_override_in_default_pipeline(tmp_path):
    df = run(
        price_overrides={"Toyota RAV4 Hybrid": 200_000},
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[df["model"] == "Toyota RAV4 Hybrid"].iloc[0]
    assert rav4_row["reference_price_nok"] == 200_000


def test_pipeline_returns_sorted(tmp_path):
    df = run(output_dir=tmp_path, verbose=False)
    assert df["total_cost_nok"].tolist() == sorted(df["total_cost_nok"].tolist())


def test_pipeline_writes_csvs(tmp_path):
    run(output_dir=tmp_path, output_prefix="test", verbose=False)
    assert (tmp_path / "test_full.csv").exists()
    assert (tmp_path / "test_summary.csv").exists()
    assert (tmp_path / "overrides_example.json").exists()
    assert (tmp_path / "reliability_cache.json").exists()
    assert (tmp_path / "results_cache.json").exists()


def test_scrape_prices_updates_cache_only(tmp_path):
    run(
        mode=RunMode.SCRAPE_PRICES,
        price_estimator=StubEstimator({"Toyota RAV4 Hybrid": 255_000}),
        output_dir=tmp_path,
        verbose=False,
    )
    assert (tmp_path / "finn_price_cache.json").exists()
    assert not (tmp_path / "tco_full.csv").exists()


def test_rerun_model_uses_scraped_prices(tmp_path):
    df = run(
        mode=RunMode.RERUN_MODEL,
        price_estimator=StubEstimator(
            {"Toyota RAV4 Hybrid": 255_000},
            {"Toyota RAV4 Hybrid": 118_000},
        ),
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[df["model"] == "Toyota RAV4 Hybrid"].iloc[0]
    assert rav4_row["reference_price_nok"] == 255_000
    assert rav4_row["reference_km"] == 118_000
    assert rav4_row["price_source"] == "finn_typical"
    assert (tmp_path / "finn_price_cache.json").exists()


def test_use_cached_scraped_price_reuses_price_cache(tmp_path):
    run(
        mode=RunMode.RERUN_MODEL,
        price_estimator=StubEstimator(
            {"Toyota RAV4 Hybrid": 255_000},
            {"Toyota RAV4 Hybrid": 118_000},
        ),
        output_dir=tmp_path,
        verbose=False,
    )
    df = run(
        mode=RunMode.USE_CACHED_SCRAPED_PRICE,
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[df["model"] == "Toyota RAV4 Hybrid"].iloc[0]
    assert rav4_row["reference_price_nok"] == 255_000
    assert rav4_row["reference_km"] == 118_000
    assert rav4_row["price_source"] == "finn_cached"


def test_use_cached_reliability_uses_reliability_cache(tmp_path):
    run(output_dir=tmp_path, verbose=False)
    cache_path = tmp_path / "reliability_cache.json"
    cache = _load_entries(cache_path)
    cache["Toyota RAV4 Hybrid::2020::120000"]["reliability"]["reliability_score"] = 61.0
    cache_path.write_text(json.dumps({"entries": cache}, indent=2, sort_keys=True))

    df = run(
        mode=RunMode.USE_CACHED_RELIABILITY,
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[
        (df["model"] == "Toyota RAV4 Hybrid") & (df["reference_model_year"] == 2020)
    ].iloc[0]
    assert rav4_row["reliability_score"] == 61.0


def test_use_cached_reads_results_cache(tmp_path):
    run(output_dir=tmp_path, verbose=False)
    cache_path = tmp_path / "results_cache.json"
    cache = _load_entries(cache_path)
    cache["Toyota RAV4 Hybrid::2020::120000"]["result"]["total_cost_nok"] = 123
    cache_path.write_text(json.dumps({"entries": cache}, indent=2, sort_keys=True))

    df = run(mode=RunMode.USE_CACHED, output_dir=tmp_path, verbose=False)
    rav4_row = df[
        (df["model"] == "Toyota RAV4 Hybrid") & (df["reference_model_year"] == 2020)
    ].iloc[0]
    assert rav4_row["total_cost_nok"] == 123


def test_overrides_file_can_force_exact_resale(tmp_path):
    run(output_dir=tmp_path, verbose=False)
    overrides_path = tmp_path / "overrides_example.json"
    payload = json.loads(overrides_path.read_text())
    payload["fleet_overrides"]["Mitsubishi Outlander PHEV::2020::60000"]["resale_nok"] = 150_000
    overrides_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    df = run(output_dir=tmp_path, verbose=False)
    outlander = df[df["model"] == "Mitsubishi Outlander PHEV"].iloc[0]
    assert outlander["resale_nok"] == 150_000


def test_overrides_win_over_cached_results(tmp_path):
    run(output_dir=tmp_path, verbose=False)
    overrides_path = tmp_path / "overrides_example.json"
    payload = json.loads(overrides_path.read_text())
    payload["fleet_overrides"]["Toyota RAV4 Hybrid::2020::120000"]["resale_nok"] = 999
    overrides_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    df = run(mode=RunMode.USE_CACHED, output_dir=tmp_path, verbose=False)
    rav4_row = df[
        (df["model"] == "Toyota RAV4 Hybrid") & (df["reference_model_year"] == 2020)
    ].iloc[0]
    assert rav4_row["resale_nok"] == 999


def test_overrides_json_takes_precedence_over_example(tmp_path):
    run(output_dir=tmp_path, verbose=False)
    explicit_path = tmp_path / "overrides.json"
    explicit_path.write_text(
        json.dumps(
            {
                "fleet_overrides": {
                    "Toyota RAV4 Hybrid::2020::120000": {
                        "price_nok": 333_000,
                        "km": None,
                        "year": None,
                        "model_year": None,
                        "url": None,
                        "known_repairs_nok": None,
                        "current_resale_value_nok": None,
                        "scheduled_maintenance_nok": None,
                        "residual_base": None,
                        "resale_nok": None,
                    }
                }
            },
            indent=2,
            sort_keys=True,
        )
    )

    df = run(output_dir=tmp_path, verbose=False)
    rav4_row = df[
        (df["model"] == "Toyota RAV4 Hybrid") & (df["reference_model_year"] == 2020)
    ].iloc[0]
    assert (tmp_path / "overrides_example.json").exists()
    assert rav4_row["reference_price_nok"] == 333_000


def test_cached_price_mode_keeps_current_override_when_cache_key_is_missing(tmp_path):
    run(
        mode=RunMode.RERUN_MODEL,
        price_estimator=StubEstimator({"Toyota RAV4 Hybrid": 255_000}),
        output_dir=tmp_path,
        verbose=False,
    )
    explicit_path = tmp_path / "overrides.json"
    explicit_path.write_text(
        json.dumps(
            {
                "fleet_overrides": {
                    "Toyota RAV4 Hybrid::2020::120000": {
                        "price_nok": 333_000,
                        "km": 100_000,
                        "year": None,
                        "model_year": None,
                        "url": None,
                        "known_repairs_nok": None,
                        "current_resale_value_nok": None,
                        "scheduled_maintenance_nok": None,
                        "residual_base": None,
                        "resale_nok": None,
                    }
                }
            },
            indent=2,
            sort_keys=True,
        )
    )

    df = run(
        mode=RunMode.USE_CACHED_SCRAPED_PRICE,
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[
        (df["model"] == "Toyota RAV4 Hybrid") & (df["reference_model_year"] == 2020)
    ].iloc[0]
    assert rav4_row["reference_price_nok"] == 333_000
    assert rav4_row["reference_km"] == 100_000
    assert rav4_row["price_source"] == "manual"


def test_rerun_model_reapplies_price_input_overrides_after_scrape(tmp_path):
    run(output_dir=tmp_path, verbose=False)
    explicit_path = tmp_path / "overrides.json"
    explicit_path.write_text(
        json.dumps(
            {
                "fleet_overrides": {
                    "Toyota RAV4 Hybrid::2020::120000": {
                        "price_nok": 333_000,
                        "km": 100_000,
                        "year": None,
                        "model_year": 2019,
                        "url": None,
                        "known_repairs_nok": None,
                        "current_resale_value_nok": None,
                        "scheduled_maintenance_nok": None,
                        "residual_base": None,
                        "resale_nok": None,
                    }
                }
            },
            indent=2,
            sort_keys=True,
        )
    )

    df = run(
        mode=RunMode.RERUN_MODEL,
        price_estimator=StubEstimator(
            {"Toyota RAV4 Hybrid": 255_000},
            {"Toyota RAV4 Hybrid": 118_000},
        ),
        output_dir=tmp_path,
        verbose=False,
    )
    rav4_row = df[
        (df["model"] == "Toyota RAV4 Hybrid") & (df["reference_model_year"] == 2019)
    ].iloc[0]
    assert rav4_row["reference_price_nok"] == 333_000
    assert rav4_row["reference_km"] == 100_000


def test_no_phev_blend_uses_catalogue():
    a_blend = Assumptions(phev_dynamic_consumption=True)
    a_raw = Assumptions(phev_dynamic_consumption=False)
    outlander = {
        "model": "Mitsubishi Outlander PHEV",
        "price_nok": 220_000,
        "year": 2020,
        "km": 60_000,
    }
    assert compute_tco(outlander, a_raw)["energy_nok"] > compute_tco(outlander, a_blend)["energy_nok"]


def test_existing_car_known_repairs_and_opportunity_cost():
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
    assert avensis["foregone_resale_value_nok"] == 20_000
    assert avensis["opportunity_cost_nok"] == 8_400
    assert avensis["maintenance_nok"] == (
        avensis["scheduled_maintenance_nok"]
        + avensis["failure_risk_cost_nok"]
        + avensis["known_repairs_nok"]
    )
    assert avensis["total_cost_nok"] == (
        avensis["maintenance_nok"]
        + avensis["energy_nok"]
        + avensis["depreciation_nok"]
        + avensis["opportunity_cost_nok"]
        + avensis["foregone_resale_value_nok"]
    )


def test_new_models_compute_tco():
    for car in (
        {"model": "Skoda Kodiaq 2.0 TDI 4x4", "price_nok": 269_000, "year": 2018, "km": 132_700},
        {"model": "Mazda CX-5 diesel AWD", "price_nok": 179_532, "year": 2016, "km": 112_200},
        {"model": "Mercedes GLC 300e 4MATIC", "price_nok": 435_000, "year": 2020, "km": 86_772},
        {"model": "Tesla Model Y", "price_nok": 264_532, "year": 2021, "km": 68_901},
        {"model": "Mercedes EQC", "price_nok": 260_000, "year": 2020, "km": 126_000},
    ):
        assert compute_tco(car)["total_cost_nok"] > 0


def test_tco_exposes_model_year_override():
    result = compute_tco(
        {
            "model": "Toyota RAV4 Hybrid",
            "price_nok": 240_000,
            "year": 2018,
            "model_year": 2018,
            "km": 120_000,
        }
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
