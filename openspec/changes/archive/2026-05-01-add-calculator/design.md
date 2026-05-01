## Context

`add-domain-models` shipped the typed shapes (`Component`, `Volume`, `Catalog`, `MixPreset`, `MaterialProportion`, `Material`, …) and the YAML loaders. Phase 1 of the roadmap closes with a calculator that turns `(Component, Catalog)` into a per-component material breakdown. Every later phase consumes that breakdown: machine aggregation sums it, the optimizer feeds it into supplier-package selection, the exporter writes it to CSV/xlsx, and the wizard renders it with Rich.

The legacy reference (`mixsheet_backup/backend/src/mixsheet/services/calculator.py`) implements the same arithmetic but quantises every weight to two decimals inside the calculator. We deliberately diverge: the domain layer keeps full precision; rounding happens at the display boundary using the constants already in `mixsheet.domain.display`.

## Goals / Non-Goals

**Goals:**

- One pure function (`calculate_component`) consumed by every later capability, with a single, frozen return type (`ComponentBreakdown`).
- Full-precision `Decimal` arithmetic — no `.quantize()` inside the calculator.
- Stable, alphabetically ordered material rows so exports and snapshots diff cleanly.
- Clear failure mode when a preset id does not resolve (`UnknownPresetError`).
- Catalog preset is authoritative; pinned `preset_version` mismatches are reported elsewhere.

**Non-Goals:**

- Multi-component aggregation (`add-machine-aggregation`).
- Purchase optimization, strategies, waste, cost (`add-purchase-optimizer`).
- Display formatting / Rich tables (`add-interactive-wizard`).
- CSV / xlsx export (`add-export`).
- Filtering by `purchase.excluded_materials`.
- 0.01 L minimum-volume warning (input validation belongs to the wizard).
- Mismatch resolution UX between pinned version and catalog version.

## Decisions

### D1. Pure function, not a service class

`calculate_component(component: Component, catalog: Catalog) -> ComponentBreakdown` is a module-level function, not a class. There is no state to carry between calls.

*Alternative considered:* a `CalculatorService` class mirroring the legacy backend. Rejected: nothing motivates a class — no DI, no configuration, no batching state. A free function is easier to call from the wizard, the optimizer, and tests, and keeps the public surface minimal.

### D2. Calculator resolves the preset itself

The function takes a `Catalog`, not a pre-resolved preset, and looks the preset up via `catalog.preset_by_id`. Callers cannot drift between `component.preset_id` and a separately fetched preset.

*Alternative considered:* `calculate_component(component, preset, catalog)`. Rejected: two arguments that must agree is a footgun. Single source of truth wins.

### D3. Catalog preset is authoritative; mismatch reporting stays in the loader

When `component.preset_version` differs from the catalog version of the same preset id, the calculator still computes against the catalog preset. `load_project` already returns a `ProjectLoadResult` with a `mismatches` list; the wizard's resolution UX consumes that. The calculator never raises on version drift.

*Alternative considered:* refusing to calculate on mismatch. Rejected: the user-flow explicitly allows recalculation against the new catalog as one of the resolution options, and refusing here would leak loader concerns into the calculator.

### D4. Full-precision Decimal, no quantisation in the calculator

All multiplications stay in `Decimal` with the default `getcontext()` precision (28 digits). The breakdown stores unrounded values. Rounding happens at the renderer using the constants in `mixsheet.domain.display`.

*Alternative considered:* quantising to `Decimal("0.01")` inside the calculator (legacy behaviour). Rejected: it conflates display with calculation, sums of rounded weights drift from `total_weight_kg`, and any later capability that needs precision (e.g. the optimizer's per-kg cost arithmetic) would have to redo the math. FR-009 ("Decimal-only, internal precision throughout") is the binding rule.

### D5. Denormalise material name into the breakdown

`MaterialBreakdownRow.material_name` is filled by looking up the material in the catalog. Renderers (Rich tables, CSV writer, xlsx writer) consume the breakdown alone — they do not need the catalog.

*Alternative considered:* leaving renderers to look up names. Rejected: every renderer would need to plumb the catalog through, and the breakdown would be incomplete on its own (bad for snapshot tests and JSON dumps).

### D6. Alphabetical material ordering, case-insensitive

Rows are sorted by `material_name` in case-insensitive ascending order. Stable across calls.

*Alternative considered:* preserve preset order. Rejected: preset order is editorial and shifts when catalogs are reorganised. Alphabetical ordering keeps exports diff-friendly and protects the user from caring about catalog row order.

### D7. `UnknownPresetError` is its own exception type

A dedicated `UnknownPresetError(LookupError)` sits in `calculator.py`. It is raised by `calculate_component` when `catalog.preset_by_id(component.preset_id)` returns `None`.

*Alternative considered:* `KeyError` or reusing `CatalogError`. Rejected: `KeyError` is too generic for callers to discriminate against; `CatalogError` is reserved for fail-fast catalog loading. A typed domain error keeps the wizard's "pick a replacement" flow simple to wire up later.

### D8. Output model location and shape

`ComponentBreakdown` and `MaterialBreakdownRow` live next to the function in `src/mixsheet/domain/calculator.py`, mirroring how `Project` and `Catalog` co-locate their loaders. Both models are `frozen=True, extra="forbid"`. `ComponentBreakdown` carries denormalised preset metadata (`preset_id`, `preset_name`, `density_kg_per_l`) so renderers and exporters do not need the catalog or the preset object.

*Alternative considered:* a separate `breakdown.py` module. Rejected: nothing else lives there yet, and the breakdown is meaningless without the function that produces it.

## Risks / Trade-offs

- **[Risk]** Full-precision Decimal weights might surprise downstream consumers that expect a rounded display value. → **Mitigation**: every renderer (wizard, exporter) MUST round at its own boundary using the `display.py` constants. Tests assert that the calculator does not quantise.
- **[Risk]** Alphabetical ordering hides a subtle change if a catalog is renamed. → **Mitigation**: `material_id` stays in the row; tests assert ordering explicitly.
- **[Risk]** Sum of unrounded material weights may differ from a rounded `total_weight_kg` in displays if renderers round each row independently. → **Mitigation**: the renderer is responsible for footer reconciliation (compute the footer total from the same source data, not by summing rounded rows). Out of scope here, but flagged for the wizard/exporter changes.
- **[Trade-off]** Catalog-preset-wins over pinned version means a user opening an old project may see different weights than when they originally calculated. → **Mitigation**: the loader already returns mismatches and the wizard's resolution UX (later change) makes this user-visible before the calculator runs.

## Catalog ownership and CLI surface

- **Catalog ownership**: unchanged. Calculator consumes a `Catalog` produced by `add-domain-models`. No new YAML files, no new bundled data.
- **File-format compatibility**: unchanged. Project files written by `save_project` remain valid; the calculator reads no new fields.
- **CLI surface**: unchanged in this change. `add-interactive-wizard` will wire `calculate_component` into the wizard later.
