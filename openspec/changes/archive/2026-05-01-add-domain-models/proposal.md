## Why

Phase 1 of the roadmap requires a typed domain core before any
calculator, optimizer, or wizard can be built. The CLI needs a Pydantic
v2 foundation that mirrors the project file format described in
`docs/user-flow.md`, with strict validation, Decimal-only arithmetic,
and fail-fast catalog loading at startup.

Locking the data model now prevents churn in every downstream change
(`add-calculator`, `add-purchase-optimizer`, `add-machine-aggregation`,
`add-interactive-wizard`, `add-export`) — they all consume the same
types.

## What Changes

- Add Pydantic v2 models for the project domain: `Project`, `Component`,
  `Volume` (three input modes: dimensions, area-and-height, direct),
  `MixPreset`, `Material`, `MaterialProportion`, `Supplier`,
  `SupplierPackage`, and a `Strategy` enum.
- All numeric fields use `Decimal`; no `int` grams or `float` shortcuts.
  Models are strict (`ConfigDict(strict=True, frozen=True)` where
  applicable).
- `Volume` exposes a `volume_l` computed field that derives litres from
  whichever input mode is active. Volume → material weights stays out of
  scope (lands in `add-calculator`).
- Add a YAML catalog loader that fails fast at startup when the catalog
  is malformed: unknown material IDs, proportions not summing to 1.0,
  duplicate IDs, packages referencing missing materials, or missing
  `catalog_version`.
- Add a project-file loader and saver (YAML, with optional JSON path)
  honouring `schema_version: 1` and round-tripping the normative example
  in `docs/user-flow.md` byte-equivalent on inputs.
- Ship the catalog YAML in the shape `docs/user-flow.md` § "Catalog
  cleanup vs old implementation" prescribes: no `material_name` inside
  preset rows, no `vat_rate` on suppliers, no `description` on
  packages, `water.default_excluded: true`, file-level
  `catalog_version` (date string), and a `density_kg_per_l` field on
  every preset.
- Add a `display` constants module with the FR-012 precision rules:
  quantities show 1 decimal when ≤ 10 and 0 above; prices show 2
  decimals; percentages show 0 decimals. Constants only — formatting
  helpers come with the wizard.
- Pin `preset_version` on every `Component` at save time and surface a
  mismatch when reopening a project against a newer catalog (warning
  payload only; the resolution UX lands in the wizard change).

### Non-goals

- No calculator: dimensions/volume → material weights stays in
  `add-calculator`.
- No optimizer or strategy implementation: `Strategy` is an enum only;
  `add-purchase-optimizer` provides the algorithms.
- No machine-level aggregation logic beyond the `Project.shape: machine`
  flag and a list of components: aggregate totals come with
  `add-machine-aggregation`.
- No Typer commands, Rich tables, or interactive prompts:
  `add-interactive-wizard` owns the CLI surface.
- No CSV/xlsx export: `add-export` owns artifact writers.
- No supplier price feeds, pour scheduling, or stock tracking — out of
  charter scope.

## Capabilities

### New Capabilities

- `domain-models`: typed project, catalog, and configuration models with
  strict Pydantic validation, Decimal arithmetic, YAML catalog/project
  loaders with fail-fast validation, and display-precision constants.

### Modified Capabilities

_None — this is the first capability spec in the repo._

## Impact

- **New code**: `src/mixsheet/domain/` package (project, catalog,
  display modules) and a `src/mixsheet/data/` directory holding
  `presets.yaml` and `suppliers.yaml` in the cleaned shape.
- **New dependencies**: `pyyaml` (catalog and project I/O). `pydantic`
  is already in scope per `STACK.md`.
- **Tests**: `tests/domain/` covering catalog load (happy path + each
  fail-fast case), project round-trip (load → save → reload byte-equal
  on inputs), Volume computed-field across the three modes, proportion
  sum validation, and display-precision constant values.
- **Docs**: `docs/STACK.md` notes `pyyaml`; `CHANGELOG.md` records
  Phase 1 domain core under `[Unreleased]`.
