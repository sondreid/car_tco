"""
Command-line interface for car_reliability.

Usage examples
--------------
# Default run:
    car-reliability

# Override prices:
    car-reliability --price "Toyota RAV4 Hybrid=260000" --price "Volkswagen Passat GTE=190000"

# Toggle assumptions:
    car-reliability --charge-share 0.25 --annual-km 20000 --petrol 25.0

# Change horizon:
    car-reliability --years 5

# Change output directory:
    car-reliability --output-dir ./results --output-prefix scenario_a

# Suppress file output:
    car-reliability --no-output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .assumptions import Assumptions
from .pipeline import run
from .pricing import PriceEstimatorConfig


def _parse_price_override(value: str) -> tuple[str, float]:
    """Parse 'Model Name=123456' into ('Model Name', 123456.0)."""
    try:
        model, price = value.rsplit("=", 1)
        return model.strip(), float(price.strip())
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Price override must be 'Model Name=price_nok', got: {value!r}"
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="car-reliability",
        description="Compute 3-year TCO and reliability scores for a set of reference cars.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── Output ────────────────────────────────────────────────────────────────
    p.add_argument(
        "--output-dir", default="reports", metavar="DIR",
        help="Directory for CSV output (default: reports/).",
    )
    p.add_argument(
        "--output-prefix", default="tco", metavar="PREFIX",
        help="Filename prefix for CSVs (default: tco).",
    )
    p.add_argument(
        "--no-output", action="store_true",
        help="Skip writing CSV files.",
    )
    p.add_argument(
        "--quiet", action="store_true",
        help="Suppress console output.",
    )

    # ── Price overrides ───────────────────────────────────────────────────────
    p.add_argument(
        "--price", action="append", metavar="MODEL=NOK",
        type=_parse_price_override,
        help=(
            "Override purchase price for a model. "
            "Can be specified multiple times. "
            "Example: --price \"Toyota RAV4 Hybrid=260000\""
        ),
    )
    p.add_argument(
        "--scrape-prices", action="store_true",
        help="Estimate reference prices from current FINN listings before running TCO.",
    )
    p.add_argument(
        "--use-cached-scraped-prices", action="store_true",
        help="Use cached scraped FINN prices only; do not fetch live data.",
    )
    p.add_argument(
        "--price-cache-file", default=None, metavar="PATH",
        help="Path to cached scraped price JSON file (default: reports/finn_price_cache.json).",
    )
    p.add_argument(
        "--year-tolerance", type=int, default=None, metavar="YEARS",
        help="Max year difference for scraped price matches (default: 1).",
    )
    p.add_argument(
        "--km-tolerance", type=int, default=None, metavar="KM",
        help="Max km difference for scraped price matches (default: 20000).",
    )
    p.add_argument(
        "--min-matches", type=int, default=None, metavar="N",
        help="Minimum matching FINN listings required before using the scraped price estimate (default: 2).",
    )

    # ── Driving / horizon ─────────────────────────────────────────────────────
    p.add_argument("--annual-km", type=float, default=None, metavar="KM",
                   help="Annual kilometres driven (default: 15000).")
    p.add_argument("--years", type=int, default=None, metavar="N",
                   help="Ownership horizon in years (default: 3).")

    # ── Energy prices ─────────────────────────────────────────────────────────
    p.add_argument("--petrol", type=float, default=None, metavar="NOK/L",
                   help="Petrol price per litre NOK (default: 23.0).")
    p.add_argument("--diesel", type=float, default=None, metavar="NOK/L",
                   help="Diesel price per litre NOK (default: 22.0).")
    p.add_argument("--electricity", type=float, default=None, metavar="NOK/kWh",
                   help="Electricity price per kWh NOK (default: 1.5).")

    # ── Capital ───────────────────────────────────────────────────────────────
    p.add_argument("--capital-rate", type=float, default=None, metavar="RATE",
                   help="Annual capital/opportunity cost rate (default: 0.04).")

    # ── PHEV assumptions ──────────────────────────────────────────────────────
    p.add_argument("--charge-share", type=float, default=None, metavar="0-1",
                   help="Fraction of trips starting with full PHEV charge (default: 0.5).")
    p.add_argument("--trip-km", type=float, default=None, metavar="KM",
                   help="Representative trip length for PHEV blend (default: 60).")
    p.add_argument("--ev-range-km", type=float, default=None, metavar="KM",
                   help="PHEV usable EV range on full charge (default: 54).")
    p.add_argument("--battery-kwh", type=float, default=None, metavar="KWH",
                   help="PHEV usable battery capacity kWh (default: 13.8).")
    p.add_argument("--no-phev-blend", action="store_true",
                   help="Disable dynamic PHEV consumption blending; use catalogue value.")

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.scrape_prices and args.use_cached_scraped_prices:
        parser.error("--scrape-prices and --use-cached-scraped-prices cannot be used together")

    # Build Assumptions, only overriding fields the user passed
    kw: dict = {}
    if args.annual_km is not None:
        kw["annual_km"] = args.annual_km
    if args.years is not None:
        kw["horizon_years"] = args.years
    if args.petrol is not None:
        kw["petrol_nok_per_l"] = args.petrol
    if args.diesel is not None:
        kw["diesel_nok_per_l"] = args.diesel
    if args.electricity is not None:
        kw["electricity_nok_per_kwh"] = args.electricity
    if args.capital_rate is not None:
        kw["capital_rate"] = args.capital_rate
    if args.charge_share is not None:
        kw["charge_share"] = args.charge_share
    if args.trip_km is not None:
        kw["trip_km"] = args.trip_km
    if args.ev_range_km is not None:
        kw["ev_range_km"] = args.ev_range_km
    if args.battery_kwh is not None:
        kw["battery_kwh_full"] = args.battery_kwh
    if args.no_phev_blend:
        kw["phev_dynamic_consumption"] = False

    assumptions = Assumptions(**kw)

    price_overrides: dict[str, float] = {}
    if args.price:
        price_overrides = dict(args.price)

    estimator_config = None
    if args.scrape_prices or args.use_cached_scraped_prices:
        estimator_kw: dict = {}
        if args.year_tolerance is not None:
            estimator_kw["year_tolerance"] = args.year_tolerance
        if args.km_tolerance is not None:
            estimator_kw["km_tolerance"] = args.km_tolerance
        if args.min_matches is not None:
            estimator_kw["min_matches"] = args.min_matches
        estimator_config = PriceEstimatorConfig(**estimator_kw)

    run(
        assumptions=assumptions,
        price_overrides=price_overrides or None,
        price_estimation=args.scrape_prices or args.use_cached_scraped_prices,
        price_estimator_config=estimator_config,
        use_cached_scraped_prices=args.use_cached_scraped_prices,
        price_cache_file=args.price_cache_file,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        write_output=not args.no_output,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
