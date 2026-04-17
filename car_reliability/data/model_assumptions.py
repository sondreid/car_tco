"""Pricing model assumptions loaded from checked-in JSON."""

from __future__ import annotations

from dataclasses import dataclass

from ._json import load_json_data


@dataclass(frozen=True)
class PricingModelProfile:
    query: str
    required_groups: tuple[tuple[str, ...], ...]
    excluded_tokens: tuple[str, ...] = ()


def _build_pricing_profile(payload: dict) -> PricingModelProfile:
    return PricingModelProfile(
        query=str(payload["query"]),
        required_groups=tuple(
            tuple(str(token) for token in group)
            for group in payload["required_groups"]
        ),
        excluded_tokens=tuple(str(token) for token in payload.get("excluded_tokens", ())),
    )


def _load_pricing_profiles() -> dict[str, PricingModelProfile]:
    payload = load_json_data("model_assumptions.json")
    if not isinstance(payload, dict):
        raise ValueError("model_assumptions.json must contain an object")
    profiles_payload = payload.get("pricing_profiles")
    if not isinstance(profiles_payload, dict):
        raise ValueError("model_assumptions.json must contain a pricing_profiles object")
    return {
        model: _build_pricing_profile(profile_payload)
        for model, profile_payload in profiles_payload.items()
    }


PRICING_MODEL_PROFILES: dict[str, PricingModelProfile] = _load_pricing_profiles()
