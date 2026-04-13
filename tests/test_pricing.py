"""Tests for FINN price estimation."""

from car_reliability.pricing.finn import FinnPriceEstimator, PriceEstimatorConfig


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

_DETAIL_ONE = '"key":"year","value":["2020"] "key":"mileage","value":["64000"] "key":"price","value":["215000"]'
_DETAIL_TWO = '"key":"year","value":["2020"] "key":"mileage","value":["59000"] "key":"price","value":["225000"]'
_DETAIL_THREE = '"key":"year","value":["2020"] "key":"mileage","value":["61000"] "key":"price","value":["109000"]'


def test_estimator_uses_mean_of_matching_listings():
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
    assert estimate.match_count == 2
    assert estimate.price_source == "finn_mean"


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
    assert estimate.used_fallback is True
