# Car TCO Agent Notes

## Purpose

This repo compares used-car TCO for a Norwegian buyer.

The model combines:
- source-backed reliability
- maintenance and residual-value effects
- fuel or electricity cost
- optional FINN-based price estimation

## How To Use

- Run tests with `python tests/run_tests.py`
- Run the default comparison with `python -m car_tco --no-output`
- Run with live FINN pricing with `python -m car_tco --scrape-prices --no-output`
- Reuse cached FINN prices with `python -m car_tco --use-cached-scraped-price --no-output`
- Validate model data with `python skills/add-model/scripts/validate_models.py`

## Data Layout

- `car_tco/data/models.json` holds all per-model definitions:
  catalogue (consumption, residual, maintenance), optional FINN pricing
  profile, and reliability evidence with provenance metadata.
- `car_tco/data/models.py` loads that file and exposes `CAR_CATALOGUE`,
  `PRICING_MODEL_PROFILES`, `RELIABILITY_PROFILES` and
  `resolve_reliability_profile`.
- `car_tco/data/reference_fleet.json` holds the default comparison instances
  (price, year, km); `build_car()` copies and patches them.
- Everything under `reports/` is generated output, never configuration.

## Design Choices

- Reliability is a ranking model, not a failure-probability model.
- Reliability exposes a headline score plus a breakdown: evidence score,
  technical-risk score, confidence score, age penalty, mileage penalty.
- Maintenance is split into `scheduled_maintenance_nok` and
  `failure_risk_cost_nok`.
- An already-owned car is modeled with `existing_car = True`, `price_nok = 0`,
  `current_resale_value_nok` (keep-versus-sell opportunity cost) and
  `known_repairs_nok`; see the Toyota Avensis example in the fleet.
- FINN scraping is opt-in and should not be assumed stable. It produces a
  typical comparable-market price (median of nearest matches), not a mean,
  and falls back to the manual reference price when matches are thin.

## Adding Cars

Two layers:

- Model definition: one entry in `car_tco/data/models.json`.
  Use the `skills/add-model` skill to have an agent research and populate it —
  optional but practical. Schema: `skills/add-model/references/models-json.md`.
- Car instance: `build_car("Model Name", **overrides)`. Only add a row to
  `reference_fleet.json` when the car belongs in the default comparison set.

## Constraints

- Keep Python changes simple and explicit.
- Prefer source-backed reliability inputs over invented scalars.
- If a model has mixed evidence or expensive downside faults, reflect that
  through `failure_cost_risk`, `evidence_confidence` and
  `known_failure_modes`.
- Avoid hiding known one-off costs inside scheduled maintenance if they are
  already known.
