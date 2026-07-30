# car_tco

Python package for comparing used cars on 3-year Total Cost of Ownership (TCO)
and a composite reliability score, built for the Norwegian market.

The reliability model is a structured scorecard: an evidence score, a technical
robustness score, an evidence-confidence score, and age/mileage penalties.
Maintenance is split into scheduled maintenance and failure-risk cost.
Prices can be estimated live from FINN.no listings.

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

```bash
# Refresh FINN prices, rerun the model, write CSVs and caches to reports/
car-tco

# Reuse cached FINN prices and rerun reliability + TCO
car-tco --use-cached-scraped-price

# Custom scenario
car-tco --petrol 25.0 --annual-km 20000 --years 4

# Print only, no file output
car-tco --no-output
```

```python
from car_tco.pipeline import RunMode, run
from car_tco.assumptions import Assumptions
from car_tco.data import build_car

# Default scenario from checked-in reference data (no scraping)
df = run()

# Custom scenario
df = run(
    assumptions=Assumptions(annual_km=20_000, horizon_years=4, charge_share=0.25),
    price_overrides={"Toyota RAV4 Hybrid": 260_000},
)

# Refresh FINN prices and rerun everything
df = run(mode=RunMode.RERUN_MODEL)

# Compare against a car you already own (keep-versus-sell)
df = run(
    extra_cars=[
        build_car(
            "Toyota Avensis",
            existing_car=True,
            price_nok=0,
            current_resale_value_nok=20_000,
            known_repairs_nok=50_000,
            exclude_from_price_estimation=True,
        )
    ]
)
```

## How data is organized

There are two layers, and two files:

1. **Model definitions — `car_tco/data/models.json`**
   One entry per car model, holding everything the model needs:
   - `catalogue`: consumption, residual value base, scheduled maintenance
   - `pricing_profile`: FINN search query and matching rules (optional)
   - `reliability`: source-backed scores, failure modes, evidence with metadata

2. **Car instances — `car_tco/data/reference_fleet.json`**
   The default comparison fleet: one concrete car per model with price, year
   and km. Instances are built with `build_car("Model Name", **overrides)`;
   omitted fields fall back to the reference instance.

All other JSON files (`reports/*.json`) are generated caches and overrides —
they are not configuration and are not checked in.

## Adding a car model

Add an entry to `models.json` (and optionally `reference_fleet.json`), then run
the tests. The `skills/add-model` skill lets a coding agent (Claude Code, Codex,
etc.) research and populate the entry for you — practical, but not required;
hand-editing the JSON works exactly the same. The schema is documented in
[`skills/add-model/references/models-json.md`](skills/add-model/references/models-json.md).

Validate with:

```bash
python skills/add-model/scripts/validate_models.py
python tests/run_tests.py
```

## Package layout

```
car_tco/
├── assumptions.py        ← All toggleable parameters (single source of truth)
├── pipeline.py           ← High-level run() entry point
├── cli.py                ← argparse CLI (car-tco command)
├── cache_store.py        ← Shared JSON cache reader/writer
├── overrides.py          ← Manual per-car override loading and precedence
├── data/
│   ├── models.json           ← Per-model definitions (catalogue, pricing, reliability)
│   ├── models.py             ← Loader and dataclasses for models.json
│   ├── reference_fleet.json  ← Default comparison fleet (instances)
│   └── reference_fleet.py    ← Fleet helpers and build_car()
├── scoring/reliability.py    ← Composite reliability score
├── cost/                     ← energy, maintenance, depreciation, tco assembly
├── pricing/finn.py           ← FINN scraping, matching, price cache
└── reports/                  ← print/CSV output helpers
skills/
└── add-model/                ← Agent skill to research + populate a model entry
```

## Key assumptions (`Assumptions`)

| Field | Default | Description |
|---|---|---|
| `annual_km` | 15 000 | km/year |
| `horizon_years` | 3 | Ownership horizon |
| `petrol_nok_per_l` | 23.0 | NOK per litre petrol |
| `diesel_nok_per_l` | 22.0 | NOK per litre diesel |
| `electricity_nok_per_kwh` | 1.5 | NOK per kWh |
| `capital_rate` | 0.04 | Opportunity cost rate |
| `charge_share` | 0.50 | Fraction of PHEV trips starting fully charged |
| `weight_evidence` | 0.55 | Weight of evidence score |
| `weight_technical_risk` | 0.30 | Weight of technical-risk score |
| `weight_confidence` | 0.15 | Weight of evidence confidence |

See `car_tco/assumptions.py` for the full list, including PHEV blending, age and
mileage penalties, and residual-value sensitivities.

## Run modes

- default / `--rerun-model`: refresh FINN prices, recompute everything
- `--scrape-prices`: refresh only the FINN price cache
- `--use-cached-scraped-price`: reuse cached prices, rerun reliability + TCO
- `--use-cached-reliability`: reuse cached reliability, rerun cost layers
- `--use-cached`: reuse the full cached result

The Python API's `run()` stays conservative: it recomputes from checked-in data
without scraping unless you pass an explicit `RunMode`.

## FINN price estimation

The estimator filters listings to the expected model and a year/km window,
ranks accepted listings by closeness to the target, and uses the median price
of the nearest comparable subset. Results are cached in
`<output_dir>/finn_price_cache.json`; caches are keyed by model, year,
model year and km, so different model-year experiments cache separately.

## Manual overrides

The pipeline writes an `overrides_example.json` scaffold to the output
directory. Copy it to `overrides.json` and fill in values; non-null fields win
over scraped prices and cached results. Supported fields: `price_nok`, `km`,
`year`, `model_year`, `url`, `known_repairs_nok`, `current_resale_value_nok`,
`scheduled_maintenance_nok`, `resale_nok`.

```json
{
  "fleet_overrides": {
    "Mitsubishi Outlander PHEV::2020::60000": {
      "resale_nok": 150000
    }
  }
}
```

## Tests

```bash
python tests/run_tests.py
```

## License

MIT — see [LICENSE](LICENSE).
