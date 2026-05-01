## ADDED Requirements

### Requirement: Purchase rendering contract

The system SHALL expose a pure function that, given a frozen
`PurchaseList`, returns a frozen `PurchaseListView` describing the
same purchase information regrouped by supplier and decorated with
display-rounded string fields. The function MUST NOT mutate any
input, MUST NOT perform I/O, and MUST be deterministic across
repeated calls with equal inputs.

#### Scenario: Returns a frozen view for a single-supplier purchase list

- **WHEN** the input `PurchaseList` carries one line item with one
  allocation from supplier `A`
- **THEN** the result is a frozen `PurchaseListView` containing one
  `SupplierGroupView` whose `supplier_id == "A"` and whose
  `line_items` list reports that allocation

#### Scenario: Does not mutate inputs and is reproducible

- **WHEN** the renderer runs against any valid `PurchaseList`
- **THEN** the input is not mutated, and a second call with the same
  argument returns an equal `PurchaseListView`

### Requirement: Supplier grouping fans out cross-supplier line items

The system SHALL emit one `PurchaseLineItemView` per
`PurchaseAllocation` in the input, placed under the
`SupplierGroupView` matching the allocation's `supplier_id`. When a
single input `PurchaseLineItem` allocates packages from multiple
suppliers, its allocations MUST be split across the corresponding
supplier groups. Each `PurchaseLineItemView` MUST carry the parent
`material_id` and `material_name` so cross-supplier rows remain
attributable.

#### Scenario: Splits a cross-supplier line item into two rows

- **WHEN** an input line item for `material_id == "cement"` allocates
  one package from supplier `A` (€30.00) and one package from supplier
  `B` (€6.00)
- **THEN** the view emits one `PurchaseLineItemView` for `cement`
  under supplier `A` reporting `allocation_cost_incl_vat ==
  Decimal("30.00")` and one under supplier `B` reporting
  `allocation_cost_incl_vat == Decimal("6.00")`

#### Scenario: Keeps a single-supplier line item as one row

- **WHEN** an input line item allocates two packages from supplier `A`
  only
- **THEN** the view emits exactly one `PurchaseLineItemView` under
  supplier `A` reporting `package_count == 2` and the line item's full
  `cost_incl_vat`

### Requirement: Supplier-group ordering is alphabetical and stable

The system SHALL order `PurchaseListView.suppliers` alphabetically by
`supplier_id`. Repeated calls with the same input MUST produce the
same ordering.

#### Scenario: Orders three suppliers alphabetically

- **WHEN** the input purchase list draws from suppliers `bcs`, `acme`,
  and `delta`
- **THEN** the view's `suppliers` list reports them in the order
  `["acme", "bcs", "delta"]`

### Requirement: Line-item ordering preserves the input order within each supplier

The system SHALL list each supplier group's `line_items` in the same
order as the matching allocations appear in
`PurchaseList.line_items`. The renderer MUST NOT re-sort, deduplicate,
or merge rows beyond the supplier-group split.

#### Scenario: Preserves input order across two suppliers

- **WHEN** the input `line_items` order is `["aggregate-fines",
  "cement", "quartz-sand"]` and `cement` is the only material drawing
  from supplier `B`
- **THEN** supplier `A`'s group lists `aggregate-fines` before
  `quartz-sand`, and supplier `B`'s group lists `cement` alone

### Requirement: Per-cell quantity precision switches at the threshold

The system SHALL format every quantity cell (required, purchased,
waste, package weight) using `QUANTITY_DECIMALS_LOW` decimals when the
absolute value is less than or equal to `QUANTITY_THRESHOLD`, and
`QUANTITY_DECIMALS_HIGH` decimals when the absolute value is strictly
greater than `QUANTITY_THRESHOLD`. The switch MUST apply per cell, not
per column. Display rounding MUST use `ROUND_HALF_UP`.

#### Scenario: Rounds a 9.99 kg cell to one decimal

- **WHEN** an allocation reports `purchased_kg == Decimal("9.99")`
- **THEN** its formatted string reports `"10.0"` (one decimal,
  half-up)

#### Scenario: Rounds a 10.00 kg cell to one decimal

- **WHEN** an allocation reports `purchased_kg == Decimal("10.00")`
- **THEN** its formatted string reports `"10.0"` (still at or below
  the threshold)

#### Scenario: Rounds a 10.01 kg cell to zero decimals

- **WHEN** an allocation reports `purchased_kg == Decimal("10.01")`
- **THEN** its formatted string reports `"10"` (strictly above the
  threshold)

#### Scenario: Mixed-magnitude column keeps per-cell precision

- **WHEN** one row reports `purchased_kg == Decimal("9.6")` and a
  sibling row reports `purchased_kg == Decimal("124")`
- **THEN** the formatted strings report `"9.6"` and `"124"`
  respectively

### Requirement: Price cells use the price-decimals constant

The system SHALL format every monetary cell (per-row allocation cost,
supplier subtotal, grand total) using `PRICE_DECIMALS` decimals with
`ROUND_HALF_UP`. The currency symbol MUST be `€` and MUST appear in
the formatted string, separated from the numeric body by a single
space.

#### Scenario: Formats a price at two decimals with the euro symbol

- **WHEN** a cell carries `Decimal("30")`
- **THEN** the formatted string reports `"€ 30.00"`

#### Scenario: Half-up rounding at the second decimal

- **WHEN** a cell carries `Decimal("30.005")`
- **THEN** the formatted string reports `"€ 30.01"`

### Requirement: Raw and formatted fields appear together on every numeric cell

The system SHALL expose, for every numeric cell on the view (quantity
cells, price cells), both the raw `Decimal` value and the formatted
string. The raw `Decimal` MUST equal the corresponding value on the
input `PurchaseList` without quantisation; the formatted string MUST
be derived solely from that raw value and the constants in
`mixsheet.domain.display`.

#### Scenario: Raw Decimal preserves full precision

- **WHEN** an input `PurchaseLineItem` reports `required_kg ==
  Decimal("12.345678")`
- **THEN** the matching view row exposes `required_kg ==
  Decimal("12.345678")` and `required_kg_display == "12"` (above the
  threshold)

#### Scenario: Raw and formatted price stay in sync

- **WHEN** an allocation reports `cost_incl_vat == Decimal("36.00")`
- **THEN** the view exposes `allocation_cost_incl_vat ==
  Decimal("36.00")` and `allocation_cost_incl_vat_display == "€
  36.00"`

### Requirement: Supplier subtotals carried through the view

The system SHALL place each input `SupplierSubtotal` on its matching
`SupplierGroupView` as both raw `Decimal` (`subtotal_incl_vat`,
`item_count`) and formatted string (`subtotal_incl_vat_display`). The
renderer MUST NOT recompute the subtotal; it MUST reuse the value the
optimizer emitted.

#### Scenario: Echoes the optimizer's subtotal

- **WHEN** the input reports `SupplierSubtotal(supplier_id="A",
  subtotal_incl_vat=Decimal("100.00"), item_count=3)`
- **THEN** supplier `A`'s group reports `subtotal_incl_vat ==
  Decimal("100.00")`, `item_count == 3`, and
  `subtotal_incl_vat_display == "€ 100.00"`

#### Scenario: Per-row allocation costs within a group sum to the subtotal

- **WHEN** any view is produced
- **THEN** for each `SupplierGroupView`, the sum of its line items'
  `allocation_cost_incl_vat` values equals
  `subtotal_incl_vat` exactly at full `Decimal` precision

### Requirement: Grand totals carried through the view

The system SHALL expose `total_cost_incl_vat` and `total_waste_kg`
on `PurchaseListView` as both raw `Decimal` (matching the input
`PurchaseList`) and formatted string. The renderer MUST NOT
recompute the totals.

#### Scenario: Echoes the optimizer's grand totals

- **WHEN** the input reports `total_cost_incl_vat == Decimal("136.00")`
  and `total_waste_kg == Decimal("2.5")`
- **THEN** the view exposes `total_cost_incl_vat == Decimal("136.00")`,
  `total_cost_incl_vat_display == "€ 136.00"`, `total_waste_kg ==
  Decimal("2.5")`, and `total_waste_kg_display == "2.5"`

#### Scenario: Sum of supplier subtotals equals the view's grand total

- **WHEN** any view is produced
- **THEN** the sum of every `SupplierGroupView.subtotal_incl_vat`
  equals `PurchaseListView.total_cost_incl_vat` exactly at full
  `Decimal` precision

### Requirement: Empty purchase list renders to an empty view

The system SHALL accept a `PurchaseList` with zero `line_items` and
zero `suppliers` (every material was excluded) and return a
`PurchaseListView` whose `suppliers` list is empty,
`total_cost_incl_vat == Decimal("0")`, and `total_waste_kg ==
Decimal("0")`. The renderer MUST NOT raise on the empty case.

#### Scenario: Empty input produces an empty view

- **WHEN** the input `PurchaseList` has no line items and no
  suppliers
- **THEN** the view's `suppliers` list is empty,
  `total_cost_incl_vat_display == "€ 0.00"`, and
  `total_waste_kg_display == "0.0"`
