## ADDED Requirements

### Requirement: Per-material rolled-up summary view

`PurchaseListView` SHALL expose a `materials` field — a list of
`PurchaseLineItemSummaryView` with one entry per input
`PurchaseLineItem`, in the same order as
`PurchaseList.line_items`. Each summary view MUST carry
`material_id`, `material_name`, raw `Decimal` plus formatted
strings for `required_kg`, `required_with_overage_kg`,
`purchased_kg`, `waste_kg`, `cost_incl_vat`, and a `suppliers`
field (a single `str` listing the deduplicated supplier ids that
allocate to this material, sorted alphabetically and joined with
`" + "`). The renderer MUST NOT recompute these values; they are
echoed from the input line item with display rounding applied
where the corresponding `_display` companion exists.

#### Scenario: One materials entry per parent line item

- **WHEN** the input `PurchaseList.line_items` has length 3
- **THEN** the view's `materials` list has length 3 in the same
  order

#### Scenario: Single-supplier material reports one supplier id

- **WHEN** an input line item allocates two packages from supplier
  `acme` only
- **THEN** the matching `PurchaseLineItemSummaryView.suppliers ==
  "acme"`

#### Scenario: Cross-supplier material joins supplier ids alphabetically

- **WHEN** an input line item allocates one package from supplier
  `bcs` and one from supplier `acme`
- **THEN** the matching `PurchaseLineItemSummaryView.suppliers ==
  "acme + bcs"`

#### Scenario: Echoes parent line item totals at full precision

- **WHEN** an input line item reports `cost_incl_vat ==
  Decimal("36.00")` and `purchased_kg == Decimal("30")`
- **THEN** the matching `PurchaseLineItemSummaryView` exposes
  `cost_incl_vat == Decimal("36.00")` and `purchased_kg ==
  Decimal("30")` (raw values unmodified)

#### Scenario: Display strings follow the threshold and price rules

- **WHEN** an input line item reports `purchased_kg ==
  Decimal("9.6")` and `cost_incl_vat == Decimal("36")`
- **THEN** the summary view reports `purchased_kg_display == "9.6"`
  and `cost_incl_vat_display == "€ 36.00"`

#### Scenario: Empty purchase list yields an empty materials list

- **WHEN** the input `PurchaseList` has no line items
- **THEN** `PurchaseListView.materials` is an empty list
