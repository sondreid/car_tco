"""CLI for area_search."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .finn import (
    AreaSearchClient,
    AreaSearchConfig,
    ListingSearch,
    format_listing,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="area-search",
        description="Search FINN car listings by model and area.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    recent = subparsers.add_parser("recent", help="Find recent listings for one model.")
    recent.add_argument("--model", required=True)
    recent.add_argument("--year-from", type=int, default=None)
    recent.add_argument("--year-to", type=int, default=None)
    recent.add_argument("--km-max", type=int, default=None)
    recent.add_argument("--price-max", type=int, default=None)
    recent.add_argument("--max-pages", type=int, default=3)
    recent.add_argument("--detail-fetch-limit", type=int, default=20)

    alert = subparsers.add_parser("alert", help="Find listings for models within areas and track new ads.")
    alert.add_argument("--model", action="append", required=True, help="Repeatable model query.")
    alert.add_argument("--area", action="append", required=True, help="Repeatable area filter.")
    alert.add_argument("--state-file", default=None)
    alert.add_argument("--max-pages", type=int, default=3)
    alert.add_argument("--detail-fetch-limit", type=int, default=50)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AreaSearchConfig(
        max_pages=args.max_pages,
        detail_fetch_limit=args.detail_fetch_limit,
        alert_state_file=Path(args.state_file) if getattr(args, "state_file", None) else AreaSearchConfig().alert_state_file,
    )
    client = AreaSearchClient(config=config)

    if args.command == "recent":
        result = client.find_recent_listings(
            ListingSearch(
                model=args.model,
                year_from=args.year_from,
                year_to=args.year_to,
                km_max=args.km_max,
                price_max=args.price_max,
            )
        )
        for listing in result.listings:
            print(format_listing(listing))
        return

    if args.command == "alert":
        searches = [ListingSearch(model=model) for model in args.model]
        result = client.run_alert(searches=searches, areas=args.area, state_file=args.state_file)
        print(f"matched={len(result.listings)} new={len(result.new_listings)} state={result.state_path}")
        for listing in result.new_listings:
            print(format_listing(listing))
        return

    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main(sys.argv[1:])
