"""FINN-based price estimation."""

from __future__ import annotations

from dataclasses import dataclass
import html
import json
from pathlib import Path
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
    comparable_subset_size: int = 6
    max_results: int = 50
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
    comparable_count: int
    used_fallback: bool
    notes: str = ""
    scraped_at: str = ""


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

        comparable_subset = select_nearest_comparables(matches, car, self.config)
        typical_price = median_price(comparable_subset)
        return FinnPriceEstimate(
            estimated_price_nok=typical_price,
            price_source="finn_typical",
            match_count=len(matches),
            comparable_count=len(comparable_subset),
            used_fallback=False,
            notes=(
                f"median of nearest {len(comparable_subset)} comparable listings "
                f"from {len(matches)} accepted matches"
            ),
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
            comparable_count=0,
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
    cache_mode: bool = False,
    cache_file: str | Path | None = None,
) -> list[dict]:
    """Return a fleet with estimated prices and price metadata."""

    import copy

    resolved = copy.deepcopy(fleet)
    cache_path = Path(cache_file) if cache_file is not None else Path("reports/finn_price_cache.json")
    cache = load_price_cache(cache_path) if cache_mode else {}
    service = estimator or FinnPriceEstimator(config=config)
    cache_updates: dict[str, dict] = {}
    for car in resolved:
        if car.get("exclude_from_price_estimation"):
            car["price_source"] = car.get("price_source", "existing_car")
            car["price_match_count"] = 0
            car["price_comparable_count"] = 0
            car["price_fallback_used"] = False
            car["price_note"] = car.get("price_note", "excluded from price estimation")
            continue
        if cache_mode:
            try:
                estimate = estimate_price_from_cache(car, cache)
            except KeyError as exc:
                raise KeyError(
                    f"{exc.args[0]} in {cache_path}. Run with --scrape-prices to populate the cache."
                ) from exc
        else:
            estimate = service.estimate_price(car)
            if estimate.price_source == "finn_typical":
                cache_updates[car["model"]] = build_cache_entry(car, estimate)
        if estimate.estimated_price_nok is not None:
            car["price_nok"] = float(estimate.estimated_price_nok)
        car["price_source"] = estimate.price_source
        car["price_match_count"] = estimate.match_count
        car["price_comparable_count"] = estimate.comparable_count
        car["price_fallback_used"] = estimate.used_fallback
        car["price_note"] = estimate.notes
    if not cache_mode and cache_updates:
        save_price_cache(cache_path, cache_updates)
    return resolved


def load_price_cache(path: Path) -> dict[str, dict]:
    """Load cached scraped prices."""

    if not path.exists():
        raise FileNotFoundError(f"price cache not found: {path}")
    payload = json.loads(path.read_text())
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        raise ValueError("price cache missing entries object")
    return entries


def save_price_cache(path: Path, entries: dict[str, dict]) -> None:
    """Write scraped price cache."""

    existing: dict[str, dict] = {}
    if path.exists():
        try:
            existing = load_price_cache(path)
        except Exception:
            existing = {}
    merged = dict(existing)
    merged.update(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"entries": merged}, indent=2, sort_keys=True)
    )


def build_cache_entry(car: dict, estimate: FinnPriceEstimate) -> dict:
    """Build one cache entry."""

    from datetime import datetime, UTC

    return {
        "model": car["model"],
        "estimated_price_nok": estimate.estimated_price_nok,
        "price_source": estimate.price_source,
        "match_count": estimate.match_count,
        "comparable_count": estimate.comparable_count,
        "price_note": estimate.notes,
        "reference_year": int(car["year"]),
        "reference_km": int(float(car["km"])),
        "scraped_at": datetime.now(UTC).isoformat(),
    }


def estimate_price_from_cache(car: dict, cache: dict[str, dict]) -> FinnPriceEstimate:
    """Estimate price from cache only."""

    model = car["model"]
    if model not in cache:
        raise KeyError(f"missing cached scraped price for {model}")
    entry = cache[model]
    if entry.get("reference_year") != int(car["year"]) or entry.get("reference_km") != int(float(car["km"])):
        raise ValueError(f"cached scraped price for {model} does not match reference year/km")
    return FinnPriceEstimate(
        estimated_price_nok=int(entry["estimated_price_nok"]),
        price_source="finn_cached",
        match_count=int(entry.get("match_count", 0)),
        comparable_count=int(entry.get("comparable_count", 0)),
        used_fallback=False,
        notes=entry.get("price_note", ""),
        scraped_at=entry.get("scraped_at", ""),
    )


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


def select_nearest_comparables(
    matches: list[FinnListing],
    car: dict,
    config: PriceEstimatorConfig,
) -> list[FinnListing]:
    """Return the nearest comparable listings within the accepted match set."""

    target_year = int(car["year"])
    target_km = int(float(car["km"]))

    def distance(listing: FinnListing) -> tuple[float, int, int, int]:
        year_delta = abs((listing.year or target_year) - target_year)
        km_delta = abs((listing.km or target_km) - target_km)
        normalized_km = km_delta / max(config.km_tolerance, 1)
        return (year_delta + normalized_km, year_delta, km_delta, listing.price_nok)

    ranked = sorted(matches, key=distance)
    return ranked[: min(config.comparable_subset_size, len(ranked))]


def median_price(listings: list[FinnListing]) -> int:
    """Return median price from listing set."""

    prices = sorted(item.price_nok for item in listings)
    mid = len(prices) // 2
    if len(prices) % 2:
        return prices[mid]
    return round((prices[mid - 1] + prices[mid]) / 2)


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
