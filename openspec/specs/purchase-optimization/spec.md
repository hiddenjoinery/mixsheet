# purchase-optimization Specification

## Purpose
TBD - created by archiving change add-purchase-optimization. Update Purpose after archive.
## Requirements
### Requirement: Purchase optimization contract

The system SHALL expose a pure function that, given a frozen
`ProjectBreakdown`, a `Catalog`, a `Strategy`, an `overage_pct`, and a
list of excluded `material_id` values, returns a frozen `PurchaseList`
describing the package allocations needed to cover every non-excluded
material in the breakdown. The function MUST NOT mutate any input,
MUST NOT perform I/O, and MUST be deterministic across repeated calls
with equal inputs.

#### Scenario: Returns a frozen purchase list for a single-material breakdown

- **WHEN** the breakdown contains one material with
  `total_weight_kg == Decimal("10")`, the catalog has one
  `SupplierPackage` of `weight_kg == Decimal("25")` and
  `price_incl_vat == Decimal("30.00")`, `overage_pct ==
  Decimal("0")`, and `strategy == Strategy.CHEAPEST`
- **THEN** the result is a frozen `PurchaseList` containing one
  `PurchaseLineItem` whose `allocations` lists exactly that package
  with `count == 1`, `purchased_kg == Decimal("25")`, and
  `cost_incl_vat == Decimal("30.00")`

#### Scenario: Does not mutate inputs and is reproducible

- **WHEN** the optimizer runs against any valid breakdown and
  catalog
- **THEN** neither object is mutated, and a second call with the same
  arguments returns an equal `PurchaseList`

### Requirement: Overage applied before package selection

The system SHALL multiply each material's `total_weight_kg` by
`(1 + overage_pct)` to derive the `required_with_overage_kg` value
that package selection MUST cover. The optimizer MUST NOT cover the
bare `total_weight_kg` when `overage_pct > 0`.

#### Scenario: Inflates required weight by the overage percentage

- **WHEN** a material has `total_weight_kg == Decimal("10")` and
  `overage_pct == Decimal("0.10")`
- **THEN** the resulting line item reports `required_with_overage_kg
  == Decimal("11.0")` and the chosen `purchased_kg` is `≥
  Decimal("11.0")`

#### Scenario: Zero overage covers exactly the net weight

- **WHEN** a material has `total_weight_kg == Decimal("10")` and
  `overage_pct == Decimal("0")`
- **THEN** the line item reports `required_with_overage_kg ==
  Decimal("10")` and `purchased_kg ≥ Decimal("10")`

### Requirement: Multi-package allocations per material

The system SHALL allow each `PurchaseLineItem` to carry one or more
`PurchaseAllocation` entries, each describing one supplier package
and its integer `count`. The optimizer MUST consider allocations
combining different package sizes when doing so improves the strategy
objective relative to a single-package allocation.

#### Scenario: Combines two package sizes when it strictly improves the strategy

- **WHEN** a material requires `Decimal("28")` kg with no overage,
  candidate packages are `25 kg @ €30` and `5 kg @ €7`, and
  `strategy == Strategy.MINIMAL_WASTE`
- **THEN** the chosen allocation is `[(25 kg, count=1), (5 kg,
  count=1)]` with `purchased_kg == Decimal("30")` rather than `[(25
  kg, count=2)]` with `purchased_kg == Decimal("50")`

#### Scenario: Returns a single-allocation list when one package is optimal

- **WHEN** a material requires `Decimal("20")` kg, candidate packages
  are `25 kg @ €25` and `5 kg @ €7`, and `strategy ==
  Strategy.CHEAPEST`
- **THEN** the line item's `allocations` contains exactly one entry
  with the `25 kg` package and `count == 1`

### Requirement: Cross-supplier package mixing per material

The system SHALL permit a single `PurchaseLineItem` to draw packages
from multiple suppliers when that improves the strategy objective.
The optimizer MUST NOT artificially restrict a material's allocation
to one supplier.

#### Scenario: Picks packages from two suppliers for one material

- **WHEN** a material requires `Decimal("28")` kg with no overage,
  supplier A offers a `25 kg @ €30` package, supplier B offers a `5
  kg @ €6` package, and `strategy == Strategy.CHEAPEST`
- **THEN** the line item's `allocations` contains a `25 kg` entry
  with `supplier_id == "A"` and a `5 kg` entry with `supplier_id ==
  "B"`, totalling `purchased_kg == Decimal("30")` and
  `cost_incl_vat == Decimal("36.00")`

### Requirement: Excluded materials are skipped silently

The system SHALL omit any material whose `material_id` appears in the
caller-supplied excluded list from the resulting `PurchaseList`. No
line item, supplier subtotal contribution, or grand-total contribution
MUST be emitted for excluded materials, regardless of whether the
catalog ships packages for them.

#### Scenario: Drops an excluded material entirely

- **WHEN** a breakdown contains materials `cement` and `water`,
  `excluded_materials == ["water"]`, and the catalog has packages for
  both
- **THEN** the resulting `PurchaseList` contains a line item for
  `cement` only, and `total_cost_incl_vat` reflects `cement`'s cost
  alone

#### Scenario: Skips an excluded material with no packages without raising

- **WHEN** a breakdown contains material `water`, the catalog has
  zero packages for `water`, and `excluded_materials == ["water"]`
- **THEN** the optimizer returns a `PurchaseList` without raising

### Requirement: Unpurchasable material error

The system SHALL raise `UnpurchasableMaterialError` carrying the
offending `material_id` when a non-excluded material in the breakdown
has zero matching `SupplierPackage` entries in the catalog. The error
message MUST include the `material_id`.

#### Scenario: Raises when the only candidate material has no packages

- **WHEN** a breakdown contains material `phantom-fines`,
  `excluded_materials == []`, and the catalog has no packages with
  `material_id == "phantom-fines"`
- **THEN** calling the optimizer raises `UnpurchasableMaterialError`
  whose message contains `"phantom-fines"`

### Requirement: Cheapest strategy minimises total cost

The `Strategy.CHEAPEST` selection SHALL pick the feasible allocation
that minimises `cost_incl_vat` (the sum of `package.price_incl_vat ×
count`) for each material. Ties on cost MUST be broken first by
`waste_kg` ascending, then by the lexicographically smallest tuple of
sorted `package_id` values repeated by `count`.

#### Scenario: Picks the cheaper allocation when waste differs

- **WHEN** a material requires `Decimal("20")` kg with no overage,
  candidate packages are `25 kg @ €30` and `10 kg @ €13`, and
  `strategy == Strategy.CHEAPEST`
- **THEN** the optimizer picks `[(10 kg, count=2)]` with
  `cost_incl_vat == Decimal("26.00")` over `[(25 kg, count=1)]` with
  `cost_incl_vat == Decimal("30.00")`

#### Scenario: Breaks cost ties by lower waste

- **WHEN** two allocations have equal `cost_incl_vat`, but allocation
  A wastes `1 kg` and allocation B wastes `5 kg`, and `strategy ==
  Strategy.CHEAPEST`
- **THEN** the optimizer picks allocation A

### Requirement: Minimal-waste strategy minimises overage above buffer

The `Strategy.MINIMAL_WASTE` selection SHALL pick the feasible
allocation that minimises `waste_kg = purchased_kg −
required_with_overage_kg`. Ties on waste MUST be broken first by
`cost_incl_vat` ascending, then by the lexicographically smallest
sorted `package_id` tuple.

#### Scenario: Picks the lower-waste allocation even at higher cost

- **WHEN** a material requires `Decimal("28")` kg with no overage,
  candidate packages are `25 kg @ €30` and `5 kg @ €8`, and
  `strategy == Strategy.MINIMAL_WASTE`
- **THEN** the optimizer picks `[(25 kg, count=1), (5 kg, count=1)]`
  with `waste_kg == Decimal("2")` and `cost_incl_vat ==
  Decimal("38.00")` over `[(25 kg, count=2)]` with `waste_kg ==
  Decimal("22")` and `cost_incl_vat == Decimal("60.00")`

### Requirement: Bulk-value strategy minimises weighted price per kilo

The `Strategy.BULK_VALUE` selection SHALL pick the feasible
allocation that minimises the weighted price per purchased kilogram,
defined as `sum(package.price_incl_vat × count) ÷ sum(package.weight_kg
× count)`. Ties on weighted price-per-kg MUST be broken first by
`cost_incl_vat` ascending, then by the lexicographically smallest
sorted `package_id` tuple.

#### Scenario: Prefers a single bulk SKU over many small SKUs

- **WHEN** a material requires `Decimal("20")` kg with no overage,
  candidate packages are `25 kg @ €25` (€1.00/kg) and `5 kg @ €7`
  (€1.40/kg), and `strategy == Strategy.BULK_VALUE`
- **THEN** the optimizer picks `[(25 kg, count=1)]` with
  `weighted_price_per_kg == Decimal("1.00")` over `[(5 kg, count=4)]`
  with `weighted_price_per_kg == Decimal("1.40")`

### Requirement: Waste reported relative to buffered demand

The system SHALL compute every line item's `waste_kg` as
`purchased_kg − required_with_overage_kg`. The optimizer MUST NOT
include the project's overage buffer in the reported waste.

#### Scenario: Reports zero waste when purchase exactly matches buffered demand

- **WHEN** a material has `total_weight_kg == Decimal("10")`,
  `overage_pct == Decimal("0.10")`, and the chosen packages total
  exactly `Decimal("11")` kg
- **THEN** the line item reports `waste_kg == Decimal("0")`

#### Scenario: Reports positive waste only above the overage buffer

- **WHEN** a material has `total_weight_kg == Decimal("10")`,
  `overage_pct == Decimal("0.10")`, and the chosen packages total
  `Decimal("12")` kg
- **THEN** the line item reports `waste_kg == Decimal("1.0")`

### Requirement: Supplier subtotals and grand totals

The system SHALL set `PurchaseList.suppliers` to one
`SupplierSubtotal` per `supplier_id` that appears in any allocation,
each carrying the supplier's `subtotal_incl_vat` (the sum of allocation
costs from that supplier) and `item_count` (the sum of allocation
`count` values from that supplier). The system SHALL set
`total_cost_incl_vat` to the exact sum of all line items'
`cost_incl_vat` values and `total_waste_kg` to the exact sum of all
line items' `waste_kg` values, both at full `Decimal` precision.

#### Scenario: Aggregates one supplier across two materials

- **WHEN** materials `cement` and `sand` both source packages from
  supplier `A` for combined cost `Decimal("100.00")` across three
  packages
- **THEN** `suppliers` contains exactly one `SupplierSubtotal` with
  `supplier_id == "A"`, `subtotal_incl_vat == Decimal("100.00")`, and
  `item_count == 3`

#### Scenario: Aggregates two suppliers from one cross-supplier line item

- **WHEN** a single line item allocates `[(pkg-A1, count=1), (pkg-B1,
  count=1)]` from suppliers `A` and `B` at `€30.00` and `€6.00`
  respectively
- **THEN** `suppliers` contains two `SupplierSubtotal` entries
  reporting `Decimal("30.00")` for supplier `A` and `Decimal("6.00")`
  for supplier `B`, each with `item_count == 1`

#### Scenario: Grand totals equal the sum of line items

- **WHEN** a `PurchaseList` is produced for any breakdown
- **THEN** `total_cost_incl_vat` equals the exact `Decimal` sum of
  every line item's `cost_incl_vat` and `total_waste_kg` equals the
  exact sum of every line item's `waste_kg`

### Requirement: Deterministic tie-breaking

The system SHALL break strategy-objective ties in a fully
deterministic order: first by `total_cost_incl_vat` ascending (when
not already the primary key), then by the lexicographically smallest
sorted tuple of `package_id` values repeated by `count`. Repeated
calls with the same inputs MUST produce equal results.

#### Scenario: Resolves a perfect strategy and cost tie by package id

- **WHEN** two feasible allocations have identical strategy
  objectives and identical `total_cost_incl_vat`, but allocation A
  uses package id `"alpha"` while allocation B uses package id
  `"beta"`
- **THEN** the optimizer picks allocation A

### Requirement: Material name and required-weight echoed into line items

The system SHALL set each line item's `material_id` and
`material_name` to the values reported in the breakdown's matching
`AggregatedMaterial`, and `required_kg` to that material's
`total_weight_kg` at full `Decimal` precision (pre-overage).

#### Scenario: Echoes the aggregated material identity into the line item

- **WHEN** the breakdown reports `material_id == "durigid-1-3"`,
  `material_name == "Durigid 1-3"`, and `total_weight_kg ==
  Decimal("26.34")`
- **THEN** the matching line item reports the same `material_id`,
  `material_name`, and `required_kg == Decimal("26.34")`

### Requirement: Line-item ordering matches the breakdown

The system SHALL emit `PurchaseList.line_items` in the same order as
the input breakdown's `materials` list, so the alphabetical ordering
established by the aggregator carries through to the purchase list.

#### Scenario: Preserves the breakdown's material order

- **WHEN** the breakdown's `materials` list is ordered `["Aggregate
  fines", "Cement", "Quartz sand"]`
- **THEN** `line_items` appears in the order `["Aggregate fines",
  "Cement", "Quartz sand"]`

### Requirement: Full-precision decimal arithmetic at the boundary

The system SHALL perform internal ranking on integer milligrams and
integer cents and SHALL convert chosen allocations back to `Decimal`
without quantisation when populating the result models. Display
rounding belongs to the renderer layer, not the optimizer.

#### Scenario: Does not quantise required or purchased weights

- **WHEN** a material's `total_weight_kg` is
  `Decimal("12.345678")` and the chosen packages total `Decimal("15")`
  kg with `overage_pct == Decimal("0")`
- **THEN** the line item reports `required_kg ==
  Decimal("12.345678")`, `required_with_overage_kg ==
  Decimal("12.345678")`, and `purchased_kg == Decimal("15")` rather
  than rounded values
