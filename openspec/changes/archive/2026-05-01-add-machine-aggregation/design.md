## Context

The clean-room repo currently exposes `calculate_component`
(`src/mixsheet/domain/calculator.py`) which produces a
`ComponentBreakdown` for a single `Component` against a `Catalog`. The
`Project` model already supports a `shape: machine` with multiple
components and a `shape: single` with exactly one — both share the
same file format.

The legacy backend in `mixsheet_backup/` performed the equivalent of
aggregation inline inside `api/routes/purchase.py`: it ran the
calculator per component, summed weights into a `defaultdict[str,
Decimal]`, multiplied in `overage_pct`, then handed the result to the
optimizer — all in one route handler, with `Decimal.quantize`
sprinkled at intermediate steps. That code is now reference-only; the
legacy approach mixed three concerns (mix-sheet semantics, purchase
overage, package selection) and dropped precision before the
optimizer saw the numbers.

This change introduces a single, pure aggregation step that the
wizard, the eventual purchase optimizer, and the exporter can all
build on.

## Goals / Non-Goals

**Goals:**

- One pure function `aggregate_project(project, catalog) ->
  ProjectBreakdown` that the wizard and the (future) purchase
  optimizer share.
- Frozen, strict Pydantic value objects so callers cannot mutate
  results — consistent with `ComponentBreakdown` and the rest of the
  domain layer.
- Full `Decimal` precision end-to-end; rounding is the renderer's
  job.
- Source attribution per material (`component_id`, `preset_id`,
  `weight_kg`) so the future purchase list can show "where did these
  20 kg of Durigid go" and the per-component mix sheet exporter can
  reuse the same data.
- Single iteration over `project.components`; reuse
  `calculate_component` so arithmetic lives in exactly one place.

**Non-Goals:**

- No `purchase.overage_pct` application (Phase 3, purchase
  optimization).
- No `purchase.excluded_materials` filtering (Phase 3, purchase
  optimization).
- No supplier, package, cost, or waste calculation.
- No CLI command, no Rich rendering, no export. The renderer/wizard
  layer consumes the breakdown later.
- No new dependency.

## Decisions

### Capability name: `project-aggregation` (not `machine-aggregation`)

A `Project` is the aggregation unit, not a "machine". Single-component
projects pass through the same function and the wizard renders both
shapes from the same data. The change folder is named
`add-machine-aggregation` (per the proposal trigger), but the
capability spec is `project-aggregation`.

**Alternatives considered:**

- `machine-aggregation` — would force the wizard to branch on `shape`
  before deciding whether to call the aggregator. Two code paths for
  the same arithmetic.

### Module placement: `mixsheet/domain/aggregator.py`

Mirrors `calculator.py` (one module, one pure function, one frozen
result type). Keeps the domain layer flat and discoverable.

**Alternatives considered:**

- Adding a method on `Project` — couples the model to the catalog and
  to a calculation that is not part of the persisted state.
- Folding aggregation into `calculator.py` — the calculator's
  contract is "one component, one breakdown"; aggregation is a
  distinct shape.

### Result shape: rich, with sources

`ProjectBreakdown` carries:

- `project_id: str`, `project_name: str`, `shape: Literal["single",
  "machine"]` for downstream rendering without re-loading the
  project.
- `components: list[ComponentBreakdown]` — full per-component
  breakdowns, in `project.components` order. Reuses the existing
  type; no parallel structure.
- `total_net_volume_l: Decimal`, `total_weight_kg: Decimal` —
  project-wide totals.
- `materials: list[AggregatedMaterial]` — sorted alphabetically by
  `material_name` (case-insensitive), each with `total_weight_kg` and
  a non-empty `sources: list[AggregatedMaterialSource]`.
- `AggregatedMaterialSource(component_id, preset_id, weight_kg)` —
  one entry per `(component_id, material_id)` pair contributing to
  the total. Two components with the same preset and same material
  produce two source entries, not one.

Sources let the purchase optimizer attribute selected packages back
to components for a per-component mix sheet without recomputing the
calculator. The cost is one extra list per material (small data,
zero new arithmetic).

**Alternatives considered:**

- Totals only (no sources) — forces a re-derivation later from
  `components`, duplicating logic when the exporter needs the
  attribution.
- Sources keyed by `(component_id, preset_id, material_id)` as a
  flat list at the top level — more flexible but loses the natural
  grouping by material that the user-flow display needs.

### Precision: no quantisation in the aggregator

`Decimal` arithmetic is exact for sums of `Decimal` operands. The
calculator already returns full-precision values; the aggregator
sums them. The renderer rounds to display rules (`PRICE_DECIMALS`,
`QUANTITY_DECIMALS_*`).

**Alternatives considered:**

- Quantise to 2 decimals like the legacy code — caused drift between
  per-component sums and project totals (10 components × 0.005 kg
  rounding error per component = 5 g project-wide). Already
  rejected at the calculator level; reject again here.

### Material ordering: alphabetical

Same rule as `calculate_component` — case-insensitive sort by
`material_name`. A diff-friendly stable order matters more for
exports than catalog/preset order.

### Errors: propagate `UnknownPresetError` only

The aggregator delegates preset resolution to `calculate_component`;
its only error path is the calculator's `UnknownPresetError`. No new
exception type. Empty `components` is already prevented by the
`Project` model (`min_length=1`).

### Source list ordering

`AggregatedMaterial.sources` follows `project.components` order, not
alphabetical. The components list is a stable ordered sequence the
user authored; rearranging it in the source view would surprise.

## Risks / Trade-offs

- **Risk**: The `sources` list duplicates information already present
  in `ProjectBreakdown.components`. → **Mitigation**: documented as
  intentional denormalisation; the exporter and optimizer both want
  the per-material rollup, and computing it once is cheaper than
  twice. No write-path duplication (the breakdown is computed, never
  persisted).
- **Risk**: Two components sharing one preset produce two source
  entries for every material — verbose for large machines. →
  **Mitigation**: acceptable; the user-flow's "Aggregated totals"
  display only renders the totals, sources surface in the (future)
  per-component mix-sheet exporter where the granularity is
  desired.
- **Risk**: Adding `shape` and `project_id` to `ProjectBreakdown`
  couples the result to the project model fields. → **Mitigation**:
  these are read-only echoes used purely for rendering. The
  aggregator does not need to look them up later — they ride along
  in the breakdown so the renderer doesn't need both `Project` and
  `ProjectBreakdown`.

## Migration Plan

Purely additive change; nothing to migrate. After merge, the wizard
(Phase 5) and the purchase optimizer (Phase 3) will both consume
`ProjectBreakdown`.

## Open Questions

_None._
