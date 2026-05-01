## Why

The calculator produces per-component breakdowns, but a project of
shape `machine` (and a single-component project, trivially) needs an
aggregated view: combined volume, combined weight, and one row per
material summed across components, with traceability back to where
each kilogram came from. Without aggregation the wizard cannot render
the "Aggregated totals" step in `docs/user-flow.md` and Phase 3
(purchase optimization) has no canonical demand vector to consume.

## What Changes

- Add a pure domain function `aggregate_project(project, catalog)` in
  a new module `mixsheet/domain/aggregator.py`.
- Add frozen Pydantic value objects `ProjectBreakdown`,
  `AggregatedMaterial`, and `AggregatedMaterialSource` describing the
  result shape.
- The aggregator reuses `calculate_component` for per-component
  arithmetic — no duplicated formulas.
- Materials are summed by `material_id` across components; each
  resulting row carries a `sources` list of `(component_id, preset_id,
  weight_kg)` so the purchase optimizer and exporter can attribute
  every kilogram.
- Material rows are sorted alphabetically by `material_name`,
  consistent with `ComponentBreakdown`.
- Full `Decimal` precision throughout — the aggregator never quantises;
  display rounding stays at the renderer layer.
- The aggregator is a pure function: no I/O, no mutation, no logging,
  no exceptions beyond `UnknownPresetError` propagated from the
  calculator.

## Non-goals

- No `purchase.overage_pct` applied — overage belongs to the purchase
  optimizer (Phase 3).
- No filtering of `purchase.excluded_materials` — the mix sheet shows
  what you pour; exclusion is a purchase-list concern.
- No package selection, supplier resolution, or cost calculation.
- No CLI command, no wizard prompt, no export — domain layer only.
- No persistence — `ProjectBreakdown` is computed on demand from a
  loaded `Project` plus the current `Catalog`.

## Capabilities

### New Capabilities

- `project-aggregation`: pure domain capability that aggregates a
  loaded `Project` into a `ProjectBreakdown` with combined volume,
  combined weight, per-component breakdowns, and per-material totals
  with sources.

### Modified Capabilities

_None._ The existing `calculator` and `domain-models` specs are
unchanged; aggregation composes on top of them.

## Impact

- **New code**: `src/mixsheet/domain/aggregator.py`, exports added to
  `src/mixsheet/domain/__init__.py`.
- **Tests**: `tests/domain/test_aggregator.py` covering
  single-component pass-through, multi-component summation, identical
  presets across components, alphabetical ordering, decimal precision,
  source attribution, and `UnknownPresetError` propagation.
- **No breaking changes** — purely additive.
- **Downstream**: unblocks Phase 3 (purchase optimization) which will
  consume `ProjectBreakdown.materials` as its demand vector.
- **Docs**: roadmap Phase 2 entry resolved; `docs/user-flow.md`
  "Aggregated totals" section is now backed by a contract.
