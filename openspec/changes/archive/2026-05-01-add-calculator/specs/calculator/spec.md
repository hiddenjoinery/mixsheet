## ADDED Requirements

### Requirement: Component breakdown contract

The system SHALL expose a pure function that, given a single `Component` and a `Catalog`, returns a strict, frozen `ComponentBreakdown` describing per-material weights derived from the catalog preset's density and proportions. The function MUST NOT mutate its inputs and MUST NOT perform any I/O.

#### Scenario: Computes weights from a dimensions volume

- **WHEN** a component has `volume.mode: dimensions` with `length_mm: 800`, `width_mm: 400`, `height_mm: 120`, `quantity: 1`, and `preset_id` resolving to a preset with `density_kg_per_l: Decimal("1.91")`
- **THEN** the breakdown reports `volume_per_component_l == Decimal("38.4")`, `net_volume_l == Decimal("38.4")`, `weight_per_component_kg == Decimal("38.4") * Decimal("1.91")`, and `total_weight_kg == weight_per_component_kg`

#### Scenario: Computes weights from an area-and-height volume

- **WHEN** a component has `volume.mode: area_height` with `area_mm2: 240000`, `height_mm: 80`, `quantity: 1`, and a preset with density `Decimal("0.88")`
- **THEN** the breakdown reports `volume_per_component_l == Decimal("19.2")` and `total_weight_kg == Decimal("19.2") * Decimal("0.88")`

#### Scenario: Computes weights from a direct volume

- **WHEN** a component has `volume.mode: direct` with `volume_l: Decimal("12.5")` and `quantity: 1`
- **THEN** the breakdown reports `volume_per_component_l == Decimal("12.5")` and `net_volume_l == Decimal("12.5")`

#### Scenario: Multiplies net volume and total weight by quantity

- **WHEN** a component has `volume_per_component_l == Decimal("12.5")` and `quantity: 3`
- **THEN** the breakdown reports `net_volume_l == Decimal("37.5")` and `total_weight_kg == Decimal("37.5") * density`

### Requirement: Material rows derive from preset proportions

The system SHALL emit one `MaterialBreakdownRow` per material in the resolved preset. Each row MUST set `weight_kg = total_weight_kg × proportion` and `weight_per_component_kg = weight_per_component_kg_total × proportion`, where the per-component weight base equals `volume_per_component_l × density`.

#### Scenario: Distributes total weight across materials by proportion

- **WHEN** a preset declares two materials with proportions `Decimal("0.4")` and `Decimal("0.6")` and the breakdown's `total_weight_kg` is `Decimal("10")`
- **THEN** the breakdown's material rows report `weight_kg` of `Decimal("4")` and `Decimal("6")` respectively

#### Scenario: Material weights sum back to total weight

- **WHEN** a breakdown is produced for any catalog preset whose proportions sum to `Decimal("1.0")`
- **THEN** the sum of every row's `weight_kg` equals the breakdown's `total_weight_kg` exactly under `Decimal` arithmetic

### Requirement: Material name lookup via catalog

The system SHALL populate each `MaterialBreakdownRow.material_name` by looking up the material in the supplied catalog (`Catalog.material_by_id`). The preset's proportion entries MUST NOT carry a `material_name` field.

#### Scenario: Denormalises material name into the row

- **WHEN** a preset row references `material_id: cement` and the catalog defines `Material(id="cement", name="Portland cement", ...)`
- **THEN** the breakdown's matching row reports `material_name == "Portland cement"`

### Requirement: Full-precision decimal arithmetic

The system SHALL preserve full `Decimal` precision throughout the calculator. Intermediate products and the values stored on the returned `ComponentBreakdown` MUST NOT be rounded or quantised by the calculator. Display rounding belongs to the renderer layer.

#### Scenario: Does not quantise weight values

- **WHEN** a breakdown is produced for a component whose arithmetic yields a weight with more than two decimal places (e.g. `Decimal("0.4761904761904761904761904761")`)
- **THEN** the matching `MaterialBreakdownRow.weight_kg` retains the unrounded value rather than `Decimal("0.48")`

### Requirement: Alphabetical material ordering

The system SHALL return material rows sorted by `material_name` in case-insensitive ascending order, regardless of the order they appear in the preset. Ordering MUST be stable across repeated calls with the same inputs.

#### Scenario: Sorts rows by material name independent of preset order

- **WHEN** a preset lists materials in the order `["Quartz sand", "Aggregate fines", "Hardener"]` and the breakdown is produced
- **THEN** the breakdown's material rows appear in the order `["Aggregate fines", "Hardener", "Quartz sand"]`

### Requirement: Unknown preset error

The system SHALL raise an `UnknownPresetError` when the supplied catalog does not contain a preset whose `id` matches `component.preset_id`. The error message MUST include the offending `preset_id`.

#### Scenario: Raises when the preset id is missing from the catalog

- **WHEN** a component references `preset_id: "phantom-mix"` and the catalog defines no such preset
- **THEN** calling the calculator raises `UnknownPresetError` whose message contains `"phantom-mix"`

### Requirement: Catalog preset wins over pinned version

The system SHALL compute against the preset currently in the supplied catalog, regardless of whether the component's pinned `preset_version` matches the catalog version. The calculator MUST NOT raise on a version mismatch; mismatch detection is the responsibility of the project loader.

#### Scenario: Calculates against the catalog when versions diverge

- **WHEN** a component pins `preset_version: "1.0.0"` but the supplied catalog ships the same `preset_id` at version `"1.1.0"` with different proportions
- **THEN** the breakdown reflects the `1.1.0` proportions and density, and no error is raised

### Requirement: Excluded materials are not filtered

The system SHALL include every material declared in the preset in the breakdown's material rows, irrespective of any `purchase.excluded_materials` setting on a project. Filtering excluded materials is the responsibility of the purchase optimizer, not the calculator.

#### Scenario: Includes a default-excluded material in the breakdown

- **WHEN** a preset declares `water` and the catalog marks `water.default_excluded: true`
- **THEN** the breakdown's material rows include a row for `water`
