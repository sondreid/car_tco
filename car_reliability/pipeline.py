"""
High-level pipeline — single call from library or CLI.

    from car_reliability.pipeline import run
    from car_reliability.assumptions import Assumptions

    df = run(assumptions=Assumptions(charge_share=0.25))
"""

from __future__ import annotations

from pathlib import Path

from .assumptions import Assumptions
from .data.reference_fleet import build_reference_fleet
from .reports import build_results_df, write_csv, print_summary
from .pricing import FinnPriceEstimator, PriceEstimatorConfig, estimate_fleet_prices


def run(
    assumptions: Assumptions | None = None,
    price_overrides: dict[str, float] | None = None,
    price_estimation: bool = False,
    price_estimator_config: PriceEstimatorConfig | None = None,
    price_estimator: FinnPriceEstimator | None = None,
    use_cached_scraped_prices: bool = False,
    price_cache_file: str | Path | None = None,
    extra_cars: list[dict] | None = None,
    output_dir: str | Path = "reports",
    output_prefix: str = "tco",
    write_output: bool = True,
    verbose: bool = True,
) -> "pd.DataFrame":  # noqa: F821
    """
    Execute the full TCO pipeline.

    Parameters
    ----------
    assumptions:
        Override any defaults by passing a custom ``Assumptions`` instance.
    price_overrides:
        Map of {model_name: new_price_nok} — patches purchase price without
        editing source code in the default non-scraping mode. Example::

            price_overrides={"Toyota RAV4 Hybrid": 260_000}
    price_estimation:
        When True, replace reference prices with a FINN-based mean asking
        price before TCO is calculated.
    price_estimator_config:
        Optional FINN scraper config.
    price_estimator:
        Optional estimator instance. Useful for tests.
    use_cached_scraped_prices:
        When True, use cached scraped prices only and do not query FINN.
    price_cache_file:
        JSON cache path for scraped prices.

    extra_cars:
        List of additional car dicts to include beyond the default fleet.
    output_dir:
        Directory for CSV output.
    output_prefix:
        Filename prefix for generated CSVs.
    write_output:
        Write CSVs when True (default).
    verbose:
        Print summary table when True (default).

    Returns
    -------
    pd.DataFrame
        Full results DataFrame sorted by total cost (ascending).
    """
    if assumptions is None:
        assumptions = Assumptions()

    fleet = build_reference_fleet(extra_cars=extra_cars)

    if price_estimation:
        fleet = estimate_fleet_prices(
            fleet,
            config=price_estimator_config,
            estimator=price_estimator,
            cache_mode=use_cached_scraped_prices,
            cache_file=price_cache_file,
        )
    elif price_overrides:
        for car in fleet:
            if car["model"] in price_overrides:
                car["price_nok"] = float(price_overrides[car["model"]])
                car["price_source"] = "manual_override"
                car["price_match_count"] = 0
                car["price_fallback_used"] = False
                car["price_note"] = "manual override"

    df = build_results_df(fleet, assumptions)

    if write_output:
        full_path, summary_path = write_csv(df, output_dir=output_dir, prefix=output_prefix)
        if verbose:
            print(f"Written: {full_path}, {summary_path}")

    if verbose:
        print_summary(df)

    return df
