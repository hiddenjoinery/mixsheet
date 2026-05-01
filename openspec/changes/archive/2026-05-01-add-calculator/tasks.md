## 1. Output models and error type

- [x] 1.1 Add `MaterialBreakdownRow` (frozen, `extra="forbid"`) to `src/mixsheet/domain/calculator.py` with `material_id`, `material_name`, `weight_kg: Decimal`, `weight_per_component_kg: Decimal`
- [x] 1.2 Add `ComponentBreakdown` (frozen, `extra="forbid"`) with `component_id`, `preset_id`, `preset_name`, `density_kg_per_l: Decimal`, `quantity: int`, `volume_per_component_l: Decimal`, `net_volume_l: Decimal`, `weight_per_component_kg: Decimal`, `total_weight_kg: Decimal`, `materials: list[MaterialBreakdownRow]`
- [x] 1.3 Add `UnknownPresetError(LookupError)` with a message naming the offending `preset_id`

## 2. Calculator function

- [x] 2.1 Implement `calculate_component(component: Component, catalog: Catalog) -> ComponentBreakdown` in `src/mixsheet/domain/calculator.py`
- [x] 2.2 Resolve the preset via `catalog.preset_by_id(component.preset_id)`; raise `UnknownPresetError` when `None`
- [x] 2.3 Compute `volume_per_component_l = component.volume.volume_l`, `net_volume_l = volume_per_component_l * Decimal(component.quantity)`, `weight_per_component_kg = volume_per_component_l * preset.density_kg_per_l`, `total_weight_kg = net_volume_l * preset.density_kg_per_l`
- [x] 2.4 Build one `MaterialBreakdownRow` per `MaterialProportion` with `weight_kg = total_weight_kg * proportion` and `weight_per_component_kg = weight_per_component_kg_base * proportion`; use `catalog.material_by_id` for `material_name`
- [x] 2.5 Sort the rows by `material_name.casefold()` ascending before constructing the breakdown
- [x] 2.6 Confirm no `.quantize()` calls anywhere in the calculator path

## 3. Public surface

- [x] 3.1 Export `calculate_component`, `ComponentBreakdown`, `MaterialBreakdownRow`, `UnknownPresetError` from `src/mixsheet/domain/__init__.py`
- [x] 3.2 Run `ruff check --fix` and `ruff format` on touched files
- [x] 3.3 Run `pyright` on `src/mixsheet/domain/` and resolve any errors

## 4. Tests — happy paths

- [x] 4.1 Create `tests/domain/test_calculator.py`
- [x] 4.2 Add a test that constructs a `dimensions` component (800×400×120 mm, qty 1) against the bundled catalog's `epoxy-mix` and asserts `volume_per_component_l == Decimal("38.4")`, `total_weight_kg == Decimal("38.4") * density`
- [x] 4.3 Add a test for `area_height` mode (240000 mm² × 80 mm) against `gantry-beam-dynamic-fill` asserting volume and total weight
- [x] 4.4 Add a test for `direct` mode (12.5 L) covering both `quantity == 1` and `quantity == 3`
- [x] 4.5 Add a test asserting per-row `weight_kg` distributes `total_weight_kg` by proportion (sum of rows equals `total_weight_kg` exactly under Decimal)
- [x] 4.6 Add a test asserting `material_name` comes from `catalog.material_by_id` and is not `None`/empty for any row

## 5. Tests — ordering, precision, and edge cases

- [x] 5.1 Add a test asserting rows are sorted case-insensitively by `material_name`, independent of preset declaration order (use a fixture preset whose declaration order is intentionally non-alphabetical)
- [x] 5.2 Add a test asserting that no row's `weight_kg` is rounded to two decimals — pick proportions that yield repeating decimals and assert the unrounded `Decimal` is preserved
- [x] 5.3 Add a test asserting `UnknownPresetError` is raised when `component.preset_id` is missing from the catalog, and that the message contains the offending id
- [x] 5.4 Add a test asserting the calculator does NOT raise on a pinned `preset_version` mismatch — construct a component with a pinned version different from the catalog version and assert the breakdown reflects the catalog preset
- [x] 5.5 Add a test asserting the breakdown still includes `water` when `water.default_excluded` is `true` (excluded materials are not filtered at the calculator layer)

## 6. Tests — user-flow normative example

- [x] 6.1 Add a test that loads the router-gantry example from `docs/user-flow.md` (bed: 800×400×120 mm, epoxy-mix; cross-slide: 240000 mm² × 80 mm, gantry-beam-dynamic-fill) and runs `calculate_component` for each component
- [x] 6.2 Assert the bed's `net_volume_l == Decimal("38.4")` and the cross-slide's `net_volume_l == Decimal("19.2")`
- [x] 6.3 Assert each breakdown's material rows are alphabetically ordered

## 7. Documentation and validation

- [x] 7.1 Update `CHANGELOG.md` `[Unreleased]` `### Added` with one bullet for the calculator (mention `calculate_component`, `ComponentBreakdown`, full-precision Decimal contract)
- [x] 7.2 Run `pytest --cov=mixsheet.domain.calculator` and confirm coverage ≥ 95% for the new module
- [x] 7.3 Run `openspec validate --change add-calculator` and resolve any issues
- [x] 7.4 Run the full `pytest` suite and confirm no regressions in existing `tests/domain/` tests
