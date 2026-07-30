"""Per-model definitions loaded from checked-in models.json.

Each entry holds the catalogue data, the optional FINN pricing profile and
the reliability evidence for one car model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._json import load_json_data


@dataclass(frozen=True)
class PricingModelProfile:
    """FINN search and matching profile for one model."""

    query: str
    required_groups: tuple[tuple[str, ...], ...]
    excluded_tokens: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReliabilitySource:
    """One external reliability reference."""

    publisher: str
    url: str
    summary: str


@dataclass(frozen=True)
class ReliabilityProfile:
    """Reliability inputs for one model."""

    survey_score: float
    owner_score: float
    complexity_risk: int
    failure_cost_risk: int
    evidence_confidence: float
    known_failure_modes: tuple[str, ...]
    sources: tuple[ReliabilitySource, ...]


@dataclass(frozen=True)
class ReliabilityProfileMetadata:
    """Provenance metadata for one reliability entry."""

    status: str
    generated_by: str
    generated_at: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None


@dataclass(frozen=True)
class ReliabilityYearObservation:
    """One year-specific reliability observation."""

    year: int
    profile: ReliabilityProfile
    metadata: ReliabilityProfileMetadata


def _build_pricing_profile(payload: dict) -> PricingModelProfile:
    return PricingModelProfile(
        query=str(payload["query"]),
        required_groups=tuple(
            tuple(str(token) for token in group)
            for group in payload["required_groups"]
        ),
        excluded_tokens=tuple(str(token) for token in payload.get("excluded_tokens", ())),
    )


def _build_metadata(payload: dict) -> ReliabilityProfileMetadata:
    return ReliabilityProfileMetadata(
        status=str(payload["status"]),
        generated_by=str(payload["generated_by"]),
        generated_at=str(payload["generated_at"]),
        reviewed_by=(
            str(payload["reviewed_by"])
            if payload.get("reviewed_by") is not None
            else None
        ),
        reviewed_at=(
            str(payload["reviewed_at"])
            if payload.get("reviewed_at") is not None
            else None
        ),
    )


def _build_source(payload: dict) -> ReliabilitySource:
    return ReliabilitySource(
        publisher=str(payload["publisher"]),
        url=str(payload["url"]),
        summary=str(payload["summary"]),
    )


def _build_profile(payload: dict) -> ReliabilityProfile:
    return ReliabilityProfile(
        survey_score=float(payload["survey_score"]),
        owner_score=float(payload["owner_score"]),
        complexity_risk=int(payload["complexity_risk"]),
        failure_cost_risk=int(payload["failure_cost_risk"]),
        evidence_confidence=float(payload["evidence_confidence"]),
        known_failure_modes=tuple(str(mode) for mode in payload["known_failure_modes"]),
        sources=tuple(_build_source(source) for source in payload["sources"]),
    )


def _build_year_observations(payloads: list) -> tuple[ReliabilityYearObservation, ...]:
    return tuple(
        ReliabilityYearObservation(
            year=int(observation["year"]),
            profile=_build_profile(observation["profile"]),
            metadata=_build_metadata(observation["metadata"]),
        )
        for observation in payloads
    )


def _load_models() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, PricingModelProfile],
    dict[str, ReliabilityProfile],
    dict[str, ReliabilityProfileMetadata],
    dict[str, tuple[ReliabilityYearObservation, ...]],
]:
    payload = load_json_data("models.json")
    if not isinstance(payload, dict):
        raise ValueError("models.json must contain an object keyed by model name")

    catalogue: dict[str, dict[str, Any]] = {}
    pricing_profiles: dict[str, PricingModelProfile] = {}
    reliability_profiles: dict[str, ReliabilityProfile] = {}
    reliability_metadata: dict[str, ReliabilityProfileMetadata] = {}
    year_profiles: dict[str, tuple[ReliabilityYearObservation, ...]] = {}

    for model, entry in payload.items():
        if not isinstance(entry, dict):
            raise ValueError(f"models.json entry for {model!r} must be an object")
        if not isinstance(entry.get("catalogue"), dict):
            raise ValueError(f"models.json entry for {model!r} must contain a catalogue object")
        reliability = entry.get("reliability")
        if not isinstance(reliability, dict):
            raise ValueError(f"models.json entry for {model!r} must contain a reliability object")

        catalogue[model] = entry["catalogue"]
        if "pricing_profile" in entry:
            pricing_profiles[model] = _build_pricing_profile(entry["pricing_profile"])
        reliability_profiles[model] = _build_profile(reliability["profile"])
        reliability_metadata[model] = _build_metadata(reliability["metadata"])
        if "year_profiles" in reliability:
            year_profiles[model] = _build_year_observations(reliability["year_profiles"])

    return catalogue, pricing_profiles, reliability_profiles, reliability_metadata, year_profiles


(
    CAR_CATALOGUE,
    PRICING_MODEL_PROFILES,
    RELIABILITY_PROFILES,
    RELIABILITY_PROFILE_METADATA,
    RELIABILITY_YEAR_PROFILES,
) = _load_models()


def resolve_reliability_profile(
    model: str,
    model_year: int | None = None,
) -> ReliabilityProfile:
    """Return the best reliability profile for a model and optional model year."""

    observations = RELIABILITY_YEAR_PROFILES.get(model, ())
    if model_year is not None and observations:
        return min(
            observations,
            key=lambda observation: (abs(observation.year - model_year), observation.year),
        ).profile
    return RELIABILITY_PROFILES[model]
