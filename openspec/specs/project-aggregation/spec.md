# project-aggregation Specification

## Purpose

Pure domain capability that aggregates a loaded `Project` into a
`ProjectBreakdown` with combined volume, combined weight, per-component
breakdowns, and per-material totals with source attribution. Composes
on top of the `calculator` capability and provides the canonical demand
vector consumed by purchase optimization.

## Requirements

### Requirement: Project breakdown contract

The system SHALL expose a pure function that, given a `Project` and a
`Catalog`, returns a strict, frozen `ProjectBreakdown` describing
project-wide totals, the per-component breakdowns, and per-material
totals aggregated across components. The function MUST NOT mutate its
inputs and MUST NOT perform any I/O.

#### Scenario: Returns a frozen breakdown for a single-component project

- **WHEN** a project has `shape: single` with one component whose
  preset resolves in the catalog
- **THEN** the aggregator returns a `ProjectBreakdown` whose
  `shape == "single"`, `components` contains exactly one
  `ComponentBreakdown` matching `calculate_component`'s output for
  that component, and the model is frozen against mutation

#### Scenario: Returns a frozen breakdown for a machine project

- **WHEN** a project has `shape: machine` with two or more components
- **THEN** the aggregator returns a `ProjectBreakdown` whose
  `shape == "machine"` and whose `components` list preserves the
  order of `project.components`

#### Scenario: Does not mutate the input project or catalog

- **WHEN** the aggregator runs against any valid project and catalog
- **THEN** neither object is mutated, and re-running the aggregator
  with the same inputs yields an equal `ProjectBreakdown`

### Requirement: Per-component delegation to the calculator

The system SHALL produce each `ComponentBreakdown` in the result by
calling the existing single-component calculator. The aggregator MUST
NOT re-implement per-component arithmetic.

#### Scenario: Component breakdowns equal calculator output

- **WHEN** a project lists components `[c1, c2]` with presets
  resolving in the catalog
- **THEN** the aggregator's `components[0]` equals
  `calculate_component(c1, catalog)` and `components[1]` equals
  `calculate_component(c2, catalog)`

#### Scenario: Propagates UnknownPresetError from the calculator

- **WHEN** any component references a `preset_id` not present in the
  supplied catalog
- **THEN** the aggregator raises `UnknownPresetError` with the
  offending `preset_id` in its message

### Requirement: Project-wide volume and weight totals

The system SHALL set `total_net_volume_l` to the sum of every
component's `net_volume_l` and `total_weight_kg` to the sum of every
component's `total_weight_kg`, both at full `Decimal` precision with
no quantisation.

#### Scenario: Sums net volume across components

- **WHEN** a project has components with `net_volume_l` values
  `Decimal("38.4")` and `Decimal("19.2")`
- **THEN** the breakdown reports `total_net_volume_l == Decimal("57.6")`

#### Scenario: Sums total weight across components

- **WHEN** a project has components with `total_weight_kg` values
  `Decimal("73.344")` and `Decimal("16.896")`
- **THEN** the breakdown reports `total_weight_kg == Decimal("90.240")`

#### Scenario: Preserves full Decimal precision in totals

- **WHEN** component arithmetic yields weights with more than two
  decimal places (e.g. `Decimal("12.345678")` and
  `Decimal("0.000022")`)
- **THEN** `total_weight_kg` equals `Decimal("12.345700")` rather
  than a rounded `Decimal("12.35")`

### Requirement: Per-material aggregation across components

The system SHALL emit one `AggregatedMaterial` per distinct
`material_id` that appears in any component's breakdown. Each row's
`total_weight_kg` MUST equal the sum of every contributing component's
`MaterialBreakdownRow.weight_kg` for that material at full `Decimal`
precision.

#### Scenario: Sums one material across two components using different presets

- **WHEN** component `bed` (preset epoxy-mix) contributes
  `Decimal("20.85")` kg of `durigid-1-3` and component `cross-slide`
  (preset gantry-fill) contributes `Decimal("5.49")` kg of
  `durigid-1-3`
- **THEN** the breakdown's `materials` row for `durigid-1-3` reports
  `total_weight_kg == Decimal("26.34")`

#### Scenario: Sums one material across two components using the same preset

- **WHEN** components `a` and `b` both reference the same preset and
  contribute `Decimal("3.00")` kg each of `cement`
- **THEN** the breakdown's `materials` row for `cement` reports
  `total_weight_kg == Decimal("6.00")`

#### Scenario: Material totals sum back to project total weight

- **WHEN** a `ProjectBreakdown` is produced for any project whose
  preset proportions sum to `Decimal("1.0")`
- **THEN** the sum of every `AggregatedMaterial.total_weight_kg`
  equals the breakdown's `total_weight_kg` exactly under `Decimal`
  arithmetic

#### Scenario: Includes default-excluded materials in the aggregate

- **WHEN** any component's preset declares a material that the
  catalog marks `default_excluded: true` (e.g. `water`), and the
  project's `purchase.excluded_materials` lists that material
- **THEN** the aggregate row for that material is present with the
  summed `total_weight_kg`; the aggregator MUST NOT filter on
  `purchase.excluded_materials`

### Requirement: Material source attribution

The system SHALL attach to every `AggregatedMaterial` a non-empty
`sources` list of `AggregatedMaterialSource` entries. There MUST be
exactly one source entry per `(component_id, material_id)` pair that
contributes to the row, carrying that pair's `component_id`,
`preset_id`, and the contributing `weight_kg` at full `Decimal`
precision. Sources MUST appear in the order their components appear
in `project.components`.

#### Scenario: Lists one source per contributing component

- **WHEN** components `bed` and `cross-slide` both contribute to
  `durigid-1-3`
- **THEN** the `durigid-1-3` row's `sources` contains exactly two
  entries with `component_id` values `"bed"` and `"cross-slide"` in
  that order

#### Scenario: Source weights sum to material total

- **WHEN** an aggregated material has `sources` with `weight_kg`
  values `Decimal("20.85")` and `Decimal("5.49")`
- **THEN** the row's `total_weight_kg` equals the exact sum
  `Decimal("26.34")`

#### Scenario: Source preset id reflects the contributing component

- **WHEN** component `bed` references `preset_id: epoxy-mix` and
  contributes to `durigid-1-3`
- **THEN** that material's source entry for `bed` reports
  `preset_id == "epoxy-mix"`

#### Scenario: Sources preserve component order even when sorted material rows differ

- **WHEN** `project.components` is `[bed, cross-slide]` and the
  `materials` rows are sorted alphabetically by `material_name`
- **THEN** every `AggregatedMaterial.sources` list still appears in
  the order `[bed-source, cross-slide-source]` for materials that
  both components contribute to

### Requirement: Alphabetical material ordering

The system SHALL return `ProjectBreakdown.materials` sorted by
`material_name` in case-insensitive ascending order, regardless of
the order materials appear in any component's preset or in the
catalog. Ordering MUST be stable across repeated calls with the same
inputs.

#### Scenario: Sorts aggregated rows alphabetically by material name

- **WHEN** the contributing components yield materials in the order
  `["Quartz sand", "Aggregate fines", "Hardener"]`
- **THEN** `materials` appears in the order
  `["Aggregate fines", "Hardener", "Quartz sand"]`

### Requirement: Full-precision decimal arithmetic in aggregation

The system SHALL preserve full `Decimal` precision throughout
aggregation. Sums (project totals, material totals, source weights)
MUST NOT be rounded or quantised by the aggregator; renderers round
at display time.

#### Scenario: Does not quantise aggregated material totals

- **WHEN** components contribute `Decimal("0.4761904761904761904761904762")`
  and `Decimal("0.5238095238095238095238095238")` to the same material
- **THEN** the row's `total_weight_kg` equals
  `Decimal("1.0000000000000000000000000000")` rather than a rounded
  `Decimal("1.00")`

### Requirement: Project metadata echo

The system SHALL set `project_id`, `project_name`, and `shape` on the
returned `ProjectBreakdown` to the corresponding fields on the input
`Project`.

#### Scenario: Echoes project identity into the breakdown

- **WHEN** a project has `id: router-gantry-2026-05`,
  `name: Router gantry`, and `shape: machine`
- **THEN** the breakdown reports `project_id ==
  "router-gantry-2026-05"`, `project_name == "Router gantry"`, and
  `shape == "machine"`

### Requirement: Excluded materials and overage are not applied

The system SHALL ignore `project.purchase.overage_pct` and
`project.purchase.excluded_materials` during aggregation. The
aggregator's contract is the mix-sheet view ("what you pour"); the
purchase optimizer is responsible for applying overage and filtering
excluded materials.

#### Scenario: Total weight does not include overage

- **WHEN** a project has `purchase.overage_pct: Decimal("0.10")` and
  the calculator-derived `total_weight_kg` per component sums to
  `Decimal("90.24")`
- **THEN** `ProjectBreakdown.total_weight_kg` equals
  `Decimal("90.24")`, not `Decimal("99.264")`

#### Scenario: Excluded materials still appear in the aggregate

- **WHEN** a project has `purchase.excluded_materials: ["water"]`
  and at least one component's preset declares `water`
- **THEN** the breakdown's `materials` list contains a `water` row
  with the summed contribution
