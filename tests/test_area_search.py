"""Tests for area_search."""

from area_search.finn import (
    AreaSearchClient,
    AreaSearchConfig,
    ListingSearch,
    load_alert_state,
    parse_detail_metadata,
    parse_search_page,
)


_SEARCH_HTML = """
<html><body>
<article class="sf-search-ad">
  <div class="mobility-search-ad-card-content m-16">
    <h2 class="h4 mb-0"><a href="https://www.finn.no/mobility/item/111"><span>Toyota RAV4 Hybrid</span></a></h2>
    <div class="text-caption mb-4 s-text-subtle truncate block max-w-full">AWD-i Style</div>
    <span class="text-caption font-bold inline-block mb-8">2020 ∙ 95 000 km ∙ Hybrid</span>
    <div><span class="t3 font-bold">329 000</span></div>
    <div class="flex items-end text-detail truncate">
      <div class="flex-col flex flex-1 s-text-subtle max-w-full truncate">
        <span class="truncate">Oslo</span>
        <span class="truncate">Forhandler</span>
      </div>
    </div>
  </div>
</article>
<article class="sf-search-ad">
  <div class="mobility-search-ad-card-content m-16">
    <h2 class="h4 mb-0"><a href="https://www.finn.no/mobility/item/222"><span>Toyota RAV4 Hybrid</span></a></h2>
    <div class="text-caption mb-4 s-text-subtle truncate block max-w-full">AWD-i Style</div>
    <span class="text-caption font-bold inline-block mb-8">2017 ∙ 130 000 km ∙ Hybrid</span>
    <div><span class="t3 font-bold">229 000</span></div>
    <div class="flex items-end text-detail truncate">
      <div class="flex-col flex flex-1 s-text-subtle max-w-full truncate">
        <span class="truncate">Bergen</span>
        <span class="truncate">Privat</span>
      </div>
    </div>
  </div>
</article>
<w-pagination current-page="1" pages="1"></w-pagination>
</body></html>
"""

_DETAIL_HTML = """
<html><body>
<section class="pt-40 mt-40 border-t"><h2 class="t3 mb-16">Sted</h2>
<div><a href="https://www.finn.no/map?adId=111&postalCode=0150">0150 Oslo</a></div></section>
<div><p class="s-text-subtle mb-0">Sist oppdatert</p><p class="font-bold whitespace-nowrap mb-0 md:mt-8">14. april 2026, 08:30</p></div>
<script>
{"key":"county","value":["20003"]}
</script>
<dt>Modellår</dt><dd>2020</dd>
<dt>Kilometerstand</dt><dd>95 000 km</dd>
</body></html>
"""


def test_parse_search_page_extracts_cards():
    listings, is_last_page = parse_search_page(_SEARCH_HTML)

    assert len(listings) == 2
    assert listings[0].finn_code == "111"
    assert listings[0].price_nok == 329_000
    assert listings[0].location_text == "Oslo"
    assert is_last_page is True


def test_parse_detail_metadata_extracts_alert_fields():
    detail = parse_detail_metadata(_DETAIL_HTML)

    assert detail["location_text"] == "0150 Oslo"
    assert detail["updated_at"] == "14. april 2026, 08:30"
    assert detail["postal_code"] == "0150"
    assert detail["county_code"] == "20003"
    assert detail["year"] == 2020
    assert detail["km"] == 95_000


def test_recent_search_filters_and_enriches_results():
    responses = {
        "https://www.finn.no/mobility/search/car?q=Toyota+RAV4+Hybrid&page=1": _SEARCH_HTML,
        "https://www.finn.no/mobility/item/111": _DETAIL_HTML,
    }
    client = AreaSearchClient(
        config=AreaSearchConfig(detail_fetch_limit=1),
        fetcher=responses.__getitem__,
    )

    result = client.find_recent_listings(
        ListingSearch(
            model="Toyota RAV4 Hybrid",
            year_from=2019,
            year_to=2021,
            km_max=120_000,
            price_max=350_000,
        )
    )

    assert len(result.listings) == 1
    assert result.listings[0].finn_code == "111"
    assert result.listings[0].updated_at == "14. april 2026, 08:30"


def test_alert_only_returns_new_matching_area_entries(tmp_path):
    responses = {
        "https://www.finn.no/mobility/search/car?q=Toyota+RAV4+Hybrid&page=1": _SEARCH_HTML,
        "https://www.finn.no/mobility/item/111": _DETAIL_HTML,
    }
    state_file = tmp_path / "area_alert.json"
    client = AreaSearchClient(
        config=AreaSearchConfig(detail_fetch_limit=1, alert_state_file=state_file),
        fetcher=responses.__getitem__,
    )

    first = client.run_alert(
        searches=[ListingSearch(model="Toyota RAV4 Hybrid", year_from=2019)],
        areas=["Oslo"],
    )
    second = client.run_alert(
        searches=[ListingSearch(model="Toyota RAV4 Hybrid", year_from=2019)],
        areas=["Oslo"],
    )

    assert len(first.new_listings) == 1
    assert len(second.new_listings) == 0
    assert load_alert_state(state_file) == {"111"}
