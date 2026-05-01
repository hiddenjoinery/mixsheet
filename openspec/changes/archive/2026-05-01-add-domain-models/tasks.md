## 1. Package scaffold and dependencies

- [x] 1.1 Add `pyyaml` to `pyproject.toml` runtime deps and `types-pyyaml` to dev deps; run `uv sync`
- [x] 1.2 Create `src/mixsheet/domain/__init__.py` exporting the public model surface
- [x] 1.3 Create empty `src/mixsheet/domain/` modules: `catalog.py`, `project.py`, `strategy.py`, `display.py`
- [x] 1.4 Create `src/mixsheet/data/` directory; mark it as package data in `pyproject.toml` so it ships in the wheel

## 2. Display precision constants

- [x] 2.1 Implement `display.py` constants (`QUANTITY_DECIMALS_LOW`, `QUANTITY_DECIMALS_HIGH`, `QUANTITY_THRESHOLD`, `PRICE_DECIMALS`, `PERCENT_DECIMALS`)
- [x] 2.2 Add unit test asserting every constant equals its specified value
- [x] 2.3 Run `ruff check --fix` and `ruff format` on touched files

## 3. Strategy enum

- [x] 3.1 Implement `Strategy` `StrEnum` with members `CHEAPEST`, `BULK_VALUE`, `MINIMAL_WASTE`
- [x] 3.2 Add unit tests for round-trip and unknown-value rejection
- [x] 3.3 Run `ruff check --fix` and `ruff format`

## 4. Catalog models

- [x] 4.1 Implement `Material` (strict, frozen) with `id`, `name`, `category`, `default_excluded: bool = False`
- [x] 4.2 Implement `MaterialProportion` (strict, frozen) with `material_id` and `proportion: Decimal` validators (`0 < p ≤ 1`)
- [x] 4.3 Implement `MixPreset` (strict, frozen) with `id`, `name`, `version`, `density_kg_per_l: Decimal > 0`, optional `description`, optional `application`, non-empty `materials`, sum-to-one validator (tolerance `1e-4`)
- [x] 4.4 Implement `Supplier` (strict, frozen) with `id`, `name` (no `vat_rate`)
- [x] 4.5 Implement `SupplierPackage` (strict, frozen) with `id`, `material_id`, `supplier_id`, `weight_kg: Decimal > 0`, `price_incl_vat: Decimal ≥ 0`, computed `price_per_kg`
- [x] 4.6 Add unit tests for every spec scenario in "Material catalog model", "Material proportion model", "Mix preset model", "Supplier and package models"
- [x] 4.7 Run `ruff check --fix` and `ruff format`

## 5. Catalog file shape and loader

- [x] 5.1 Implement `Catalog` model holding `catalog_version`, `materials`, `presets`, `suppliers`, `packages` with cross-reference validation (every preset row's `material_id` resolves; every package's `material_id` and `supplier_id` resolve; no duplicate ids per kind)
- [x] 5.2 Implement `catalog_version` regex validator (`YYYY-MM-DD`)
- [x] 5.3 Implement `load_catalog(presets_path, suppliers_path)` using `yaml.safe_load`, raising one aggregated `CatalogError` listing all problems
- [x] 5.4 Implement `load_bundled_catalog()` using `importlib.resources` to read `mixsheet.data.presets` and `mixsheet.data.suppliers`
- [x] 5.5 Add unit tests for "Catalog file with version" and "Fail-fast catalog loader" scenarios, including the `safe_load` rejection of `!!python/object` tags
- [x] 5.6 Run `ruff check --fix` and `ruff format`

## 6. Bundled catalog YAML

- [x] 6.1 Author `src/mixsheet/data/presets.yaml` with `catalog_version: "2026-05-01"`, the materials list (with `default_excluded: true` on `water`), and the four presets (`epoxy-mix`, `gantry-beam-dynamic-fill`, `uhpc-mix`, `pure-epoxy-low-volume`) each carrying `density_kg_per_l` and proportions summing to 1.0; data values mirror the figures from the docs and `mixsheet_backup` reference
- [x] 6.2 Author `src/mixsheet/data/suppliers.yaml` with `catalog_version: "2026-05-01"`, the suppliers, and their packages — no `vat_rate`, no `description` — covering every material referenced by the presets except `water`
- [x] 6.3 Run `load_bundled_catalog()` in a smoke test and assert it returns a populated, error-free catalog

## 7. Volume discriminated union

- [x] 7.1 Implement `DimensionsVolume`, `AreaHeightVolume`, `DirectVolume` with strict `mode` literals and positive-Decimal validators
- [x] 7.2 Implement `volume_l` computed field per variant (`mm³ → L` via `Decimal("1000000")`)
- [x] 7.3 Wire the three variants into a `Volume` discriminated union via `Annotated[Union[...], Field(discriminator="mode")]`
- [x] 7.4 Add unit tests for every "Volume input modes" spec scenario
- [x] 7.5 Run `ruff check --fix` and `ruff format`

## 8. Project, Component, PurchaseConfig

- [x] 8.1 Implement `Component` (strict) with `id`, `name`, `quantity: int ≥ 1`, `volume`, `preset_id`, `preset_version`, computed `net_volume_l`
- [x] 8.2 Implement `PurchaseConfig` (strict) with documented defaults
- [x] 8.3 Implement `Project` (strict) with `schema_version: Literal[1]`, `id`, `name`, `shape: Literal["single", "machine"]`, `created_at`, `updated_at`, non-empty `components`, `purchase`, plus model-level validator enforcing exactly one component when `shape == "single"`
- [x] 8.4 Add unit tests for every "Component model", "Project purchase configuration", and "Project model" spec scenario
- [x] 8.5 Run `ruff check --fix` and `ruff format`

## 9. Project file load, save, version mismatch, default-excluded seed

- [x] 9.1 Implement `load_project(path, catalog)` returning a `ProjectLoadResult` (the `Project` plus a list of `CatalogVersionMismatch`)
- [x] 9.2 Implement `save_project(project, path)` that updates `updated_at` to UTC `now`, drops derived fields, and writes deterministic YAML (sorted keys for stable diffs)
- [x] 9.3 Implement `new_project(name, shape, catalog)` constructor seeding `purchase.excluded_materials` from `Material.default_excluded`
- [x] 9.4 Add unit tests for "Project file load and save", "Catalog version mismatch detection", "Default-excluded materials seed" spec scenarios, including round-tripping the normative YAML example from `docs/user-flow.md`
- [x] 9.5 Run `ruff check --fix` and `ruff format`

## 10. Documentation and validation

- [x] 10.1 Update `docs/STACK.md` with `pyyaml` and the bundled-catalog packaging note
- [x] 10.2 Update `CHANGELOG.md` `[Unreleased]` block under `### Added` with one bullet for the domain core
- [x] 10.3 Run `pytest --cov=mixsheet.domain` and confirm coverage ≥ 95% for the new package
- [x] 10.4 Run `pyright` and resolve any type errors in `src/mixsheet/domain/`
- [x] 10.5 Run `openspec validate --change add-domain-models` and resolve any issues
