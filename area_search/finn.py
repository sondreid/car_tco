"""Search recent FINN car listings by query and area."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from car_reliability.pricing.finn import normalize_text, parse_int


_SEARCH_URL = "https://www.finn.no/mobility/search/car"
_ITEM_URL_PREFIX = "https://www.finn.no/mobility/item/"
_DEFAULT_ALERT_STATE = Path("reports/area_search_alert_state.json")

_COUNTY_ALIASES = {
    "agder": ("agder",),
    "akershus": ("akershus",),
    "buskerud": ("buskerud",),
    "finnmark": ("finnmark",),
    "innlandet": ("innlandet",),
    "more og romsdal": ("more og romsdal", "mre og romsdal", "møre og romsdal"),
    "nordland": ("nordland",),
    "oslo": ("oslo",),
    "rogaland": ("rogaland",),
    "telemark": ("telemark",),
    "troms": ("troms",),
    "trondelag": ("trondelag", "trøndelag"),
    "vestfold": ("vestfold",),
    "vestland": ("vestland",),
    "ostfold": ("ostfold", "østfold"),
}


@dataclass(frozen=True)
class AreaSearchConfig:
    """Config for area search."""

    request_timeout_seconds: float = 15.0
    max_pages: int = 3
    max_results_per_search: int = 150
    detail_fetch_limit: int = 50
    alert_state_file: Path = _DEFAULT_ALERT_STATE


@dataclass(frozen=True)
class ListingSearch:
    """Structured listing query."""

    model: str
    year_from: int | None = None
    year_to: int | None = None
    km_max: int | None = None
    price_max: int | None = None


@dataclass(frozen=True)
class SearchListing:
    """One FINN listing."""

    finn_code: str
    title: str
    subtitle: str
    price_nok: int | None
    year: int | None
    km: int | None
    fuel: str
    location_text: str
    seller_text: str
    url: str
    updated_at: str = ""
    postal_code: str = ""
    county_code: str = ""


@dataclass(frozen=True)
class RecentSearchResult:
    """Result set for one recent-listing search."""

    query: ListingSearch
    listings: list[SearchListing]


@dataclass(frozen=True)
class AlertResult:
    """Result set for area alert runs."""

    areas: tuple[str, ...]
    listings: list[SearchListing]
    new_listings: list[SearchListing]
    state_path: Path


class AreaSearchClient:
    """FINN search client for recent listings and area alerts."""

    def __init__(
        self,
        config: AreaSearchConfig | None = None,
        fetcher: callable | None = None,
    ) -> None:
        self.config = config or AreaSearchConfig()
        self._fetcher = fetcher or self._default_fetcher

    def find_recent_listings(self, search: ListingSearch) -> RecentSearchResult:
        listings = self._search(search)
        return RecentSearchResult(query=search, listings=listings)

    def fetch_area_listings(
        self,
        searches: list[ListingSearch],
        areas: list[str],
    ) -> list[SearchListing]:
        normalized_areas = {_normalize_area(area) for area in areas}
        results: list[SearchListing] = []
        seen_codes: set[str] = set()
        for search in searches:
            for listing in self._search(search):
                if listing.finn_code in seen_codes:
                    continue
                if not _matches_area(listing, normalized_areas):
                    continue
                seen_codes.add(listing.finn_code)
                results.append(listing)
        return sorted(results, key=_listing_sort_key)

    def run_alert(
        self,
        searches: list[ListingSearch],
        areas: list[str],
        state_file: str | Path | None = None,
    ) -> AlertResult:
        state_path = Path(state_file) if state_file is not None else self.config.alert_state_file
        previous_ids = load_alert_state(state_path)
        listings = self.fetch_area_listings(searches, areas)
        new_listings = [listing for listing in listings if listing.finn_code not in previous_ids]
        save_alert_state(state_path, {listing.finn_code for listing in listings})
        return AlertResult(
            areas=tuple(areas),
            listings=listings,
            new_listings=new_listings,
            state_path=state_path,
        )

    def _search(self, search: ListingSearch) -> list[SearchListing]:
        page = 1
        listings: list[SearchListing] = []
        while page <= self.config.max_pages and len(listings) < self.config.max_results_per_search:
            search_html = self._fetcher(self._build_search_url(search, page))
            page_listings, is_last_page = parse_search_page(search_html)
            matched = [listing for listing in page_listings if _matches_search(listing, search)]
            listings.extend(matched)
            if is_last_page or not page_listings:
                break
            page += 1

        unique = _dedupe_listings(listings)
        enriched = self._enrich_listings(unique[: self.config.detail_fetch_limit])
        if len(unique) > self.config.detail_fetch_limit:
            enriched.extend(unique[self.config.detail_fetch_limit :])
        return sorted(enriched, key=_listing_sort_key)

    def _enrich_listings(self, listings: list[SearchListing]) -> list[SearchListing]:
        enriched: list[SearchListing] = []
        for listing in listings:
            try:
                detail_html = self._fetcher(listing.url)
            except Exception:
                enriched.append(listing)
                continue
            detail = parse_detail_metadata(detail_html)
            enriched.append(
                SearchListing(
                    finn_code=listing.finn_code,
                    title=listing.title,
                    subtitle=listing.subtitle,
                    price_nok=listing.price_nok,
                    year=detail.get("year") or listing.year,
                    km=detail.get("km") or listing.km,
                    fuel=listing.fuel,
                    location_text=detail.get("location_text") or listing.location_text,
                    seller_text=listing.seller_text,
                    url=listing.url,
                    updated_at=detail.get("updated_at", ""),
                    postal_code=detail.get("postal_code", ""),
                    county_code=detail.get("county_code", ""),
                )
            )
        return enriched

    def _build_search_url(self, search: ListingSearch, page: int) -> str:
        params = {
            "q": search.model,
            "page": page,
        }
        return f"{_SEARCH_URL}?{urlencode(params)}"

    def _default_fetcher(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/135.0 Safari/537.36"
                ),
                "Accept-Language": "nb-NO,nb;q=0.9,en;q=0.8",
            },
        )
        try:
            with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                return response.read().decode("utf-8")
        except Exception:
            result = subprocess.run(
                ["curl", "-L", url],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout


def parse_search_page(html_text: str) -> tuple[list[SearchListing], bool]:
    """Parse FINN search cards from one page."""

    cards = re.findall(
        r'<article class="[^"]*sf-search-ad[^"]*".*?</article>',
        html_text,
        re.DOTALL,
    )
    listings = [parse_search_card(card) for card in cards]
    current_page, page_count = parse_pagination(html_text)
    return listings, current_page >= page_count


def parse_search_card(card_html: str) -> SearchListing:
    """Parse one search-card article."""

    url_match = re.search(r'href="(?P<url>https://www\.finn\.no/mobility/item/\d+)"', card_html)
    if not url_match:
        raise ValueError("listing url not found")
    url = html.unescape(url_match.group("url"))
    code = url.rsplit("/", 1)[-1]
    title = _extract_tag_text(card_html, "h2")
    subtitle = _extract_first_class_text(card_html, "text-caption mb-4")
    meta_text = _extract_first_class_text(card_html, "text-caption font-bold inline-block mb-8")
    price_text = _extract_first_class_text(card_html, "t3 font-bold")
    location_parts = re.findall(r'<span class="truncate">(?P<text>.*?)</span>', card_html, re.DOTALL)
    location_text = _clean_html_text(location_parts[0]) if location_parts else ""
    seller_text = _clean_html_text(location_parts[1]) if len(location_parts) > 1 else ""
    year, km, fuel = parse_card_meta(meta_text)
    return SearchListing(
        finn_code=code,
        title=title,
        subtitle=subtitle,
        price_nok=parse_int(price_text),
        year=year,
        km=km,
        fuel=fuel,
        location_text=location_text,
        seller_text=seller_text,
        url=url,
    )


def parse_card_meta(meta_text: str) -> tuple[int | None, int | None, str]:
    """Parse year, km and fuel from one card metadata line."""

    parts = [_clean_html_text(part) for part in meta_text.split("∙")]
    year = parse_int(parts[0]) if parts else None
    km = parse_int(parts[1]) if len(parts) > 1 else None
    fuel = parts[2] if len(parts) > 2 else ""
    return year, km, fuel


def parse_pagination(html_text: str) -> tuple[int, int]:
    """Parse current and last page numbers."""

    match = re.search(r'<w-pagination[^>]*current-page="(?P<current>\d+)"[^>]*pages="(?P<pages>\d+)"', html_text)
    if not match:
        return 1, 1
    return int(match.group("current")), int(match.group("pages"))


def parse_detail_metadata(html_text: str) -> dict[str, str | int | None]:
    """Parse listing detail metadata used for alerts."""

    location_match = re.search(
        r'<h2 class="t3 mb-16">Sted</h2>.*?<a [^>]*>(?P<location>.*?)</a>',
        html_text,
        re.DOTALL,
    )
    updated_match = re.search(
        r'<p class="s-text-subtle mb-0">Sist oppdatert</p><p class="font-bold whitespace-nowrap mb-0 md:mt-8">(?P<updated>.*?)</p>',
        html_text,
        re.DOTALL,
    )
    postal_match = re.search(r'postalCode=(?P<postal>\d{4})', html_text)
    county_match = re.search(r'"key":"county","value":\["(?P<county>\d+)"\]', html_text)
    if not county_match:
        county_match = re.search(r'"key":"county","value":\["(?P<county>\d+)"\]', html.unescape(html_text))
    if not county_match:
        county_match = re.search(r'"key":"county","value":\["(?P<county>\d+)"\]', re.sub(r"\s+", "", html_text))
    if not county_match:
        county_match = re.search(r'"key":"county","value":\["(?P<county>\d+)"\]', re.sub(r"\s+", "", html.unescape(html_text)))
    if not county_match:
        county_match = re.search(r'"key":"county","value":\["(?P<county>\d+)"\]', html_text.replace(" ", ""))
    if not county_match:
        county_match = re.search(r'"county","value":\["(?P<county>\d+)"\]', html_text)

    return {
        "location_text": _clean_html_text(location_match.group("location")) if location_match else "",
        "updated_at": _clean_html_text(updated_match.group("updated")) if updated_match else "",
        "postal_code": postal_match.group("postal") if postal_match else "",
        "county_code": county_match.group("county") if county_match else _extract_county_code(html_text),
        "year": _extract_spec_value(html_text, "Modellår"),
        "km": _extract_spec_value(html_text, "Kilometerstand"),
    }


def load_alert_state(path: Path) -> set[str]:
    """Load previously seen FINN codes."""

    if not path.exists():
        return set()
    payload = json.loads(path.read_text())
    seen = payload.get("seen_finn_codes", [])
    if not isinstance(seen, list):
        raise ValueError("alert state missing seen_finn_codes list")
    return {str(value) for value in seen}


def save_alert_state(path: Path, seen_codes: set[str]) -> None:
    """Write alert state."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"seen_finn_codes": sorted(seen_codes)}, indent=2))


def format_listing(listing: SearchListing) -> str:
    """Render one listing as text."""

    parts = [
        listing.title,
        f"{listing.price_nok or '?'} NOK",
        f"year={listing.year or '?'}",
        f"km={listing.km or '?'}",
    ]
    if listing.location_text:
        parts.append(f"location={listing.location_text}")
    if listing.updated_at:
        parts.append(f"updated={listing.updated_at}")
    parts.append(listing.url)
    return " | ".join(parts)


def _matches_search(listing: SearchListing, search: ListingSearch) -> bool:
    query_text = normalize_text(" ".join(part for part in (listing.title, listing.subtitle) if part))
    if normalize_text(search.model) not in query_text:
        return False
    if search.year_from is not None and (listing.year is None or listing.year < search.year_from):
        return False
    if search.year_to is not None and (listing.year is None or listing.year > search.year_to):
        return False
    if search.km_max is not None and (listing.km is None or listing.km > search.km_max):
        return False
    if search.price_max is not None and (listing.price_nok is None or listing.price_nok > search.price_max):
        return False
    return True


def _matches_area(listing: SearchListing, normalized_areas: set[str]) -> bool:
    if not normalized_areas:
        return True
    haystack = {
        _normalize_area(listing.location_text),
        _normalize_area(listing.seller_text),
        _normalize_area(listing.postal_code),
        _normalize_area(listing.county_code),
    }
    location_text = _normalize_area(" ".join((listing.location_text, listing.seller_text)))
    for area in normalized_areas:
        if not area:
            continue
        if area in haystack:
            return True
        if area and area in location_text:
            return True
        if listing.county_code and area == listing.county_code:
            return True
        aliases = _COUNTY_ALIASES.get(area, ())
        if aliases and any(alias in location_text for alias in aliases):
            return True
    return False


def _dedupe_listings(listings: list[SearchListing]) -> list[SearchListing]:
    unique: list[SearchListing] = []
    seen: set[str] = set()
    for listing in listings:
        if listing.finn_code in seen:
            continue
        seen.add(listing.finn_code)
        unique.append(listing)
    return unique


def _listing_sort_key(listing: SearchListing) -> tuple[float, str]:
    if listing.updated_at:
        parsed = _parse_nb_datetime(listing.updated_at)
        if parsed is not None:
            return (-parsed.timestamp(), listing.finn_code)
    return (float("inf"), listing.finn_code)


def _parse_nb_datetime(value: str) -> datetime | None:
    months = {
        "januar": 1,
        "februar": 2,
        "mars": 3,
        "april": 4,
        "mai": 5,
        "juni": 6,
        "juli": 7,
        "august": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "desember": 12,
    }
    match = re.search(
        r'(?P<day>\d{1,2})\.\s+(?P<month>[a-zæøå]+)\s+(?P<year>\d{4}),\s+(?P<hour>\d{2}):(?P<minute>\d{2})',
        normalize_text(value),
    )
    if not match:
        return None
    month = months.get(match.group("month"))
    if month is None:
        return None
    return datetime(
        year=int(match.group("year")),
        month=month,
        day=int(match.group("day")),
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
    )


def _normalize_area(value: str) -> str:
    return normalize_text(value)


def _extract_tag_text(html_text: str, tag: str) -> str:
    match = re.search(rf"<{tag}[^>]*>.*?<a[^>]*>(?P<text>.*?)</a>.*?</{tag}>", html_text, re.DOTALL)
    if not match:
        return ""
    return _clean_html_text(match.group("text"))


def _extract_first_class_text(html_text: str, class_fragment: str) -> str:
    match = re.search(
        rf'<[^>]*class="[^"]*{re.escape(class_fragment)}[^"]*"[^>]*>(?P<text>.*?)</[^>]+>',
        html_text,
        re.DOTALL,
    )
    if not match:
        return ""
    return _clean_html_text(match.group("text"))


def _clean_html_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _extract_spec_value(html_text: str, label: str) -> int | None:
    match = re.search(rf">{re.escape(label)}</dt><dd[^>]*>(?P<value>.*?)</dd>", html_text, re.DOTALL)
    if not match:
        return None
    return parse_int(_clean_html_text(match.group("value")))


def _extract_county_code(html_text: str) -> str:
    match = re.search(r'"county","value":\["(?P<county>\d+)"\]', html_text)
    if match:
        return match.group("county")
    return ""
