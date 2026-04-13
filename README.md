# car_reliability

Modular Python package for computing 3-year Total Cost of Ownership (TCO) and
composite reliability scores for a set of reference used cars (Norwegian market).

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

# Replace reference prices with the mean from matching FINN listings
car-reliability --scrape-prices

# Tighten or loosen the FINN matching window
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

# Existing car can be represented with no purchase price and known repairs
df = run(
    extra_cars=[
        {
            "model": "Toyota Avensis",
            "price_nok": 0,
            "year": 2012,
            "km": 182_000,
            "known_repairs_nok": 50_000,
            "exclude_from_price_estimation": True,
        }
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
│   ├── catalogue.py      ← Per-model TCO data (maintenance, residuals, consumption)
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
| `weight_published` | 0.55 | Weight of published reliability in score |
| `weight_owner` | 0.20 | Weight of owner-reported reliability |
| `weight_complexity` | 0.25 | Weight of inverse complexity |
| `age_penalty_per_year` | 1.5 | Score penalty per year beyond 4-year grace |
| `mileage_penalty_per_10k` | 0.8 | Score penalty per 10k km beyond 60k |
| `residual_reliability_sensitivity` | 0.003 | Residual adjustment per reliability point |
| `residual_km_penalty_per_10k` | 0.01 | Residual penalty per 10k km over 160k at end |

---

## Adding a new car

1. Add an entry to `car_reliability/data/catalogue.py` under `CAR_CATALOGUE`.
2. Add reliability inputs to `car_reliability/data/reliability.py`.
3. Add a reference entry to `car_reliability/data/reference_fleet.py` under `_DEFAULT_FLEET`,
   or pass it at runtime via `run(extra_cars=[...])`.

---

## Tests

```bash
python3 tests/run_tests.py
```
