"""CLI tests."""

from contextlib import redirect_stderr
import io

from car_reliability.cli import build_parser, _resolve_mode
from car_reliability.pipeline import RunMode


def test_cli_defaults_to_rerun_model():
    parser = build_parser()
    args = parser.parse_args([])
    assert _resolve_mode(args, parser) == RunMode.RERUN_MODEL


def test_cli_resolves_cached_price_mode():
    parser = build_parser()
    args = parser.parse_args(["--use-cached-scraped-price"])
    assert _resolve_mode(args, parser) == RunMode.USE_CACHED_SCRAPED_PRICE


def test_cli_allows_hidden_plural_cached_price_alias():
    parser = build_parser()
    args = parser.parse_args(["--use-cached-scraped-prices"])
    assert _resolve_mode(args, parser) == RunMode.USE_CACHED_SCRAPED_PRICE


def test_cli_rejects_rerun_model_with_other_mode():
    parser = build_parser()
    args = parser.parse_args(["--rerun-model", "--use-cached"])
    try:
        with redirect_stderr(io.StringIO()):
            _resolve_mode(args, parser)
    except SystemExit:
        return
    raise AssertionError("Expected mode validation to reject conflicting flags")
