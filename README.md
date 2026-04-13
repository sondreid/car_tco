# car_reliability

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
# Default run — writes reports/tco_full.csv and reports/tco_summary.csv
car-reliability

# Adjust energy prices and driving pattern
car-reliability --petrol 25.0 --annual-km 20000 --years 4

# Override purchase prices
car-reliability --price "Toyota RAV4 Hybrid=260000" --price "Volkswagen Passat GTE=190000"

# Replace reference prices with a typical comparable-market price from FINN
car-reliability --scrape-prices

# Reuse previously downloaded FINN prices from the local cache only
car-reliability --use-cached-scraped-prices

# Tighten or loosen the FINN matching window for live scraping
car-reliability --scrape-prices --year-tolerance 1 --km-tolerance 20000 --min-matches 3

# Change PHEV charge assumption (pessimistic: 25% of trips start charged)
car-reliability --charge-share 0.25

# Disable PHEV blending (model runs on petrol only)
car-reliability --no-phev-blend

# Change output location
car-reliability --output-dir results/ --output-prefix scenario_cheap_energy

# Suppress file output, print only
car-reliability --no-output
```

### Python API

```python
from car_reliability.pipeline import run
from car_reliability.assumptions import Assumptions
from car_reliability.data import build_car
from car_reliability.pricing import PriceEstimatorConfig

# Default scenario
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

df = run(
    price_estimation=True,
    price_estimator_config=PriceEstimatorConfig(
        year_tolerance=1,
        km_tolerance=20_000,
        min_matches=2,
    ),
)

df = run(
    price_estimation=True,
    use_cached_scraped_prices=True,
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
```

---

## Package layout

```
car_reliability/
├── assumptions.py        ← All toggleable parameters (single source of truth)
├── pipeline.py           ← High-level run() entry point
├── cli.py                ← argparse CLI (car-reliability command)
├── __main__.py           ← python -m car_reliability support
├── data/
│   ├── catalogue.py      ← Per-model TCO data (scheduled maintenance, residuals, consumption)
│   ├── reliability.py    ← Source-backed reliability inputs and links
│   └── reference_fleet.py← Default fleet + price_overrides / extra_cars
├── scoring/
│   └── reliability.py    ← Composite reliability score computation
├── cost/
│   ├── energy.py         ← Fuel/electricity cost with PHEV blending
│   ├── maintenance.py    ← Maintenance cost model
│   ├── depreciation.py   ← Residual value, depreciation, capital cost
│   └── tco.py            ← Assembles one complete result row
└── reports/
    └── __init__.py       ← DataFrame builder, CSV writer, console printer
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
   - `car_reliability/data/catalogue.py`
   - `car_reliability/data/reliability.py`

2. Car instance
   This is one concrete comparison candidate with price, year and km.

The code supports two instance modes:

1. Named model mode
   Use `build_car("Toyota RAV4 Hybrid")`
   This copies the repo's default reference instance for that model from
   `reference_fleet.py`.

2. Override mode
   Use `build_car("Toyota RAV4 Hybrid", price_nok=260_000, km=95_000)`
   This starts from the default reference instance and overrides only the
   fields you specify.

For an already-owned car, use:
- `existing_car=True`
- `current_resale_value_nok=...`

This is treated as a keep-versus-sell opportunity cost.
The output field is `foregone_resale_value_nok`, meaning the sale value you
give up by keeping the car instead of selling it today.

If you want a model to appear in the default shortlist, also add a default
reference instance to `car_reliability/data/reference_fleet.py`.

## FINN price estimation

Live FINN pricing is opt-in with `--scrape-prices`.

Manual `--price` overrides apply only in the default non-scraping mode.
If `--scrape-prices` or `--use-cached-scraped-prices` is active, the scraped
price wins.

It does not use a strict arithmetic mean. The estimator:
- filters listings to the expected model and year/km window
- ranks accepted listings by closeness to the target year and km
- takes the nearest comparable subset
- uses the median price from that subset as the typical price

This output is labeled `price_source=finn_typical`.

Successful live scraping updates `reports/finn_price_cache.json`.

You can then rerun offline with:

```bash
car-reliability --use-cached-scraped-prices
```

Cache-only mode uses the saved estimates and labels them
`price_source=finn_cached`.
It does not fall back to live fetching.

Example:

```python
from car_reliability.data import build_car

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
