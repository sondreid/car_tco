"""
High-level pipeline — single call from library or CLI.

    from car_tco.pipeline import RunMode, run
    from car_tco.assumptions import Assumptions

    df = run(assumptions=Assumptions(charge_share=0.25))
    df = run(mode=RunMode.USE_CACHED_SCRAPED_PRICE)
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import pandas as pd

from .assumptions import Assumptions
from .cache_store import load_entries_cache, save_entries_cache
from .cost.tco import compute_tco
from .data.reference_fleet import build_reference_fleet
from .overrides import (
    apply_fleet_overrides,
    ensure_overrides_file,
    has_active_overrides,
    has_price_input_overrides,
    load_overrides,
)
from .pricing import FinnPriceEstimator, PriceEstimatorConfig, estimate_fleet_prices
from .pricing.finn import build_cache_key, effective_model_year
from .reports import print_summary, write_csv
from .scoring.reliability import reliability_breakdown


class RunMode(str, Enum):
    DEFAULT = "default"
    SCRAPE_PRICES = "scrape_prices"
    RERUN_MODEL = "rerun_model"
    USE_CACHED_RELIABILITY = "use_cached_reliability"
    USE_CACHED = "use_cached"
    USE_CACHED_SCRAPED_PRICE = "use_cached_scraped_price"


def _normalize_mode(mode: str | RunMode) -> RunMode:
    if isinstance(mode, RunMode):
        return mode
    return RunMode(mode)


def _resolve_cache_path(
    output_dir: str | Path,
    explicit_path: str | Path | None,
    filename: str,
) -> Path:
    if explicit_path is not None:
        return Path(explicit_path)
    return Path(output_dir) / filename


def _resolve_fleet_path(
    output_dir: Path,
    explicit_path: str | Path | None,
) -> Path | None:
    if explicit_path is not None:
        return Path(explicit_path)
    local_path = output_dir / "fleet.json"
    return local_path if local_path.exists() else None


def _resolve_overrides_path(
    output_dir: Path,
    explicit_path: str | Path | None,
) -> tuple[Path, Path]:
    if explicit_path is not None:
        path = Path(explicit_path)
        return path, path
    example_path = output_dir / "overrides_example.json"
    active_path = output_dir / "overrides.json"
    return example_path, active_path if active_path.exists() else example_path


def _build_dataframe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows).sort_values("total_cost_nok").reset_index(drop=True)


def _build_reliability_cache_entry(car: dict, reliability: dict) -> dict:
    return {
        "model": car["model"],
        "cache_key": build_cache_key(car),
        "reference_year": int(car["year"]),
        "reference_model_year": effective_model_year(car),
        "reference_km": int(float(car["km"])),
        "generated_at": datetime.now(UTC).isoformat(),
        "reliability": reliability,
    }


def _build_results_cache_entry(car: dict, result: dict) -> dict:
    return {
        "model": car["model"],
        "cache_key": build_cache_key(car),
        "reference_year": int(car["year"]),
        "reference_model_year": effective_model_year(car),
        "reference_km": int(float(car["km"])),
        "generated_at": datetime.now(UTC).isoformat(),
        "result": result,
    }


def _load_reliability_from_cache(car: dict, cache: dict[str, dict]) -> dict:
    key = build_cache_key(car)
    if key not in cache:
        raise KeyError(f"missing cached reliability for {key}")
    entry = cache[key]
    reliability = entry.get("reliability")
    if not isinstance(reliability, dict):
        raise ValueError(f"cached reliability payload is invalid for {key}")
    return reliability


def _load_result_from_cache(car: dict, cache: dict[str, dict]) -> dict:
    key = build_cache_key(car)
    if key not in cache:
        raise KeyError(f"missing cached result for {key}")
    entry = cache[key]
    result = entry.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"cached result payload is invalid for {key}")
    if "opportunity_cost_nok" not in result and "financing_cost_nok" in result:
        result = dict(result)
        result["opportunity_cost_nok"] = result.pop("financing_cost_nok")
    return result


def _compute_results(
    fleet: list[dict],
    assumptions: Assumptions,
    reliability_cache: dict[str, dict] | None = None,
) -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    rows: list[dict] = []
    reliability_updates: dict[str, dict] = {}
    results_updates: dict[str, dict] = {}

    for car in fleet:
        if reliability_cache is None:
            reliability = reliability_breakdown(
                car["model"],
                int(car["year"]),
                float(car["km"]),
                model_year=int(car.get("model_year", car["year"])),
                assumptions=assumptions,
            )
            reliability_updates[build_cache_key(car)] = _build_reliability_cache_entry(
                car,
                reliability,
            )
        else:
            reliability = _load_reliability_from_cache(car, reliability_cache)

        row = compute_tco(car, assumptions, reliability=reliability)
        rows.append(row)
        results_updates[build_cache_key(car)] = _build_results_cache_entry(car, row)

    return rows, reliability_updates, results_updates


def run(
    assumptions: Assumptions | None = None,
    price_overrides: dict[str, float] | None = None,
    mode: str | RunMode = RunMode.DEFAULT,
    price_estimation: bool = False,
    price_estimator_config: PriceEstimatorConfig | None = None,
    price_estimator: FinnPriceEstimator | None = None,
    use_cached_scraped_prices: bool = False,
    price_cache_file: str | Path | None = None,
    reliability_cache_file: str | Path | None = None,
    results_cache_file: str | Path | None = None,
    overrides_file: str | Path | None = None,
    fleet_file: str | Path | None = None,
    extra_cars: list[dict] | None = None,
    output_dir: str | Path = "reports",
    output_prefix: str = "tco",
    write_output: bool = True,
    verbose: bool = True,
) -> "pd.DataFrame":  # noqa: F821
    """
    Execute one run mode for the car comparison pipeline.

    ``mode`` controls whether prices, reliability, and TCO are recomputed or
    read from caches. The Python API defaults to ``RunMode.DEFAULT`` so manual
    reference prices remain the baseline unless another mode is requested.
    """
    if assumptions is None:
        assumptions = Assumptions()

    if price_estimation or use_cached_scraped_prices:
        if mode != RunMode.DEFAULT:
            raise ValueError("legacy price_estimation flags cannot be combined with mode")
        mode = (
            RunMode.USE_CACHED_SCRAPED_PRICE
            if use_cached_scraped_prices
            else RunMode.RERUN_MODEL
        )

    mode = _normalize_mode(mode)

    if mode in {
        RunMode.SCRAPE_PRICES,
        RunMode.RERUN_MODEL,
        RunMode.USE_CACHED_SCRAPED_PRICE,
        RunMode.USE_CACHED,
    }:
        price_overrides = None

    output_dir_path = Path(output_dir)
    price_cache_path = _resolve_cache_path(output_dir_path, price_cache_file, "finn_price_cache.json")
    reliability_cache_path = _resolve_cache_path(
        output_dir_path,
        reliability_cache_file,
        "reliability_cache.json",
    )
    overrides_example_path, overrides_path = _resolve_overrides_path(
        output_dir_path,
        overrides_file,
    )
    results_cache_path = _resolve_cache_path(
        output_dir_path,
        results_cache_file,
        "results_cache.json",
    )

    fleet_path = _resolve_fleet_path(output_dir_path, fleet_file)
    fleet = build_reference_fleet(
        price_overrides=price_overrides,
        extra_cars=extra_cars,
        fleet_path=fleet_path,
    )
    ensure_overrides_file(overrides_example_path, fleet)
    fleet_overrides = load_overrides(overrides_path, fleet)
    overrides_active = has_active_overrides(fleet_overrides)
    price_input_overrides = has_price_input_overrides(fleet_overrides)
    fleet = apply_fleet_overrides(fleet, fleet_overrides)

    if mode == RunMode.SCRAPE_PRICES:
        refreshed_fleet = estimate_fleet_prices(
            fleet,
            config=price_estimator_config,
            estimator=price_estimator,
            cache_mode=False,
            cache_file=price_cache_path,
        )
        refreshed_fleet = apply_fleet_overrides(refreshed_fleet, fleet_overrides)
        return pd.DataFrame(refreshed_fleet)

    if mode == RunMode.USE_CACHED_SCRAPED_PRICE:
        fleet = estimate_fleet_prices(
            fleet,
            config=price_estimator_config,
            estimator=price_estimator,
            cache_mode=True,
            cache_file=price_cache_path,
            allow_cache_miss_fallback=price_input_overrides,
        )
        fleet = apply_fleet_overrides(fleet, fleet_overrides)
        rows, reliability_updates, results_updates = _compute_results(fleet, assumptions)
        save_entries_cache(reliability_cache_path, reliability_updates)
        save_entries_cache(results_cache_path, results_updates)
    elif mode == RunMode.RERUN_MODEL:
        fleet = estimate_fleet_prices(
            fleet,
            config=price_estimator_config,
            estimator=price_estimator,
            cache_mode=False,
            cache_file=price_cache_path,
        )
        fleet = apply_fleet_overrides(fleet, fleet_overrides)
        rows, reliability_updates, results_updates = _compute_results(fleet, assumptions)
        save_entries_cache(reliability_cache_path, reliability_updates)
        save_entries_cache(results_cache_path, results_updates)
    elif mode == RunMode.USE_CACHED_RELIABILITY:
        fleet = apply_fleet_overrides(fleet, fleet_overrides)
        reliability_cache = load_entries_cache(reliability_cache_path, "reliability")
        rows, _, results_updates = _compute_results(
            fleet,
            assumptions,
            reliability_cache=reliability_cache,
        )
        save_entries_cache(results_cache_path, results_updates)
    elif mode == RunMode.USE_CACHED:
        if overrides_active:
            if price_input_overrides:
                fleet = estimate_fleet_prices(
                    fleet,
                    config=price_estimator_config,
                    estimator=price_estimator,
                    cache_mode=True,
                    cache_file=price_cache_path,
                    allow_cache_miss_fallback=True,
                )
            fleet = apply_fleet_overrides(fleet, fleet_overrides)
            reliability_cache = load_entries_cache(reliability_cache_path, "reliability")
            rows, _, _ = _compute_results(
                fleet,
                assumptions,
                reliability_cache=reliability_cache,
            )
        else:
            results_cache = load_entries_cache(results_cache_path, "results")
            rows = [_load_result_from_cache(car, results_cache) for car in fleet]
    else:
        fleet = apply_fleet_overrides(fleet, fleet_overrides)
        rows, reliability_updates, results_updates = _compute_results(fleet, assumptions)
        save_entries_cache(reliability_cache_path, reliability_updates)
        save_entries_cache(results_cache_path, results_updates)

    df = _build_dataframe(rows)

    if write_output:
        full_path, summary_path = write_csv(df, output_dir=output_dir_path, prefix=output_prefix)
        if verbose:
            print(f"Written: {full_path}, {summary_path}")

    if verbose:
        print_summary(df)

    return df
