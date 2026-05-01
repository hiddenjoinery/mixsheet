# mixsheet-rendering Specification

## Purpose
TBD - created by archiving change add-excel-export. Update Purpose after archive.
## Requirements
### Requirement: Component mix-sheet rendering contract

The system SHALL expose a pure function
`render_component_mixsheet` that, given a frozen
`ComponentBreakdown`, returns a frozen `ComponentMixSheetView`
describing the same component decorated with display-rounded string
fields. The function MUST NOT mutate inputs, MUST NOT perform I/O,
and MUST be deterministic across repeated calls with equal inputs.

#### Scenario: Returns a frozen view for a single-component breakdown

- **WHEN** the input is a valid `ComponentBreakdown` with one
  material row
- **THEN** the result is a frozen `ComponentMixSheetView` carrying
  one entry under `materials`

#### Scenario: Does not mutate inputs and is reproducible

- **WHEN** the renderer runs against any valid `ComponentBreakdown`
- **THEN** the input is not mutated, and a second call with the
  same argument returns an equal `ComponentMixSheetView`

### Requirement: Mix-sheet view header carries component context

`ComponentMixSheetView` SHALL expose `component_id`,
`component_name`, `preset_id`, `preset_name`, raw `Decimal`
`density_kg_per_l`, `quantity` (int), raw + formatted
`volume_per_component_l`, `net_volume_l`,
`weight_per_component_kg`, and `total_weight_kg`. Quantities MUST
follow the per-cell threshold rule from
`mixsheet.domain.display`. Density MUST be exposed as both raw
`Decimal` and a string formatted to two decimal places (for
human-readable headers).

#### Scenario: Threshold applies to volume cells

- **WHEN** `volume_per_component_l == Decimal("9.6")` and
  `total_weight_kg == Decimal("124")`
- **THEN** `volume_per_component_l_display == "9.6"` and
  `total_weight_kg_display == "124"`

#### Scenario: Density formats to two decimals

- **WHEN** `density_kg_per_l == Decimal("1.91")`
- **THEN** `density_kg_per_l_display == "1.91"`

### Requirement: Mix-sheet view materials list mirrors breakdown order

`ComponentMixSheetView.materials` SHALL contain one
`MixSheetMaterialRow` per `MaterialBreakdownRow` in the input
component, in the same order. Each row MUST expose `material_id`,
`material_name`, raw + formatted `weight_per_component_kg` and
`weight_kg` (the row's per-component and total contributions).

#### Scenario: Preserves material order

- **WHEN** the input component lists materials in the order
  `["aggregate", "cement", "epoxy"]`
- **THEN** the view's `materials` list reports them in the same
  order

#### Scenario: Per-row weights carry both raw and formatted values

- **WHEN** a material row reports `weight_kg == Decimal("12.345678")`
- **THEN** the matching `MixSheetMaterialRow` exposes `weight_kg ==
  Decimal("12.345678")` and `weight_kg_display == "12"` (above
  threshold)

### Requirement: Total weight echoed without recomputation

`ComponentMixSheetView.total_weight_kg` SHALL equal the input
`ComponentBreakdown.total_weight_kg` exactly at full `Decimal`
precision. The renderer MUST NOT recompute the total from the
material rows.

#### Scenario: Echoes the breakdown total

- **WHEN** the input reports `total_weight_kg == Decimal("6.30")`
- **THEN** the view exposes `total_weight_kg == Decimal("6.30")`
  and `total_weight_kg_display == "6.3"`
