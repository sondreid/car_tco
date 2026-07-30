# models.json

`car_tco/data/models.json` is an object keyed by model name. Each entry is the
complete definition of one car model:

```json
{
  "Example Model": {
    "catalogue": {
      "consumption": { "petrol_l": 4.9 },
      "residual_base": 0.78,
      "scheduled_maintenance_nok": 5500
    },
    "pricing_profile": {
      "query": "example model",
      "required_groups": [["example"], ["model", "variant"]],
      "excluded_tokens": ["phev", "diesel"]
    },
    "reliability": {
      "metadata": {
        "status": "draft",
        "generated_by": "add-model",
        "generated_at": "2026-07-30",
        "reviewed_by": null,
        "reviewed_at": null
      },
      "profile": {
        "survey_score": 90.0,
        "owner_score": 88.0,
        "complexity_risk": 9,
        "failure_cost_risk": 7,
        "evidence_confidence": 76.0,
        "known_failure_modes": ["electrics", "DPF"],
        "sources": [
          {
            "publisher": "What Car?",
            "url": "https://example.com",
            "summary": "Short source-backed summary."
          }
        ]
      },
      "year_profiles": [
        {
          "year": 2020,
          "metadata": { "...": "same fields as metadata above" },
          "profile": { "...": "same fields as profile above" }
        }
      ]
    }
  }
}
```

## Section intent

### catalogue (required)

- `consumption`: real-world figures per 100 km; keys are `petrol_l`,
  `diesel_l` and/or `kwh`. PHEVs list both `kwh` and `petrol_l`.
- `residual_base`: expected fraction of purchase price retained over the
  default horizon before reliability/mileage adjustments.
- `scheduled_maintenance_nok`: typical annual scheduled maintenance in NOK.

### pricing_profile (optional)

Controls FINN price scraping. Omit it for models that should never be scraped
(for example an already-owned car).

- `query`: FINN search query.
- `required_groups`: list of groups; a listing title must match at least one
  token from every group.
- `excluded_tokens`: tokens that reject a listing (wrong variant/fuel).

### reliability (required)

- `survey_score`: headline source-backed reliability score when a survey gives one.
- `owner_score`: owner-reported or used-review impression as a comparable score.
- `complexity_risk`: technical complexity downside, 0-20 style ordinal.
- `failure_cost_risk`: expensive-failure downside, 0-20 style ordinal.
- `evidence_confidence`: confidence in evidence quality and consistency.
- `known_failure_modes`: short normalized phrases, not long explanations.
- `sources`: evidence items with publisher, URL and a concise summary.

### year_profiles (optional)

Add only when evidence clearly differs by generation or model year. The entry
closest to a car's `model_year` wins at lookup time.

## Metadata rules

- Use `status: "draft"` unless the user explicitly says the entry is reviewed.
- Set `generated_by` to whoever produced the entry (`add-model` when this
  skill did) and `generated_at` to the current date.
- Leave `reviewed_by` and `reviewed_at` as `null` unless provided by the user.
