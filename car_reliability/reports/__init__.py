"""
Report helpers: build DataFrames, write CSVs, print console summary.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..assumptions import Assumptions
from ..cost.tco import compute_tco

_SUMMARY_COLS = [
    "model",
    "reference_price_nok",
    "price_source",
    "price_match_count",
    "existing_car",
    "foregone_resale_value_nok",
    "reference_year",
    "reference_model_year",
    "reference_km",
    "reliability_score",
    "reliability_evidence_score",
    "technical_robustness",
    "reliability_confidence",
    "known_repairs_nok",
    "maintenance_nok",
    "energy_nok",
    "depreciation_nok",
    "investment_cost_nok",
    "total_cost_nok",
    "cost_per_month_nok",
]

_COL_LABELS = {
    "model": "Model",
    "reference_price_nok": "Price (NOK)",
    "price_source": "Price source",
    "price_match_count": "Price matches",
    "existing_car": "Existing car",
    "foregone_resale_value_nok": "Foregone resale (NOK)",
    "reference_year": "Year",
    "reference_model_year": "Model year",
    "reference_km": "Km",
    "reliability_score": "Reliability",
    "reliability_evidence_score": "Evidence",
    "technical_robustness": "Technical robustness",
    "reliability_confidence": "Confidence",
    "known_repairs_nok": "Known repairs (NOK)",
    "maintenance_nok": "Maint (NOK)",
    "energy_nok": "Energy (NOK)",
    "depreciation_nok": "Deprec. (NOK)",
    "investment_cost_nok": "Invest. (NOK)",
    "total_cost_nok": "Total (NOK)",
    "cost_per_month_nok": "NOK/mo",
}


def build_results_df(
    fleet: list[dict],
    assumptions: Assumptions | None = None,
) -> pd.DataFrame:
    """
    Run the TCO pipeline over every car in *fleet* and return a sorted
    DataFrame (cheapest total cost first).
    """
    if assumptions is None:
        assumptions = Assumptions()

    rows = [compute_tco(car, assumptions) for car in fleet]
    return pd.DataFrame(rows).sort_values("total_cost_nok").reset_index(drop=True)


def write_csv(
    df: pd.DataFrame,
    output_dir: str | Path = "reports",
    prefix: str = "tco",
) -> tuple[Path, Path]:
    """
    Write full and summary CSVs to *output_dir*.

    Returns
    -------
    (full_path, summary_path)
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    full_path = out / f"{prefix}_full.csv"
    summary_path = out / f"{prefix}_summary.csv"

    df.to_csv(full_path, index=False)

    summary = df[[c for c in _SUMMARY_COLS if c in df.columns]]
    summary.to_csv(summary_path, index=False)

    return full_path, summary_path


def print_summary(df: pd.DataFrame) -> None:
    """Print a human-readable summary table to stdout."""
    cols = [c for c in _SUMMARY_COLS if c in df.columns]
    summary = df[cols].rename(columns=_COL_LABELS)

    print(f"\n{'─' * 100}")
    print("  TCO Summary  (sorted by total cost, ascending)")
    print(f"{'─' * 100}")
    print(summary.to_string(index=False))
    print(f"{'─' * 100}\n")


__all__ = ["build_results_df", "write_csv", "print_summary"]
