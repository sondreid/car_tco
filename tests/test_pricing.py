"""Tests for FINN price estimation."""

from pathlib import Path

from car_tco.pricing.finn import (
    FinnPriceEstimator,
    PriceEstimatorConfig,
    estimate_price_from_cache,
    is_listing_match,
    load_price_cache,
    save_price_cache,
    FinnListing,
)


_SEARCH_HTML = """
<html><body>
<script id="seoStructuredData" type="application/ld+json">
{
  "@context": "https://schema.org",
  "mainEntity": {
    "itemListElement": [
      {
        "item": {
          "name": "Mitsubishi Outlander",
          "description": "PHEV Instyle+",
          "offers": {"price": "215000"},
          "url": "https://www.finn.no/mobility/item/1"
        }
      },
      {
        "item": {
          "name": "Mitsubishi Outlander",
          "description": "Plug-in hybrid S edition",
          "offers": {"price": "225000"},
          "url": "https://www.finn.no/mobility/item/2"
        }
      },
      {
        "item": {
          "name": "Mitsubishi Outlander",
          "description": "Diesel DI-D",
          "offers": {"price": "109000"},
          "url": "https://www.finn.no/mobility/item/3"
        }
      }
    ]
  }
}
</script>
</body></html>
"""

_DETAIL_ONE = '"key":"year","value":["2020"] "key":"mileage","value":["60000"] "key":"price","value":["215000"]'
_DETAIL_TWO = '"key":"year","value":["2020"] "key":"mileage","value":["59000"] "key":"price","value":["225000"]'
_DETAIL_THREE = '"key":"year","value":["2020"] "key":"mileage","value":["61000"] "key":"price","value":["109000"]'


def test_estimator_uses_typical_price_of_matching_listings():
    responses = {
        "https://www.finn.no/mobility/search/car?q=mitsubishi+outlander+phev": _SEARCH_HTML,
        "https://www.finn.no/mobility/item/1": _DETAIL_ONE,
        "https://www.finn.no/mobility/item/2": _DETAIL_TWO,
        "https://www.finn.no/mobility/item/3": _DETAIL_THREE,
    }

    estimator = FinnPriceEstimator(
        config=PriceEstimatorConfig(min_matches=2),
        fetcher=responses.__getitem__,
    )
    estimate = estimator.estimate_price(
        {
            "model": "Mitsubishi Outlander PHEV",
            "price_nok": 220_000,
            "year": 2020,
            "km": 60_000,
        }
    )

    assert estimate.estimated_price_nok == 220_000
    assert estimate.estimated_km == 59_500
    assert estimate.match_count ==2
    assert estimate.comparable_count == 2
    assert estimate.price_source == "finn_typical"


def test_estimator_falls_back_when_matches_are_missing():
    responses = {
        "https://www.finn.no/mobility/search/car?q=volkswagen+passat+gte": """
        <html><body><script id="seoStructuredData" type="application/ld+json">
        {"mainEntity": {"itemListElement": []}}
        </script></body></html>
        """,
    }

    estimator = FinnPriceEstimator(fetcher=responses.__getitem__)
    estimate = estimator.estimate_price(
        {
            "model": "Volkswagen Passat GTE",
            "price_nok": 200_000,
            "year": 2020,
            "km": 90_000,
        }
    )

    assert estimate.estimated_price_nok == 200_000
    assert estimate.estimated_km is None
    assert estimate.used_fallback is True


def test_cache_roundtrip_and_lookup(tmp_path):
    cache_file = tmp_path / "finn_price_cache.json"
    save_price_cache(
        cache_file,
        {
            "Toyota RAV4 Hybrid::2019::120000": {
                "model": "Toyota RAV4 Hybrid",
                "cache_key": "Toyota RAV4 Hybrid::2019::120000",
                "estimated_price_nok": 255_000,
                "estimated_km": 118_000,
                "price_source": "finn_typical",
                "match_count": 4,
                "comparable_count": 4,
                "price_note": "cached",
                "reference_year": 2019,
                "reference_model_year": 2019,
                "reference_km": 120_000,
                "scraped_at": "2026-04-13T00:00:00+00:00",
            }
        },
    )
    cache = load_price_cache(cache_file)
    estimate = estimate_price_from_cache(
        {"model": "Toyota RAV4 Hybrid", "year": 2019, "km": 120_000},
        cache,
    )
    assert estimate.estimated_price_nok == 255_000
    assert estimate.estimated_km == 118_000
    assert estimate.price_source == "finn_cached"


def test_cache_lookup_fails_on_missing_model():
    try:
        estimate_price_from_cache(
            {"model": "Toyota RAV4 Hybrid", "year": 2019, "km": 120_000},
            {},
        )
    except KeyError:
        return
    raise AssertionError("Expected KeyError for missing cached model")


def test_cache_lookup_uses_model_year_when_present():
    cache = {
        "Toyota RAV4 Hybrid::2018::120000": {
            "model": "Toyota RAV4 Hybrid",
            "cache_key": "Toyota RAV4 Hybrid::2018::120000",
            "estimated_price_nok": 235_000,
            "estimated_km": 117_000,
            "price_source": "finn_typical",
            "match_count": 3,
            "comparable_count": 3,
            "price_note": "cached",
            "reference_year": 2019,
            "reference_model_year": 2018,
            "reference_km": 120_000,
            "scraped_at": "2026-04-13T00:00:00+00:00",
        }
    }
    estimate = estimate_price_from_cache(
        {"model": "Toyota RAV4 Hybrid", "year": 2019, "model_year": 2018, "km": 120_000},
        cache,
    )
    assert estimate.estimated_price_nok == 235_000
    assert estimate.estimated_km == 117_000


def test_listing_match_allows_lower_km_but_rejects_higher_km():
    car = {"model": "Toyota RAV4 Hybrid", "price_nok": 240_000, "year": 2018, "km": 120_000}
    config = PriceEstimatorConfig()
    low_km = FinnListing(
        title="Toyota RAV4 Hybrid",
        description="awd hybrid",
        price_nok=235_000,
        year=2018,
        km=95_000,
        url="https://example.com/low",
    )
    high_km = FinnListing(
        title="Toyota RAV4 Hybrid",
        description="awd hybrid",
        price_nok=235_000,
        year=2018,
        km=125_000,
        url="https://example.com/high",
    )
    from car_tco.pricing.finn import _MODEL_PROFILES

    profile = _MODEL_PROFILES["Toyota RAV4 Hybrid"]
    assert is_listing_match(low_km, car, profile, config) is True
    assert is_listing_match(high_km, car, profile, config) is False


def test_listing_match_rejects_price_above_reference_price():
    car = {"model": "Toyota RAV4 Hybrid", "price_nok": 240_000, "year": 2018, "km": 120_000}
    config = PriceEstimatorConfig(max_price_nok=240_000)
    expensive = FinnListing(
        title="Toyota RAV4 Hybrid",
        description="awd hybrid",
        price_nok=245_000,
        year=2018,
        km=110_000,
        url="https://example.com/expensive",
    )
    from car_tco.pricing.finn import _MODEL_PROFILES

    profile = _MODEL_PROFILES["Toyota RAV4 Hybrid"]
    assert is_listing_match(expensive, car, profile, config) is False
