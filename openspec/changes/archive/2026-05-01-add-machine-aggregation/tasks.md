## 1. Domain models

- [x] 1.1 Create `src/mixsheet/domain/aggregator.py` with frozen
      Pydantic value objects: `AggregatedMaterialSource`
      (`component_id`, `preset_id`, `weight_kg: Decimal`),
      `AggregatedMaterial` (`material_id`, `material_name`,
      `total_weight_kg: Decimal`, `sources: list[...]` non-empty), and
      `ProjectBreakdown` (`project_id`, `project_name`, `shape`,
      `components: list[ComponentBreakdown]`, `total_net_volume_l:
      Decimal`, `total_weight_kg: Decimal`, `materials:
      list[AggregatedMaterial]`).
- [x] 1.2 Use `model_config = ConfigDict(frozen=True, extra="forbid")`
      on every value object, mirroring `ComponentBreakdown`.

## 2. Pure aggregation function

- [x] 2.1 Implement `aggregate_project(project: Project, catalog:
      Catalog) -> ProjectBreakdown` that calls
      `calculate_component(c, catalog)` once per component in
      `project.components` order.
- [x] 2.2 Build a `dict[str, list[AggregatedMaterialSource]]` keyed by
      `material_id`, appending one source per component contribution
      in component order; track the material display name from the
      first source.
- [x] 2.3 Compute `total_net_volume_l` and `total_weight_kg` as the
      sum of `ComponentBreakdown.net_volume_l` and `total_weight_kg`
      respectively, with no quantisation.
- [x] 2.4 Compute each `AggregatedMaterial.total_weight_kg` as
      `sum(source.weight_kg for source in sources)`, full Decimal
      precision.
- [x] 2.5 Sort `materials` case-insensitively by `material_name`.
- [x] 2.6 Echo `project_id`, `project_name`, and `shape` from the
      input project onto the result.
- [x] 2.7 Do not catch `UnknownPresetError`; let it propagate.

## 3. Public API

- [x] 3.1 Export `aggregate_project`, `ProjectBreakdown`,
      `AggregatedMaterial`, `AggregatedMaterialSource` from
      `src/mixsheet/domain/__init__.py`.

## 4. Tests

- [x] 4.1 Add `tests/domain/test_aggregator.py`.
- [x] 4.2 Single-component project: `components` length 1, totals
      equal the calculator's per-component output, materials echo the
      breakdown rows with one source each.
- [x] 4.3 Two-component machine with different presets sharing one
      material: aggregated row shows summed total and two sources in
      `project.components` order.
- [x] 4.4 Two components using the same preset: identical material
      rows produce two source entries (not deduplicated) and the
      total equals the exact sum.
- [x] 4.5 Material-name ordering: presets declared in non-alphabetical
      order yield alphabetical `materials`; component order in
      `sources` is independent of material ordering.
- [x] 4.6 Decimal precision: contributions chosen so the legacy
      0.01-quantise approach would drift; assert
      `total_weight_kg` retains full precision.
- [x] 4.7 Material-totals reconciliation: `sum(materials.total_weight_kg)
      == ProjectBreakdown.total_weight_kg` for a clean preset.
- [x] 4.8 Excluded materials: project with
      `purchase.excluded_materials = ["water"]` and a preset
      containing `water` still includes the `water` row in the
      aggregate.
- [x] 4.9 Overage ignored: project with `purchase.overage_pct =
      Decimal("0.10")` produces totals equal to the no-overage sum.
- [x] 4.10 Unknown preset: a component pointing at a missing preset
      raises `UnknownPresetError` with the offending id in the
      message.
- [x] 4.11 Pure-function check: aggregator does not mutate
      `project`/`catalog` (compare `model_dump()` snapshots before/after).
- [x] 4.12 Frozen result: assert assigning to any field on
      `ProjectBreakdown`, `AggregatedMaterial`, or
      `AggregatedMaterialSource` raises `ValidationError`.

## 5. Quality gates

- [x] 5.1 `uv run ruff check --fix` then `uv run ruff format` on the
      new module and tests.
- [x] 5.2 `uv run pyright` clean for `src/mixsheet/domain/aggregator.py`
      and the test file.
- [x] 5.3 `uv run pytest tests/domain/test_aggregator.py -v` green.
- [x] 5.4 `openspec validate add-machine-aggregation --strict` passes.

## 6. Documentation

- [x] 6.1 Mark Phase 2 complete in `docs/ROADMAP.md` (replace the
      bullet list with a ✅ heading once merged).
- [x] 6.2 Add an `## [Unreleased]` `### Added` bullet to `CHANGELOG.md`:
      "Pure project aggregator: per-component, per-material, and
      project-level totals with source attribution."
