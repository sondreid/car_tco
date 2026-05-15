# Car Reliability Agent Notes

## Purpose

This repo compares used-car TCO for a Norwegian buyer.

The model combines:
- source-backed reliability
- maintenance and residual-value effects
- fuel or electricity cost
- optional FINN-based price estimation

## How To Use

- Run tests with `.venv/bin/python tests/run_tests.py`
- Run the default comparison with `.venv/bin/python -m car_tco --no-output`
- Run with live FINN pricing with `.venv/bin/python -m car_tco --scrape-prices --no-output`
- Reuse cached FINN prices with `.venv/bin/python -m car_tco --use-cached-scraped-prices --no-output`

## Design Choices

- Reliability is a ranking model, not a failure-probability model.
- Reliability inputs live in `car_tco/data/reliability.py`.
- Reliability now exposes a headline score plus a breakdown:
  - evidence score
  - technical-risk score
  - confidence score
  - age penalty
  - mileage penalty
- TCO inputs such as scheduled maintenance, residuals and consumption live in `car_tco/data/catalogue.py`.
- Maintenance is split into:
  - `scheduled_maintenance_nok`
  - `failure_risk_cost_nok`
- `Toyota Avensis` is modeled as an existing car:
  - `existing_car = True`
  - `price_nok = 0`
  - `current_resale_value_nok` captures what could be realized by selling now
  - `foregone_resale_value_nok` is charged as opportunity cost if the car is kept
  - `known_repairs_nok` is added on top of modeled maintenance
  - `exclude_from_price_estimation = True`
- FINN scraping is opt-in and should not be assumed stable.
- Live FINN pricing produces a typical comparable-market price, not a strict mean.
- Successful live scraping updates `reports/finn_price_cache.json`.
- Cache-only mode reads `reports/finn_price_cache.json` and sets `price_source = "finn_cached"`.
- If live scraping cannot find enough matches, the code falls back to the manual reference price.

## Adding Cars

There are two layers:

- model definition
- car instance

Model definitions live in:
- `car_tco/data/catalogue.py`
- `car_tco/data/reliability.py`

Car instances should normally be created with:
- `build_car("Model Name")`
- `build_car("Model Name", **overrides)`

Use the first form when you want the repo's canonical default reference car.
Use the second form when you want a specific listing or scenario variant.

Only add a new row to `car_tco/data/reference_fleet.py` when the car
should become part of the repo's default comparison set.

If the car should be scraped reliably, also add a profile in:
- `car_tco/pricing/finn.py`

## Constraints

- Keep Python changes simple and explicit.
- Prefer source-backed reliability inputs over invented scalars.
- If a model has mixed evidence or expensive downside faults, reflect that through:
  - `failure_cost_risk`
  - `evidence_confidence`
  - `known_failure_modes`
- Avoid hiding known one-off costs inside scheduled maintenance if they are already known.
