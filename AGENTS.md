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
- Run the default comparison with `.venv/bin/python -m car_reliability --no-output`
- Run with FINN pricing with `.venv/bin/python -m car_reliability --scrape-prices --no-output`

## Design Choices

- Reliability is a ranking model, not a failure-probability model.
- Reliability inputs live in `car_reliability/data/reliability.py`.
- TCO inputs such as maintenance, residuals and consumption live in `car_reliability/data/catalogue.py`.
- `Toyota Avensis` is modeled as an existing car:
  - `price_nok = 0`
  - `known_repairs_nok` is added on top of modeled maintenance
  - `exclude_from_price_estimation = True`
- FINN scraping is opt-in and should not be assumed stable.
- If scraping cannot find enough matches, the code falls back to the manual reference price.

## Adding Cars

Add entries in:
- `car_reliability/data/catalogue.py`
- `car_reliability/data/reliability.py`
- `car_reliability/data/reference_fleet.py`

If the car should be scraped reliably, also add a profile in:
- `car_reliability/pricing/finn.py`

## Constraints

- Keep Python changes simple and explicit.
- Prefer source-backed reliability inputs over invented scalars.
- If a model has mixed evidence or expensive downside faults, reflect that through:
  - `failure_cost_risk`
  - `evidence_uncertainty`
- Avoid hiding known one-off costs inside generic base maintenance if they are already known.
