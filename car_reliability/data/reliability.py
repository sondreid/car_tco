"""LLM-fillable reliability evidence loaded from checked-in JSON."""

from __future__ import annotations

from dataclasses import dataclass

from ._json import load_json_data


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
    """Metadata for one fillable reliability entry."""

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


def _build_profile_entry(payload: dict) -> tuple[ReliabilityProfileMetadata, ReliabilityProfile]:
    metadata_payload = payload.get("metadata")
    profile_payload = payload.get("profile")
    if metadata_payload is None and profile_payload is None:
        metadata_payload = {
            "status": "legacy",
            "generated_by": "unknown",
            "generated_at": "",
            "reviewed_by": None,
            "reviewed_at": None,
        }
        profile_payload = payload
    if not isinstance(metadata_payload, dict):
        raise ValueError("reliability entry metadata must be an object")
    if not isinstance(profile_payload, dict):
        raise ValueError("reliability entry profile must be an object")
    return _build_metadata(metadata_payload), _build_profile(profile_payload)


def _load_profiles() -> tuple[
    dict[str, ReliabilityProfile],
    dict[str, ReliabilityProfileMetadata],
    dict[str, tuple[ReliabilityYearObservation, ...]],
]:
    payload = load_json_data("reliability_profiles.json")
    if not isinstance(payload, dict):
        raise ValueError("reliability_profiles.json must contain an object")

    profiles_payload = payload.get("profiles")
    if not isinstance(profiles_payload, dict):
        raise ValueError("reliability_profiles.json must contain a profiles object")
    profiles: dict[str, ReliabilityProfile] = {}
    profile_metadata: dict[str, ReliabilityProfileMetadata] = {}
    for model, profile_payload in profiles_payload.items():
        metadata, profile = _build_profile_entry(profile_payload)
        profiles[model] = profile
        profile_metadata[model] = metadata

    year_profiles_payload = payload.get("year_profiles", {})
    if not isinstance(year_profiles_payload, dict):
        raise ValueError("reliability_profiles.json year_profiles must be an object")
    year_profiles: dict[str, tuple[ReliabilityYearObservation, ...]] = {}
    for model, observations in year_profiles_payload.items():
        resolved_observations: list[ReliabilityYearObservation] = []
        for observation in observations:
            metadata, profile = _build_profile_entry(observation)
            resolved_observations.append(
                ReliabilityYearObservation(
                    year=int(observation["year"]),
                    profile=profile,
                    metadata=metadata,
                )
            )
        year_profiles[model] = tuple(resolved_observations)
    return profiles, profile_metadata, year_profiles


RELIABILITY_PROFILES, RELIABILITY_PROFILE_METADATA, RELIABILITY_YEAR_PROFILES = _load_profiles()


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
