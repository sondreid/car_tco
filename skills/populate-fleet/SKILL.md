---
name: populate-fleet
description: Build or update the user's local fleet file (reports/fleet.json) — the concrete used-car candidates to compare. Use this when the user wants to start a comparison, add a candidate listing, or refresh their shortlist. This file is personal experiment state and is never committed.
---

# Populate Fleet

The fleet file lists the concrete cars being compared: one entry per candidate
with price, year and km. `car-tco` uses `<output_dir>/fleet.json`
(default `reports/fleet.json`) when it exists, or a path given with `--fleet`;
otherwise it falls back to the small checked-in example fleet in
`car_tco/data/example_fleet.json`.

This is the intended way to start using the project: populate a local fleet
with the cars you are actually considering. An agent is practical for this,
not required — the file is plain JSON you can write by hand.

## Entry shape

```json
[
  {
    "name": "Toyota RAV4 Hybrid candidate",
    "description": "FINN listing under consideration",
    "model": "Toyota RAV4 Hybrid",
    "price_nok": 300000,
    "year": 2020,
    "model_year": 2020,
    "km": 120000,
    "url": "https://www.finn.no/mobility/item/..."
  }
]
```

- `model` must exist in `car_tco/data/models.json`. If it does not, run the
  `add-model` skill first.
- `model_year` is optional and defaults to `year`; set it when the listing
  year and the generation used for reliability lookup should differ.
- For a car the user already owns, use `existing_car: true`, `price_nok: 0`,
  `current_resale_value_nok`, optional `known_repairs_nok`, and
  `exclude_from_price_estimation: true`.

## Workflow

1. Ask the user for (or research on FINN.no) the candidate listings: model,
   price, year, km, and listing URL.
2. Check every model exists in `models.json`; run `add-model` for missing ones.
3. Write the entries to `reports/fleet.json` (or the user's chosen path).
4. Verify with `python -m car_tco --use-cached-scraped-price --no-output`.

## Rules

- Never commit the fleet file; `reports/` is gitignored on purpose.
- Use real listing values; do not invent prices or URLs.
- Keep one entry per concrete candidate, not per model.
