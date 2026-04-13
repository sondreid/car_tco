"""Source-backed reliability inputs."""

from __future__ import annotations

from dataclasses import dataclass


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


RELIABILITY_PROFILES: dict[str, ReliabilityProfile] = {
    "Mercedes EQC": ReliabilityProfile(
        survey_score=83.0,
        owner_score=81.0,
        complexity_risk=14,
        failure_cost_risk=10,
        evidence_confidence=66.0,
        known_failure_modes=("high-voltage systems", "air suspension/electronics", "premium EV ancillaries"),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/mercedes-benz/eqc/4x4/used-review/n23007/reliability",
                summary="EQC was not in the latest survey; Mercedes brand placed 22nd of 31 manufacturers.",
            ),
        ),
    ),
    "Mazda CX-5 diesel AWD": ReliabilityProfile(
        survey_score=88.5,
        owner_score=84.0,
        complexity_risk=9,
        failure_cost_risk=7,
        evidence_confidence=79.0,
        known_failure_modes=("DPF", "injectors", "exhaust/emissions ancillaries"),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/mazda/cx-5/estate/used-review/n947/reliability",
                summary="Diesel CX-5 scored 88.5% with DPF and exhaust-related complaints noted.",
            ),
        ),
    ),
    "Peugeot 508 SW 2.0 BlueHDi": ReliabilityProfile(
        survey_score=79.0,
        owner_score=76.0,
        complexity_risk=9,
        failure_cost_risk=8,
        evidence_confidence=60.0,
        known_failure_modes=("electrics", "diesel emissions hardware", "older French estate ancillaries"),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/peugeot/508/estate/used-review/n859/reliability",
                summary="Older 508 SW was not included in the survey; Peugeot brand result was poor and electrical issues were noted.",
            ),
        ),
    ),
    "Skoda Kodiaq 2.0 TDI 4x4": ReliabilityProfile(
        survey_score=94.7,
        owner_score=90.0,
        complexity_risk=12,
        failure_cost_risk=7,
        evidence_confidence=86.0,
        known_failure_modes=("electrics", "EGR/DPF", "AWD/diesel ancillaries"),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/skoda/kodiaq/estate/used-review/n954/reliability",
                summary="Diesel Kodiaq scored 94.7% and finished fourth in class, with mainly electrical and exhaust issues.",
            ),
        ),
    ),
    "Tesla Model Y": ReliabilityProfile(
        survey_score=97.1,
        owner_score=90.0,
        complexity_risk=8,
        failure_cost_risk=6,
        evidence_confidence=80.0,
        known_failure_modes=("build quality", "suspension/wear items", "electronics/trim"),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/tesla/model-y/estate/used-review/n25945/reliability",
                summary="Model Y scored 97.1% and finished third of 27 electric SUVs, with build-quality complaints more common than drivetrain faults.",
            ),
        ),
    ),
    "Toyota Avensis": ReliabilityProfile(
        survey_score=94.0,
        owner_score=90.0,
        complexity_risk=5,
        failure_cost_risk=4,
        evidence_confidence=58.0,
        known_failure_modes=("generic assumption",),
        sources=(
            ReliabilitySource(
                publisher="Model assumption",
                url="",
                summary="Generic Avensis assumption pending exact year and engine.",
            ),
        ),
    ),
    "Toyota RAV4 Hybrid": ReliabilityProfile(
        survey_score=99.2,
        owner_score=98.0,
        complexity_risk=6,
        failure_cost_risk=3,
        evidence_confidence=95.0,
        known_failure_modes=("minor trim/electrics",),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/toyota/rav4/4x4/used-review/n22427/reliability",
                summary="99.2% reliability score and only 2% of owners reporting faults.",
            ),
        ),
    ),
    "Mitsubishi Outlander PHEV": ReliabilityProfile(
        survey_score=86.0,
        owner_score=84.0,
        complexity_risk=10,
        failure_cost_risk=9,
        evidence_confidence=72.0,
        known_failure_modes=("battery degradation", "charger/BMS", "PHEV control systems"),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/mitsubishi/outlander/4x4/used-review/n769/reliability",
                summary="PHEV placed 13th of 14 hybrids in the survey, despite Mitsubishi brand strength.",
            ),
            ReliabilitySource(
                publisher="Electrifying",
                url="https://www.electrifying.com/used-reviews/mitsubishi/outlander-phev/review",
                summary="Used-buyer guide is materially more positive than the What Car? ranking.",
            ),
        ),
    ),
    "Volkswagen Passat GTE": ReliabilityProfile(
        survey_score=82.2,
        owner_score=78.0,
        complexity_risk=15,
        failure_cost_risk=11,
        evidence_confidence=82.0,
        known_failure_modes=("DSG", "hybrid control", "electrical/software"),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/volkswagen/passat-gte/estate/used-review/n18007/reliability",
                summary="82.2% reliability score and 19th of 20 executive cars.",
            ),
        ),
    ),
    "Skoda Superb 2.0 TDI 4x4": ReliabilityProfile(
        survey_score=98.0,
        owner_score=88.0,
        complexity_risk=14,
        failure_cost_risk=8,
        evidence_confidence=84.0,
        known_failure_modes=("EGR/DPF", "injectors", "diesel AWD ancillaries"),
        sources=(
            ReliabilitySource(
                publisher="What Car?",
                url="https://www.whatcar.com/skoda/superb/estate/used-review/n916/reliability",
                summary="Diesel estate counterpart ranked near the top of the class with a 98% score.",
            ),
        ),
    ),
}
