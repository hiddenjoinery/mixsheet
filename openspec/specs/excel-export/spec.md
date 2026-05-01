# excel-export Specification

## Purpose
TBD - created by archiving change add-excel-export. Update Purpose after archive.
## Requirements
### Requirement: Excel export contract

The system SHALL expose two pure write functions —
`write_purchase_workbook` and `write_mixsheet_workbook` — that
consume frozen domain views plus a project header and produce
`.xlsx` workbooks at caller-supplied filesystem paths. Both
functions MUST NOT mutate inputs, MUST NOT read other files, and
MUST be deterministic across repeated calls with equal inputs (modulo
xlsxwriter-emitted timestamps where unavoidable). Both functions
MUST raise a focused `ImportError`-derived error with an install
hint when the optional `xlsxwriter` extra is not installed.

#### Scenario: Writes a purchase workbook from a single-supplier view

- **WHEN** `write_purchase_workbook` runs with a `PurchaseListView`
  carrying one supplier and one material, and an output path
- **THEN** an `.xlsx` file is created at the path containing one
  Overview sheet and one supplier sheet, and the input view is not
  mutated

#### Scenario: Writes a mix-sheet workbook from one component view

- **WHEN** `write_mixsheet_workbook` runs with a one-element list of
  `ComponentMixSheetView`
- **THEN** an `.xlsx` file is created containing exactly one
  component sheet, and the input list is not mutated

#### Scenario: Reproducible across calls

- **WHEN** either writer runs twice with the same input
- **THEN** the parsed-cell content of both produced workbooks is
  identical (sheet names, row counts, every cell value and number
  format)

#### Scenario: Missing optional extra surfaces a focused error

- **WHEN** either writer is invoked in an environment without
  `xlsxwriter` installed
- **THEN** the function raises an error whose message names the
  install command for the export extra

### Requirement: Purchase workbook layout

`write_purchase_workbook` SHALL produce a workbook with one
`Overview` sheet followed by one sheet per supplier in the input
view's `suppliers` order (alphabetical by `supplier_id`). The
`Overview` sheet MUST contain three blocks in this order: a header
block (project name, strategy, overage, generation date), a
per-material table sourced from `PurchaseListView.materials`, and a
per-supplier table sourced from `PurchaseListView.suppliers`. Each
supplier sheet MUST contain a header line (supplier name + project
name) and a single material table with columns
`material`, `package`, `count`, `€ each`, `€ row`, plus a subtotal
row.

#### Scenario: Overview shows a per-material row for each parent line item

- **WHEN** the input view has `materials` of length 3
- **THEN** the Overview sheet's per-material table has exactly 3
  data rows (excluding header and totals row), in input order

#### Scenario: Cross-supplier material reports both suppliers in Overview

- **WHEN** a `PurchaseLineItemSummaryView` reports `suppliers ==
  "acme + beta"`
- **THEN** the Overview sheet's per-material row for that material
  shows `"acme + beta"` in the `Suppliers` column verbatim

#### Scenario: Per-supplier sheet hides cross-supplier markers

- **WHEN** a material is split across two suppliers
- **THEN** each supplier's sheet shows only that supplier's slice
  (one row, the slice's package, count, € each, € row) and no
  marker indicating the cross-supplier split

#### Scenario: Supplier sheets follow the alphabetical order of the view

- **WHEN** the input view has suppliers `["acme", "bcs", "delta"]`
- **THEN** the workbook's sheets after `Overview` are `Acme`, `Bcs`,
  `Delta` in that order

### Requirement: Mix-sheet workbook layout

`write_mixsheet_workbook` SHALL produce a workbook with one sheet
per `ComponentMixSheetView` in the input list, in the same order as
the list. Each component sheet MUST contain a header block
(project name, component name, preset name + version, volume per
component, quantity, density, total weight) followed by a single
material table with columns `material`, `required` plus a totals
row that echoes the view's `total_weight_kg`.

#### Scenario: One sheet per component, in input order

- **WHEN** the input list has views for `[bed, cross-slide]`
- **THEN** the workbook has exactly two sheets named after the
  components in that order

#### Scenario: Component sheet echoes view header data

- **WHEN** a `ComponentMixSheetView` reports `quantity == 2` and
  `volume_per_component_l == Decimal("19.2")`
- **THEN** the component sheet's header block contains both values
  in their formatted form (`"2"` and `"19.2"`)

### Requirement: Tab names derive from name with id fallback and 31-char limit

Sheet tabs SHALL prefer the human-readable supplier or component
name. When the name is empty, the writer MUST fall back to the
matching id. The writer MUST replace each Excel-forbidden character
(`[`, `]`, `:`, `*`, `?`, `/`, `\`) with `_`. Names exceeding 31
characters MUST be truncated to 31; when truncation produces a
collision with another tab, the writer MUST append a deterministic
`~N` numeric suffix (starting at `~2`) inside the 31-char budget.

#### Scenario: Long supplier name truncates to 31 chars

- **WHEN** a supplier's name is `"Acme Industrial Supplies and Concrete Mix Co."`
- **THEN** the supplier's tab name is exactly 31 characters and
  prefixes the original name

#### Scenario: Forbidden characters are sanitised

- **WHEN** a component is named `"bed/main"`
- **THEN** the sheet tab is named `"bed_main"`

#### Scenario: Truncation collisions resolve deterministically

- **WHEN** two suppliers truncate to the same 31-char prefix
- **THEN** the second supplier's tab gains a `~2` suffix (and the
  first is unchanged), with the suffix counted inside the 31-char
  budget

### Requirement: Per-cell number formats mirror the renderer's threshold

The writer SHALL apply Excel number formats per cell. Quantity cells
MUST use the format `"0.0"` when the absolute raw value is at or
below `QUANTITY_THRESHOLD`, and `"0"` when the absolute raw value is
strictly above the threshold. Price cells MUST use the format
`"€ #,##0.00"`. Cells receive the raw `Decimal` value from the view,
not the formatted string, so the spreadsheet stores numbers
natively.

#### Scenario: A 9.6 kg cell is written as a number with format "0.0"

- **WHEN** a row reports `purchased_kg == Decimal("9.6")`
- **THEN** the corresponding cell holds the number `9.6` and uses
  the number format `"0.0"`

#### Scenario: A 124 kg cell is written as a number with format "0"

- **WHEN** a row reports `purchased_kg == Decimal("124")`
- **THEN** the corresponding cell holds the number `124` and uses
  the number format `"0"`

#### Scenario: A price cell uses the euro format

- **WHEN** a row reports `cost_incl_vat == Decimal("36.00")`
- **THEN** the corresponding cell holds the number `36` and uses
  the number format `"€ #,##0.00"`

### Requirement: Optional dependency boundary

`xlsxwriter` SHALL be declared under
`[project.optional-dependencies] export` in `pyproject.toml` and
SHALL NOT be imported at module top-level. Both writer functions
MUST import `xlsxwriter` lazily inside the function body so the
core package installs and runs without the extra. The error raised
on missing import MUST name the install command (`uv add
mixsheet[export]`).

#### Scenario: Core package import does not require the extra

- **WHEN** the package is installed without the `export` extra
- **THEN** importing `mixsheet`, `mixsheet.domain`, and
  `mixsheet.export` succeeds without raising

#### Scenario: Writer invocation without the extra raises the install hint

- **WHEN** `xlsxwriter` is absent from the environment and either
  writer is invoked
- **THEN** the raised error's message includes the literal string
  `"uv add mixsheet[export]"`
