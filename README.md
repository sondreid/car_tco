# car_tco

Modular Python package for computing 3-year Total Cost of Ownership (TCO) and
composite reliability scores for a set of reference used cars (Norwegian market).

The reliability model is a structured scorecard:
- evidence score
- technical robustness score
- confidence score
- age and mileage penalties

Maintenance is split into scheduled maintenance and failure-risk cost.

---

## Install

```bash
pip install -e ".[dev]"
```

---

## Quick start

### CLI

```bash
# Default CLI run — refresh FINN prices, rerun the model, write CSVs and caches
car-tco

# Refresh only the FINN price/km cache
car-tco --scrape-prices

# Reuse cached FINN prices and rerun reliability + TCO
car-tco --use-cached-scraped-price

# Reuse cached reliability outputs and rerun cost/reporting layers
car-tco --use-cached-reliability

# Reuse the full cached model output without recomputing
car-tco --use-cached

# Manual-price Python-style default also exists in the library API
# and still supports price overrides for scenario work
car-tco --petrol 25.0 --annual-km 20000 --years 4

# Change PHEV charge assumption (pessimistic: 25% of trips start charged)
car-tco --charge-share 0.25

# Disable PHEV blending (model runs on petrol only)
car-tco --no-phev-blend

# Change output location
car-tco --output-dir results/ --output-prefix scenario_cheap_energy

# Suppress file output, print only
car-tco --no-output
```

### Python API

```python
from car_tco.pipeline import RunMode, run
from car_tco.assumptions import Assumptions
from car_tco.data import build_car
from car_tco.pricing import PriceEstimatorConfig

# Default Python API scenario uses checked-in reference prices
df = run()

# Custom scenario
a = Assumptions(
    annual_km=20_000,
    horizon_years=4,
    petrol_nok_per_l=25.0,
    charge_share=0.25,       # pessimistic PHEV charging
    capital_rate=0.05,
)
df = run(
    assumptions=a,
    price_overrides={"Toyota RAV4 Hybrid": 260_000},
    output_dir="results/",
    output_prefix="pessimistic",
)

# Refresh FINN prices and rerun the whole model
df = run(
    mode=RunMode.RERUN_MODEL,
    price_estimator_config=PriceEstimatorConfig(
        year_tolerance=1,
        km_tolerance=20_000,
        min_matches=2,
    ),
)

# Reuse cached FINN prices
df = run(
    mode=RunMode.USE_CACHED_SCRAPED_PRICE,
)

# Existing car can be represented with no purchase price and known repairs
df = run(
    extra_cars=[
        build_car(
            "Toyota Avensis",
            existing_car=True,
            price_nok=0,
            current_resale_value_nok=20_000,
            year=2012,
            km=182_000,
            known_repairs_nok=50_000,
            exclude_from_price_estimation=True,
        )
    ]
)

df = run(
    extra_cars=[
        build_car(
            "Toyota RAV4 Hybrid",
            year=2020,
            model_year=2019,
            km=95_000,
        )
    ]
)
```

---

## Package layout

```
car_tco/
├── assumptions.py        ← All toggleable parameters (single source of truth)
├── pipeline.py           ← High-level run() entry point
├── cli.py                ← argparse CLI (car-tco command)
├── __main__.py           ← python -m car_tco support
├── cache_store.py        ← Shared JSON cache reader/writer
├── overrides.py          ← Manual per-car override loading and precedence
├── .codex/skills/        ← Repo-local agent skills, including reliability profile updates
├── data/
│   ├── catalogue.json            ← Checked-in model maintenance/residual/consumption data
│   ├── catalogue.py              ← JSON loader for catalogue data
│   ├── model_assumptions.json    ← Checked-in FINN pricing/search assumptions
│   ├── model_assumptions.py      ← JSON loader for pricing model profiles
│   ├── reference_fleet.json      ← Checked-in default comparison fleet
│   ├── reference_fleet.py        ← Fleet helpers and build_car()
│   ├── reliability_profiles.json ← LLM-fillable reliability evidence with metadata
│   └── reliability.py            ← JSON loader for reliability profiles and metadata
├── scoring/
│   └── reliability.py    ← Composite reliability score computation
├── cost/
│   ├── energy.py         ← Fuel/electricity cost with PHEV blending
│   ├── maintenance.py    ← Maintenance cost model
│   ├── depreciation.py   ← Residual value, depreciation, purchase opportunity cost
│   └── tco.py            ← Assembles one complete result row
├── pricing/
│   └── finn.py           ← FINN scraping, matching and price cache handling
└── reports/              ← Side effects: caches and generated CSVs
```

---

## Key toggleable assumptions (`Assumptions`)

| Field | Default | Description |
|---|---|---|
| `annual_km` | 15 000 | km/year |
| `horizon_years` | 3 | Ownership horizon |
| `petrol_nok_per_l` | 23.0 | NOK per litre petrol |
| `diesel_nok_per_l` | 22.0 | NOK per litre diesel |
| `electricity_nok_per_kwh` | 1.5 | NOK per kWh |
| `capital_rate` | 0.04 | Opportunity cost rate |
| `phev_dynamic_consumption` | True | Blend PHEV petrol/kWh from usage pattern |
| `charge_share` | 0.50 | Fraction of PHEV trips starting fully charged |
| `trip_km` | 60 | Representative trip length for PHEV blend |
| `ev_range_km` | 54 | PHEV EV range on full charge |
| `battery_kwh_full` | 13.8 | PHEV usable battery kWh |
| `weight_evidence` | 0.55 | Weight of evidence score |
| `weight_technical_risk` | 0.30 | Weight of technical-risk score |
| `weight_confidence` | 0.15 | Weight of evidence confidence |
| `evidence_survey_weight` | 0.60 | Survey weight inside evidence score |
| `evidence_owner_weight` | 0.40 | Owner weight inside evidence score |
| `age_penalty_per_year` | 1.5 | Score penalty per year beyond 4-year grace |
| `mileage_penalty_per_10k` | 0.8 | Score penalty per 10k km beyond 60k |
| `failure_risk_cost_per_point` | 220 | Annual failure-risk cost per technical-risk point |
| `residual_reliability_sensitivity` | 0.002 | Residual adjustment per reliability point |
| `residual_km_penalty_per_10k` | 0.01 | Residual penalty per 10k km over 160k at end |

---

## Adding a new car

There are two layers in this repo:

1. Model definition
   This is the canonical definition of a car type.
   Add entries in:
   - `car_tco/data/catalogue.json`
   - `car_tco/data/reliability_profiles.json`
   - `car_tco/data/model_assumptions.json` if the model should scrape reliably
   - use `.codex/skills/reliability-profile-updater` when you want Codex to research and update reliability evidence

2. Car instance
   This is one concrete comparison candidate with price, year and km.

The code supports two instance modes:

1. Named model mode
   Use `build_car("Toyota RAV4 Hybrid")`
   This copies the repo's default reference instance for that model from
   `reference_fleet.json`.

2. Override mode
   Use `build_car("Toyota RAV4 Hybrid", price_nok=260_000, km=95_000)`
   This starts from the default reference instance and overrides only the
   fields you specify.

If the listing year and the model year should differ in the comparison, pass
`model_year=...`. That override is used for:
- FINN year matching and cache identity
- year-specific reliability profile selection
- reliability age penalty

For an already-owned car, use:
- `existing_car=True`
- `current_resale_value_nok=...`

This is treated as a keep-versus-sell opportunity cost.
The output field is `foregone_resale_value_nok`, meaning the sale value you
give up by keeping the car instead of selling it today.

If you want a model to appear in the default shortlist, also add a default
reference instance to `car_tco/data/reference_fleet.json`.

## Run modes

The CLI has five explicit run modes:

- default CLI run / `--rerun-model`
  Refresh FINN prices, recompute reliability, recompute TCO, refresh caches.
- `--scrape-prices`
  Refresh only the FINN price cache. No reliability run, no TCO CSV output.
- `--use-cached-scraped-price`
  Do not scrape. Reuse cached FINN prices and rerun reliability + TCO.
- `--use-cached-reliability`
  Reuse cached reliability outputs and rerun cost/reporting layers.
- `--use-cached`
  Reuse cached final result rows and do not overwrite caches.

The Python API stays conservative by default:

```python
df = run()
```

That path recomputes reliability and TCO from checked-in source data without
live scraping unless you pass an explicit `RunMode`.

## FINN price estimation

The FINN estimator does not use a strict arithmetic mean. It:
- filters listings to the expected model and year/km window
- ranks accepted listings by closeness to the target year and km
- takes the nearest comparable subset
- uses the median price from that subset as the typical price

Successful live scraping updates `finn_price_cache.json` in the active
`output_dir`.

```bash
car-tco --scrape-prices
car-tco --use-cached-scraped-price
```

The project also writes:
- `reliability_cache.json`
- `results_cache.json`
- `overrides_example.json`
- `tco_full.csv`
- `tco_summary.csv`

`overrides_example.json` is generated automatically if it does not exist.
It is a scaffold/example file. If `overrides.json` exists in the same output
directory, the pipeline applies that file automatically instead. Each fleet
entry starts with `null` values, and only non-null values are used as
overrides. Manual overrides win over scraped prices and cached results.

All caches are keyed by the full reference identity:
- `model`
- `year`
- `model_year` when present, otherwise `year`
- `km`

This matters for model-year experiments, so a `Toyota RAV4 Hybrid` `2018`
entry and a `Toyota RAV4 Hybrid` `2020` entry are cached separately.

## Manual overrides

Use `overrides.json` when you want manual scenario values to beat scraped and
cached values. `overrides_example.json` is only the generated template.
Missing or `null` fields mean "do not override".

Example:

```json
{
  "fleet_overrides": {
    "Mitsubishi Outlander PHEV::2020::60000": {
      "price_nok": null,
      "km": null,
      "year": null,
      "model_year": null,
      "url": null,
      "known_repairs_nok": null,
      "current_resale_value_nok": null,
      "scheduled_maintenance_nok": null,
      "residual_base": null,
      "resale_nok": 150000
    }
  }
}
```

Supported override fields:
- `price_nok`
- `km`
- `year`
- `model_year`
- `url`
- `known_repairs_nok`
- `current_resale_value_nok`
- `scheduled_maintenance_nok`
- `residual_base`
- `resale_nok`

Example:

```python
from car_tco.data import build_car

rav4_default = build_car("Toyota RAV4 Hybrid")
rav4_specific = build_car(
    "Toyota RAV4 Hybrid",
    price_nok=255_000,
    year=2020,
    km=98_000,
    url="https://www.finn.no/...",
)

avensis_existing = build_car(
    "Toyota Avensis",
    existing_car=True,
    price_nok=0,
    current_resale_value_nok=20_000,
    known_repairs_nok=50_000,
)
```

---

## Tests

```bash
python3 tests/run_tests.py
```
