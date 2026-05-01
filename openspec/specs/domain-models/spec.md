# domain-models Specification

## Purpose
TBD - created by archiving change add-domain-models. Update Purpose after archive.
## Requirements
### Requirement: Material catalog model

The system SHALL represent each catalog material as a strict, frozen
value object with a stable identifier, a human-readable name, a
category string, and a `default_excluded` boolean defaulting to
`false`. Two materials in the same catalog MUST NOT share an `id`.

#### Scenario: Loads a material with default excluded set

- **WHEN** a catalog row declares `id: water`, `name: Water`,
  `category: liquid`, `default_excluded: true`
- **THEN** the loaded `Material` exposes `default_excluded == True`

#### Scenario: Rejects duplicate material identifiers

- **WHEN** a catalog declares two materials with `id: cement`
- **THEN** the catalog loader raises a validation error referencing the
  duplicate id

#### Scenario: Rejects an empty material id

- **WHEN** a catalog row declares `id: ""`
- **THEN** the catalog loader raises a validation error

### Requirement: Material proportion model

The system SHALL represent a single material's share of a mix as a
strict, frozen value object holding a `material_id` and a `proportion`
expressed as a `Decimal` strictly greater than `0` and less than or
equal to `1`. The model MUST NOT carry the material's display name —
that is looked up from the materials list by id.

#### Scenario: Accepts a fractional proportion

- **WHEN** a row declares `material_id: cement` and `proportion: 0.3698`
- **THEN** the model loads with `proportion == Decimal("0.3698")`

#### Scenario: Rejects a proportion of zero

- **WHEN** a row declares `proportion: 0`
- **THEN** validation fails with a message stating proportion must be
  greater than zero

#### Scenario: Rejects a proportion above one

- **WHEN** a row declares `proportion: 1.0001`
- **THEN** validation fails with a message stating proportion must not
  exceed one

### Requirement: Mix preset model

The system SHALL represent a mix preset as a strict, frozen value
object with `id`, `name`, `version`, `density_kg_per_l` (`Decimal`,
strictly greater than zero), optional `description`, optional
`application`, and a non-empty list of `MaterialProportion` whose
proportions sum to `Decimal("1.0")` within an absolute tolerance of
`Decimal("0.0001")`.

#### Scenario: Loads a preset with summing proportions

- **WHEN** a preset declares four materials with proportions
  `0.0792 + 0.2772 + 0.5436 + 0.1000`
- **THEN** the preset loads successfully with `density_kg_per_l`
  exposed as a `Decimal`

#### Scenario: Rejects proportions that do not sum to one

- **WHEN** a preset declares proportions summing to `0.99`
- **THEN** validation fails with a message reporting the actual sum

### Requirement: Supplier and package models

The system SHALL represent a supplier as a strict, frozen value object
with `id` and `name`. A supplier package SHALL be a strict, frozen
value object with `id`, `material_id`, `supplier_id`, `weight_kg`
(`Decimal > 0`), and `price_incl_vat` (`Decimal ≥ 0`). Every package's
`material_id` MUST resolve to a material in the same catalog and its
`supplier_id` MUST resolve to a supplier in the same catalog.

#### Scenario: Loads a package and exposes derived price per kg

- **WHEN** a catalog declares a package with `weight_kg: 21.0` and
  `price_incl_vat: 84.10`
- **THEN** the package loads and exposes a `price_per_kg` `Decimal`
  value of `4.0047619...` rounded by `Decimal` semantics

#### Scenario: Rejects a package referencing an unknown material

- **WHEN** a package declares `material_id: nonexistent`
- **THEN** the catalog loader raises a validation error naming the
  missing material

#### Scenario: Rejects a package referencing an unknown supplier

- **WHEN** a package declares `supplier_id: nonexistent`
- **THEN** the catalog loader raises a validation error naming the
  missing supplier

### Requirement: Strategy enum

The system SHALL expose a string enum named `Strategy` with exactly the
members `cheapest`, `bulk_value`, and `minimal_waste`. The enum MUST
NOT include any other members in this change.

#### Scenario: Round-trips a known strategy

- **WHEN** code reads `Strategy("minimal_waste")`
- **THEN** the value equals `Strategy.MINIMAL_WASTE` and its string
  form is `"minimal_waste"`

#### Scenario: Rejects an unknown strategy

- **WHEN** code reads `Strategy("greedy")`
- **THEN** a `ValueError` is raised

### Requirement: Volume input modes

The system SHALL represent a component's volume as a discriminated
union over three modes selected by a `mode` field: `dimensions`
(`length_mm`, `width_mm`, `height_mm`, all `Decimal > 0`),
`area_height` (`area_mm2 > 0`, `height_mm > 0`), and `direct`
(`volume_l > 0`). Every variant MUST expose a `volume_l: Decimal`
computed field that returns the litre equivalent using
`1 L = 1_000_000 mm³`.

#### Scenario: Computes volume from rectangular dimensions

- **WHEN** a `Volume` is constructed with `mode: dimensions`,
  `length_mm: 800`, `width_mm: 400`, `height_mm: 120`
- **THEN** `volume_l` equals `Decimal("38.4")`

#### Scenario: Computes volume from area and height

- **WHEN** a `Volume` is constructed with `mode: area_height`,
  `area_mm2: 240000`, `height_mm: 80`
- **THEN** `volume_l` equals `Decimal("19.2")`

#### Scenario: Passes through a direct volume

- **WHEN** a `Volume` is constructed with `mode: direct`,
  `volume_l: 12.5`
- **THEN** `volume_l` equals `Decimal("12.5")`

#### Scenario: Rejects a non-positive dimension

- **WHEN** a `Volume` is constructed with `mode: dimensions` and
  `length_mm: 0`
- **THEN** validation fails

#### Scenario: Rejects fields from another mode

- **WHEN** a `Volume` is constructed with `mode: dimensions` and the
  payload also contains `area_mm2: 1000`
- **THEN** validation fails because the discriminated union rejects
  the unknown field

### Requirement: Component model

The system SHALL represent a single pourable part as a strict value
object with `id`, `name`, `quantity` (integer ≥ 1), `volume`
(`Volume`), `preset_id` (string), and `preset_version` (string pinned
at save time). The model MUST expose a `net_volume_l` derived as
`volume.volume_l × quantity`.

#### Scenario: Computes net volume across quantity

- **WHEN** a component has `quantity: 3` and `volume.volume_l: 12.5`
- **THEN** `net_volume_l` equals `Decimal("37.5")`

#### Scenario: Rejects quantity below one

- **WHEN** a component is constructed with `quantity: 0`
- **THEN** validation fails

#### Scenario: Rejects a missing preset version

- **WHEN** a component is constructed without `preset_version`
- **THEN** validation fails

### Requirement: Project purchase configuration

The system SHALL represent the project-level purchase configuration as
a strict value object with `overage_pct` (`Decimal ≥ 0`, default
`Decimal("0.10")`), `strategy` (`Strategy`, default
`Strategy.CHEAPEST`), and `excluded_materials` (list of material id
strings, default empty).

#### Scenario: Defaults match documented values

- **WHEN** a `PurchaseConfig` is constructed without arguments
- **THEN** `overage_pct == Decimal("0.10")`, `strategy ==
  Strategy.CHEAPEST`, and `excluded_materials == []`

#### Scenario: Rejects negative overage

- **WHEN** a `PurchaseConfig` is constructed with `overage_pct: -0.05`
- **THEN** validation fails

### Requirement: Project model

The system SHALL represent a project as a strict value object with
`schema_version: int` (currently `1`), `id`, `name`, `shape`
(`single` or `machine`), `created_at` and `updated_at` (timezone-aware
datetimes), a non-empty list of `Component`, and a `purchase`
(`PurchaseConfig`). When `shape == "single"` the project MUST contain
exactly one component.

#### Scenario: Accepts a single-component project

- **WHEN** a project is constructed with `shape: single` and one
  component
- **THEN** validation passes

#### Scenario: Rejects a single-shape project with multiple components

- **WHEN** a project is constructed with `shape: single` and two
  components
- **THEN** validation fails

#### Scenario: Rejects an unsupported schema version

- **WHEN** a project payload sets `schema_version: 2`
- **THEN** validation fails with a message naming the supported
  version

### Requirement: Catalog file with version

The system SHALL represent a catalog file as a strict object with a
top-level `catalog_version` (string in `YYYY-MM-DD` form) plus the
materials, presets, suppliers, and packages it contains. A catalog
MUST be rejected when `catalog_version` is missing or malformed.

#### Scenario: Loads a catalog with a valid version

- **WHEN** a catalog YAML declares `catalog_version: "2026-05-01"`
- **THEN** the loaded catalog exposes that version as a string

#### Scenario: Rejects a catalog without a version

- **WHEN** a catalog YAML omits `catalog_version`
- **THEN** the loader raises a validation error naming the missing
  field

#### Scenario: Rejects a malformed catalog version

- **WHEN** a catalog YAML declares `catalog_version: "May 2026"`
- **THEN** the loader raises a validation error referencing the date
  format

### Requirement: Fail-fast catalog loader

The system SHALL load presets and suppliers from YAML files via
`yaml.safe_load`, validate every model, and raise a single aggregated
error at process start if any of the following hold: a preset
references an unknown material id; a package references an unknown
material id; a package references an unknown supplier id; a preset's
proportions do not sum to one; a duplicate id appears among materials,
presets, suppliers, or packages.

#### Scenario: Loads a clean catalog without raising

- **WHEN** the bundled `presets.yaml` and `suppliers.yaml` are loaded
- **THEN** the loader returns a populated catalog without error

#### Scenario: Reports an unknown material in a preset

- **WHEN** a preset row declares `material_id: phantom` not in
  `materials:`
- **THEN** the loader raises an error naming both the preset id and
  the unknown material id

#### Scenario: Refuses unsafe YAML tags

- **WHEN** a catalog file contains a Python-object YAML tag such as
  `!!python/object:os.system`
- **THEN** the loader raises an error from `safe_load` rather than
  executing the tag

### Requirement: Project file load and save

The system SHALL load a project from a YAML file using
`yaml.safe_load`, validate it against the `Project` model, and save a
project back to YAML such that loading the saved file reproduces the
same input fields. Derived fields (`Volume.volume_l`,
`Component.net_volume_l`) MUST NOT be written to disk.

#### Scenario: Round-trips the normative example

- **WHEN** the loader reads the normative YAML example from
  `docs/user-flow.md` and the saver writes it back
- **THEN** loading the saved file yields a `Project` whose inputs
  equal the original, and the file contains no `volume_l` or
  `net_volume_l` keys

#### Scenario: Updates `updated_at` on save

- **WHEN** a project is saved
- **THEN** the in-memory `updated_at` is replaced with the current
  UTC time before serialization

#### Scenario: Rejects a JSON file with the wrong schema version

- **WHEN** the loader reads a project payload with `schema_version: 2`
- **THEN** loading raises a validation error naming the supported
  version

### Requirement: Catalog version mismatch detection

The system SHALL compare every component's pinned `preset_version`
against the version of the same `preset_id` in the loaded catalog and
return a structured list of mismatches alongside the loaded project.
The mismatch list MUST include each component's `id`, the `preset_id`,
the pinned version, and the catalog version. The loader MUST NOT
mutate the project file when mismatches occur.

#### Scenario: Returns no mismatches for an aligned project

- **WHEN** every component's `preset_version` equals the catalog
  version of its preset
- **THEN** the load result reports an empty mismatch list

#### Scenario: Reports a mismatched preset version

- **WHEN** a component pins `preset_version: 1.0.0` but the catalog
  ships version `1.1.0` for that preset
- **THEN** the load result reports one mismatch entry naming the
  component, preset id, pinned version `1.0.0`, and catalog version
  `1.1.0`

### Requirement: Default-excluded materials seed

The system SHALL, when constructing a fresh `Project`, seed
`purchase.excluded_materials` with the ids of every catalog material
whose `default_excluded` is `true`. Loading an existing project file
MUST preserve whatever `excluded_materials` the file contains without
auto-augmentation.

#### Scenario: Seeds water on a new project

- **WHEN** a new `Project` is constructed against a catalog where
  `water.default_excluded` is `true`
- **THEN** `purchase.excluded_materials` contains `"water"`

#### Scenario: Preserves a hand-edited excluded list

- **WHEN** a project file declares `excluded_materials: []` and the
  catalog has `water.default_excluded: true`
- **THEN** the loaded project reports `excluded_materials == []`

### Requirement: Display precision constants

The system SHALL expose precision constants for downstream renderers:
`QUANTITY_DECIMALS_LOW = 1` and `QUANTITY_DECIMALS_HIGH = 0` switching
at `QUANTITY_THRESHOLD = Decimal("10")` (values strictly greater than
ten use the high constant; values less than or equal to ten use the
low constant); `PRICE_DECIMALS = 2`; `PERCENT_DECIMALS = 0`. No
formatting helpers are part of this capability.

#### Scenario: Constants take their documented values

- **WHEN** `mixsheet.domain.display` is imported
- **THEN** `QUANTITY_DECIMALS_LOW == 1`, `QUANTITY_DECIMALS_HIGH == 0`,
  `QUANTITY_THRESHOLD == Decimal("10")`, `PRICE_DECIMALS == 2`, and
  `PERCENT_DECIMALS == 0`
