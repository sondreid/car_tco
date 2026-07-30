---
name: add-model
description: Add or refresh one car model in car_tco/data/models.json using web research. Populates catalogue data, the FINN pricing profile and source-backed reliability evidence in one pass, and optionally a default reference_fleet.json instance.
---

# Add Model

Use this skill when the task is to add a new car model to the comparison, or to
refresh the data of an existing one. Everything this skill does can also be done
by editing the JSON by hand — an LLM is practical here, not required.

Read `references/models-json.md` before editing. It defines the entry shape and
the meaning of each field.

## Workflow

1. Inspect the current entry (if any) in `car_tco/data/models.json`.
2. Research the model and fill all three sections:
   - `catalogue`: real-world consumption, residual_base, scheduled_maintenance_nok
   - `pricing_profile`: FINN search query and token matching rules
     (omit only when the model should never be price-scraped)
   - `reliability`: survey/owner scores, risk ordinals, failure modes, sources
3. Set `reliability.metadata`: `status: "draft"`, `generated_by: "add-model"`,
   `generated_at` to the current date, review fields `null` unless the user
   provides review information.
4. Add `year_profiles` only when the evidence is generation- or year-specific.
5. If the model should appear in the default comparison, add one instance to
   `car_tco/data/reference_fleet.json` (price, year, km, optional FINN URL).
6. Run `python skills/add-model/scripts/validate_models.py`, then the test
   suite with `python tests/run_tests.py`.

## Editing Rules

- Prefer direct survey or used-car reliability sources over generic journalism.
- Do not invent URLs, publishers, or source summaries.
- If evidence is mixed or thin, lower `evidence_confidence` rather than
  pretending certainty.
- Keep `known_failure_modes` short and normalized.
- Keep catalogue values plausible for the Norwegian used market and note the
  reasoning in the chat, not in the JSON.
- The primary output is the JSON update. Keep chat summaries short.
