## Why

Phase 1 of the roadmap requires a pure calculator that turns a `Component` plus a catalog into a per-component material breakdown. The domain models (`add-domain-models`) describe the shapes; this change adds the arithmetic that every downstream change — aggregation, optimizer, exporter, wizard — depends on.

Locking the calculator surface now keeps the optimizer and exporter from inventing their own ad-hoc breakdown structures. They consume one model: `ComponentBreakdown`.

## What Changes

- Add `calculate_component(component, catalog) -> ComponentBreakdown` as a pure function in `src/mixsheet/domain/calculator.py`.
- Add `ComponentBreakdown` (frozen Pydantic value object) with `component_id`, `preset_id`, `preset_name`, `density_kg_per_l`, `quantity`, `volume_per_component_l`, `net_volume_l`, `weight_per_component_kg`, `total_weight_kg`, and a `materials: list[MaterialBreakdownRow]`.
- Add `MaterialBreakdownRow` (frozen) with `material_id`, `material_name`, `weight_kg` (total across `quantity`), and `weight_per_component_kg`.
- Add `UnknownPresetError` raised when `component.preset_id` does not resolve in the supplied catalog.
- Material rows in the breakdown are sorted alphabetically by `material_name` for stable diffs and exports.
- Calculator preserves full `Decimal` precision throughout — no `.quantize()` inside the calculator. Display rounding stays in the renderer layer (the `display.py` constants already exist).
- Calculator denormalises `material_name` into the breakdown via `Catalog.material_by_id`, so renderers do not need to keep the catalog around.
- Excluded materials are NOT filtered here. The mix sheet shows every material in the preset; only the optimizer (later change) honours `excluded_materials`.
- When a project's pinned `component.preset_version` differs from the catalog version, the calculator still computes against the catalog preset. Mismatch reporting stays in `load_project` (already in `add-domain-models`); the wizard will offer recalculation as the resolution UX.

### Non-goals

- No multi-component aggregation across a machine project — lands in `add-machine-aggregation`.
- No purchase optimization, strategies, waste, or cost — lands in `add-purchase-optimizer`.
- No display formatting, Rich tables, or rounded outputs — lands in `add-interactive-wizard`.
- No CSV / xlsx export — lands in `add-export`.
- No filtering by `purchase.excluded_materials` at the calculator layer.
- No 0.01 L minimum-volume warning — that is wizard input validation, not a calculator concern.
- No version-mismatch UX (resolved in the wizard).
- No new runtime dependencies.

## Capabilities

### New Capabilities

- `calculator`: pure single-component material breakdown. Given a `Component` and a `Catalog`, produces a `ComponentBreakdown` with full-precision Decimal weights per material, alphabetically ordered, derived from the catalog preset's density and proportions.

### Modified Capabilities

_None — `domain-models` stays focused on data shapes; the calculator is its own capability._

## Impact

- **New code**: `src/mixsheet/domain/calculator.py` (function, output models, error type). `src/mixsheet/domain/__init__.py` re-exports the public surface.
- **New tests**: `tests/domain/test_calculator.py` covering golden fixtures adapted from the legacy backend (with rounding lifted out of the calculator), the user-flow normative router-gantry example, `UnknownPresetError`, all three `Volume` modes, and alphabetical material ordering.
- **Docs**: `CHANGELOG.md` `[Unreleased]` `### Added` gets one bullet for the calculator.
- **No new dependencies**.
- **Reference (do not copy)**: the legacy `mixsheet_backup/backend/src/mixsheet/services/calculator.py` quantises inside the calculator. We deliberately diverge: full precision in the domain layer, rounding at the display boundary.
