"""Source-backed reliability inputs loaded from checked-in JSON."""

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
class ReliabilityYearObservation:
    """One year-specific reliability observation."""

    year: int
    profile: ReliabilityProfile


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


def _load_profiles() -> tuple[dict[str, ReliabilityProfile], dict[str, tuple[ReliabilityYearObservation, ...]]]:
    payload = load_json_data("reliability_profiles.json")
    if not isinstance(payload, dict):
        raise ValueError("reliability_profiles.json must contain an object")

    profiles_payload = payload.get("profiles")
    if not isinstance(profiles_payload, dict):
        raise ValueError("reliability_profiles.json must contain a profiles object")
    profiles = {
        model: _build_profile(profile_payload)
        for model, profile_payload in profiles_payload.items()
    }

    year_profiles_payload = payload.get("year_profiles", {})
    if not isinstance(year_profiles_payload, dict):
        raise ValueError("reliability_profiles.json year_profiles must be an object")
    year_profiles = {
        model: tuple(
            ReliabilityYearObservation(
                year=int(observation["year"]),
                profile=_build_profile(observation["profile"]),
            )
            for observation in observations
        )
        for model, observations in year_profiles_payload.items()
    }
    return profiles, year_profiles


RELIABILITY_PROFILES, RELIABILITY_YEAR_PROFILES = _load_profiles()


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
