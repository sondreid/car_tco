"""FINN-based price estimation."""

from __future__ import annotations

from dataclasses import dataclass
import html
import json
import re
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen


_SEARCH_URL = "https://www.finn.no/mobility/search/car"
_GLOBAL_EXCLUDED_TOKENS = (
    "delebil",
    "rep.objekt",
    "repobjekt",
    "dele bil",
    "defekt",
    "motorhavari",
    "krasj",
    "crash",
    "salvage",
)


@dataclass(frozen=True)
class PriceEstimatorConfig:
    """Config for scraped price estimates."""

    source: str = "finn"
    year_tolerance: int = 1
    km_tolerance: int = 20_000
    min_matches: int = 2
    max_results: int = 30
    request_timeout_seconds: float = 15.0
    fallback_to_reference_price: bool = True


@dataclass(frozen=True)
class FinnListing:
    """Normalized FINN listing."""

    title: str
    description: str
    price_nok: int
    year: int | None
    km: int | None
    url: str
    source: str = "finn"

    @property
    def combined_text(self) -> str:
        return normalize_text(" ".join((self.title, self.description)))


@dataclass(frozen=True)
class FinnPriceEstimate:
    """Price estimate for one car."""

    estimated_price_nok: int | None
    price_source: str
    match_count: int
    used_fallback: bool
    notes: str = ""


@dataclass(frozen=True)
class _ModelProfile:
    query: str
    required_groups: tuple[tuple[str, ...], ...]
    excluded_tokens: tuple[str, ...] = ()


_MODEL_PROFILES: dict[str, _ModelProfile] = {
    "Mercedes EQC": _ModelProfile(
        query="mercedes eqc",
        required_groups=(("eqc",),),
        excluded_tokens=("eqe", "eqs"),
    ),
    "Mazda CX-5 diesel AWD": _ModelProfile(
        query="mazda cx-5 diesel awd",
        required_groups=(("cx 5", "cx-5"), ("diesel", "2 2d", "2.2d"), ("awd", "4x4")),
        excluded_tokens=("petrol", "bensin"),
    ),
    "Peugeot 508 SW 2.0 BlueHDi": _ModelProfile(
        query="peugeot 508 sw bluehdi",
        required_groups=(("508",), ("sw",), ("bluehdi",)),
        excluded_tokens=("hybrid", "phev"),
    ),
    "Skoda Kodiaq 2.0 TDI 4x4": _ModelProfile(
        query="skoda kodiaq 2.0 tdi 4x4",
        required_groups=(("kodiaq",), ("tdi",), ("4x4", "4wd")),
        excluded_tokens=("tsi", "petrol", "bensin"),
    ),
    "Tesla Model Y": _ModelProfile(
        query="tesla model y",
        required_groups=(("model y",),),
        excluded_tokens=("model s", "model 3", "model x"),
    ),
    "Toyota RAV4 Hybrid": _ModelProfile(
        query="toyota rav4 hybrid",
        required_groups=(("rav4",), ("hybrid",)),
        excluded_tokens=("plug-in", "plug in", "phev", "ladbar"),
    ),
    "Mitsubishi Outlander PHEV": _ModelProfile(
        query="mitsubishi outlander phev",
        required_groups=(("outlander",), ("phev", "plug-in", "plug in", "hybrid")),
        excluded_tokens=("diesel", "di-d"),
    ),
    "Volkswagen Passat GTE": _ModelProfile(
        query="volkswagen passat gte",
        required_groups=(("passat",), ("gte",)),
        excluded_tokens=("tdi", "diesel"),
    ),
    "Skoda Superb 2.0 TDI 4x4": _ModelProfile(
        query="skoda superb tdi 4x4",
        required_groups=(("superb",), ("tdi",), ("4x4", "4wd")),
        excluded_tokens=("iv",),
    ),
}


class FinnPriceEstimator:
    """Estimate prices from FINN used-car listings."""

    def __init__(
        self,
        config: PriceEstimatorConfig | None = None,
        fetcher: callable | None = None,
    ) -> None:
        self.config = config or PriceEstimatorConfig()
        self._fetcher = fetcher or self._default_fetcher

    def estimate_price(self, car: dict) -> FinnPriceEstimate:
        model = car["model"]
        reference_price = int(float(car["price_nok"]))
        profile = _MODEL_PROFILES.get(model, build_generic_profile(model))

        try:
            search_html = self._fetcher(self._build_search_url(profile.query))
            search_listings = parse_search_results(search_html, max_results=self.config.max_results)
        except Exception as exc:
            return self._fallback(reference_price, f"search failed: {exc}")

        matches: list[FinnListing] = []
        for listing in search_listings:
            if not is_listing_candidate(listing, car, profile):
                continue
            try:
                detail_html = self._fetcher(listing.url)
            except Exception:
                continue
            detail = parse_detail_page(detail_html)
            candidate = FinnListing(
                title=listing.title,
                description=listing.description,
                price_nok=detail.get("price_nok") or listing.price_nok,
                year=detail.get("year"),
                km=detail.get("km"),
                url=listing.url,
            )
            if is_listing_match(candidate, car, profile, self.config):
                matches.append(candidate)

        if len(matches) < self.config.min_matches:
            note = f"matched {len(matches)} listings"
            return self._fallback(reference_price, note, match_count=len(matches))

        mean_price = round(sum(item.price_nok for item in matches) / len(matches))
        return FinnPriceEstimate(
            estimated_price_nok=mean_price,
            price_source="finn_mean",
            match_count=len(matches),
            used_fallback=False,
            notes=f"mean of {len(matches)} FINN listings",
        )

    def _build_search_url(self, query: str) -> str:
        return f"{_SEARCH_URL}?{urlencode({'q': query})}"

    def _fallback(
        self,
        reference_price: int,
        note: str,
        match_count: int = 0,
    ) -> FinnPriceEstimate:
        estimate = reference_price if self.config.fallback_to_reference_price else None
        return FinnPriceEstimate(
            estimated_price_nok=estimate,
            price_source="manual",
            match_count=match_count,
            used_fallback=True,
            notes=note,
        )

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
        with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
            return response.read().decode("utf-8")


def estimate_fleet_prices(
    fleet: list[dict],
    config: PriceEstimatorConfig | None = None,
    estimator: FinnPriceEstimator | None = None,
) -> list[dict]:
    """Return a fleet with estimated prices and price metadata."""

    import copy

    resolved = copy.deepcopy(fleet)
    service = estimator or FinnPriceEstimator(config=config)
    for car in resolved:
        if car.get("exclude_from_price_estimation"):
            car["price_source"] = car.get("price_source", "existing_car")
            car["price_match_count"] = 0
            car["price_fallback_used"] = False
            car["price_note"] = car.get("price_note", "excluded from price estimation")
            continue
        estimate = service.estimate_price(car)
        if estimate.estimated_price_nok is not None:
            car["price_nok"] = float(estimate.estimated_price_nok)
        car["price_source"] = estimate.price_source
        car["price_match_count"] = estimate.match_count
        car["price_fallback_used"] = estimate.used_fallback
        car["price_note"] = estimate.notes
    return resolved


def parse_search_results(html_text: str, max_results: int) -> list[FinnListing]:
    """Parse FINN search page structured data."""

    match = re.search(
        r'<script id="seoStructuredData" type="application/ld\+json">(?P<json>.*?)</script>',
        html_text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("search structured data not found")

    payload = json.loads(html.unescape(match.group("json")))
    items = payload.get("mainEntity", {}).get("itemListElement", [])
    listings: list[FinnListing] = []
    for entry in items[:max_results]:
        item = entry.get("item", {})
        offers = item.get("offers", {})
        price = parse_int(str(offers.get("price", "")))
        url = item.get("url")
        if price is None or not url:
            continue
        listings.append(
            FinnListing(
                title=item.get("name", ""),
                description=item.get("description", ""),
                price_nok=price,
                year=None,
                km=None,
                url=url,
            )
        )
    return listings


def parse_detail_page(html_text: str) -> dict[str, int | None]:
    """Parse year, km and price from an item page."""

    return {
        "year": _extract_target_value(html_text, "year") or _extract_spec_value(html_text, "Modellår"),
        "km": _extract_target_value(html_text, "mileage")
        or _extract_spec_value(html_text, "Kilometerstand"),
        "price_nok": _extract_target_value(html_text, "price")
        or _extract_ld_json_price(html_text),
    }


def is_listing_candidate(listing: FinnListing, car: dict, profile: _ModelProfile) -> bool:
    """Apply summary-level text filtering before fetching detail pages."""

    text = listing.combined_text
    if any(token in text for token in _GLOBAL_EXCLUDED_TOKENS):
        return False
    if any(token in text for token in profile.excluded_tokens):
        return False
    return all(any(token in text for token in group) for group in profile.required_groups)


def is_listing_match(
    listing: FinnListing,
    car: dict,
    profile: _ModelProfile,
    config: PriceEstimatorConfig,
) -> bool:
    """Apply full comparability rules."""

    if listing.year is None or listing.km is None:
        return False
    if abs(listing.year - int(car["year"])) > config.year_tolerance:
        return False
    if abs(listing.km - int(float(car["km"]))) > config.km_tolerance:
        return False
    text = listing.combined_text
    if any(token in text for token in profile.excluded_tokens):
        return False
    return all(any(token in text for token in group) for group in profile.required_groups)


def build_generic_profile(model: str) -> _ModelProfile:
    """Build a permissive profile for models without a custom mapping."""

    normalized = normalize_text(model)
    query = " ".join(part for part in normalized.split() if len(part) > 2)
    tokens = tuple((part,) for part in query.split()[:2]) or ((normalized,),)
    return _ModelProfile(query=query, required_groups=tokens)


def normalize_text(value: str) -> str:
    """Normalize text for token matching."""

    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_int(value: str) -> int | None:
    """Parse a localized integer."""

    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return None
    return int(digits)


def _extract_target_value(html_text: str, key: str) -> int | None:
    pattern = rf'"key":"{re.escape(key)}","value":\["(?P<value>[^"]+)"\]'
    match = re.search(pattern, html_text)
    if not match:
        return None
    return parse_int(match.group("value"))


def _extract_spec_value(html_text: str, label: str) -> int | None:
    pattern = (
        rf">{re.escape(label)}</dt><dd[^>]*>"
        rf"(?P<value>.*?)</dd>"
    )
    match = re.search(pattern, html_text, re.DOTALL)
    if not match:
        return None
    return parse_int(html.unescape(match.group("value")))


def _extract_ld_json_price(html_text: str) -> int | None:
    match = re.search(r'"price"\s*:\s*(?P<price>\d+)', html_text)
    if not match:
        return None
    return int(match.group("price"))
