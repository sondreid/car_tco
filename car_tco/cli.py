"""
Command-line interface for car_tco.

Usage examples
--------------
# Refresh FINN prices and rerun the whole model
    car-tco

# Refresh only the FINN price cache
    car-tco --scrape-prices

# Rerun the model using cached FINN prices
    car-tco --use-cached-scraped-price

# Rerun costs using cached reliability outputs
    car-tco --use-cached-reliability

# Reuse the full cached model output without recomputing
    car-tco --use-cached
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .assumptions import Assumptions
from .pipeline import RunMode, run
from .pricing import PriceEstimatorConfig


def _parse_price_override(value: str) -> tuple[str, float]:
    """Parse 'Model Name=123456' into ('Model Name', 123456.0)."""
    try:
        model, price = value.rsplit("=", 1)
        return model.strip(), float(price.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Price override must be 'Model Name=price_nok', got: {value!r}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="car-tco",
        description="Compute 3-year TCO and reliability scores for a set of reference cars.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    p.add_argument(
        "--output-dir",
        default="reports",
        metavar="DIR",
        help="Directory for CSV output and caches (default: reports/).",
    )
    p.add_argument(
        "--output-prefix",
        default="tco",
        metavar="PREFIX",
        help="Filename prefix for CSVs (default: tco).",
    )
    p.add_argument(
        "--no-output",
        action="store_true",
        help="Skip writing CSV files.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output.",
    )

    p.add_argument(
        "--price",
        action="append",
        metavar="MODEL=NOK",
        type=_parse_price_override,
        help="Override purchase price for a model in manual-price modes.",
    )
    p.add_argument(
        "--scrape-prices",
        action="store_true",
        help="Refresh FINN price/km cache only. Does not run reliability or TCO.",
    )
    p.add_argument(
        "--rerun-model",
        action="store_true",
        help="Refresh FINN prices and rerun the full model. Cannot be combined with other mode flags.",
    )
    p.add_argument(
        "--use-cached-reliability",
        action="store_true",
        help="Reuse cached reliability outputs and rerun costs/reporting.",
    )
    p.add_argument(
        "--use-cached",
        action="store_true",
        help="Reuse fully cached model output and do not overwrite caches.",
    )
    p.add_argument(
        "--use-cached-scraped-price",
        action="store_true",
        help="Reuse cached FINN prices and rerun the full model without live scraping.",
    )
    p.add_argument(
        "--use-cached-scraped-prices",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--price-cache-file",
        default=None,
        metavar="PATH",
        help="Path to cached FINN price JSON file.",
    )
    p.add_argument(
        "--reliability-cache-file",
        default=None,
        metavar="PATH",
        help="Path to cached reliability JSON file.",
    )
    p.add_argument(
        "--results-cache-file",
        default=None,
        metavar="PATH",
        help="Path to cached full-results JSON file.",
    )
    p.add_argument(
        "--fleet",
        default=None,
        metavar="PATH",
        help=(
            "Path to a fleet JSON file listing the cars to analyse "
            "(default: OUTPUT_DIR/fleet.json if it exists, else the small "
            "checked-in example fleet)."
        ),
    )
    p.add_argument(
        "--overrides-file",
        default=None,
        metavar="PATH",
        help=(
            "Path to manual overrides JSON file "
            "(default: auto-create OUTPUT_DIR/overrides_example.json and "
            "auto-apply OUTPUT_DIR/overrides.json if it exists)."
        ),
    )
    p.add_argument(
        "--year-tolerance",
        type=int,
        default=None,
        metavar="YEARS",
        help="Max year difference for scraped price matches (default: 1).",
    )
    p.add_argument(
        "--km-tolerance",
        type=int,
        default=None,
        metavar="KM",
        help="Max km difference for scraped price matches (default: 20000).",
    )
    p.add_argument(
        "--min-matches",
        type=int,
        default=None,
        metavar="N",
        help="Minimum FINN matches required before using a scraped price estimate (default: 2).",
    )

    p.add_argument("--annual-km", type=float, default=None, metavar="KM", help="Annual kilometres driven.")
    p.add_argument("--years", type=int, default=None, metavar="N", help="Ownership horizon in years.")
    p.add_argument("--petrol", type=float, default=None, metavar="NOK/L", help="Petrol price per litre NOK.")
    p.add_argument("--diesel", type=float, default=None, metavar="NOK/L", help="Diesel price per litre NOK.")
    p.add_argument(
        "--electricity",
        type=float,
        default=None,
        metavar="NOK/kWh",
        help="Electricity price per kWh NOK.",
    )
    p.add_argument(
        "--capital-rate",
        type=float,
        default=None,
        metavar="RATE",
        help="Annual capital/opportunity cost rate.",
    )
    p.add_argument(
        "--charge-share",
        type=float,
        default=None,
        metavar="0-1",
        help="Fraction of trips starting with full PHEV charge.",
    )
    p.add_argument(
        "--trip-km",
        type=float,
        default=None,
        metavar="KM",
        help="Representative trip length for the PHEV blend.",
    )
    p.add_argument(
        "--ev-range-km",
        type=float,
        default=None,
        metavar="KM",
        help="PHEV usable EV range on full charge.",
    )
    p.add_argument(
        "--battery-kwh",
        type=float,
        default=None,
        metavar="KWH",
        help="PHEV usable battery capacity.",
    )
    p.add_argument(
        "--no-phev-blend",
        action="store_true",
        help="Disable dynamic PHEV consumption blending and use catalogue values.",
    )

    return p


def _resolve_mode(args: argparse.Namespace, parser: argparse.ArgumentParser) -> RunMode:
    mode_flags = {
        "scrape_prices": args.scrape_prices,
        "rerun_model": args.rerun_model,
        "use_cached_reliability": args.use_cached_reliability,
        "use_cached": args.use_cached,
        "use_cached_scraped_price": (
            args.use_cached_scraped_price or args.use_cached_scraped_prices
        ),
    }
    selected = [name for name, enabled in mode_flags.items() if enabled]
    if "rerun_model" in selected and len(selected) > 1:
        parser.error("--rerun-model cannot be combined with other mode flags")
    if len(selected) > 1:
        parser.error("mode flags are mutually exclusive")
    if not selected or selected == ["rerun_model"]:
        return RunMode.RERUN_MODEL
    return RunMode(selected[0])


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = _resolve_mode(args, parser)

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
    price_overrides = dict(args.price) if args.price else None

    estimator_config = PriceEstimatorConfig(
        **{
            key: value
            for key, value in {
                "year_tolerance": args.year_tolerance,
                "km_tolerance": args.km_tolerance,
                "min_matches": args.min_matches,
            }.items()
            if value is not None
        }
    )

    run(
        assumptions=assumptions,
        price_overrides=price_overrides,
        mode=mode,
        price_estimator_config=estimator_config,
        price_cache_file=args.price_cache_file,
        reliability_cache_file=args.reliability_cache_file,
        results_cache_file=args.results_cache_file,
        overrides_file=args.overrides_file,
        fleet_file=args.fleet,
        output_dir=Path(args.output_dir),
        output_prefix=args.output_prefix,
        write_output=not args.no_output and mode != RunMode.SCRAPE_PRICES,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
