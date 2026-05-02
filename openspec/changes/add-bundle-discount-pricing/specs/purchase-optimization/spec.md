## ADDED Requirements

### Requirement: Bundle discounts applied per package and count

The system SHALL, when scoring an allocation, replace each package's
listed `price_incl_vat` with its discounted price whenever any
`bundle_discount` tier on that package satisfies `min_quantity ≤
count`. The applied tier MUST be the one with the highest qualifying
`min_quantity`. Discounted prices MUST drive both the optimizer's
strategy ranking and the cost values surfaced on `PurchaseLineItem`,
`SupplierSubtotal`, and `PurchaseList.total_cost_incl_vat`.

#### Scenario: One unit ignores all tiers

- **WHEN** an allocation includes a package with
  `bundle_discounts: [{min_quantity: 2, discount_pct: 0.05}]` at
  `count = 1`
- **THEN** the package's contribution to allocation cost equals its
  listed `price_incl_vat`

#### Scenario: Lowest qualifying tier applies at the threshold

- **WHEN** a package with `price_incl_vat = Decimal("100.00")` and
  `bundle_discounts: [{min_quantity: 2, discount_pct: 0.05}]` is
  allocated at `count = 2`
- **THEN** the package's contribution to allocation cost is
  `Decimal("190.00")` (5 % off the per-unit price, summed over two
  units)

#### Scenario: Highest qualifying tier wins when multiple tiers match

- **WHEN** a package with `price_incl_vat = Decimal("340.98")` and
  `bundle_discounts: [{min_quantity: 2, discount_pct: 0.05},
  {min_quantity: 3, discount_pct: 0.10},
  {min_quantity: 4, discount_pct: 0.15}]` is allocated at `count = 4`
- **THEN** the package's contribution applies the 15 % tier, not the
  5 % or 10 % tier

#### Scenario: Tiers apply per package independently within one allocation

- **WHEN** an allocation contains
  `[(epoxy-resin-25kg, count = 4), (hardener-gl2-7.5kg, count = 4)]`
  where the first package has a 15 %-at-4 tier and the second package
  has only a 5 %-at-2 tier
- **THEN** the epoxy contribution applies 15 % off and the hardener
  contribution applies 5 % off; the basket-level cost equals the sum
  of the two independently discounted contributions

#### Scenario: Discounted cost flips the cheapest-strategy choice

- **WHEN** allocation A is `[(big-pkg, count = 2)]` with a 15 %-at-2
  tier that drops it below allocation B `[(big-pkg, count = 1),
  (small-pkg, count = 1)]` carrying no tiers, and `strategy ==
  Strategy.CHEAPEST`
- **THEN** the optimizer picks allocation A whenever the discounted
  total is strictly less than allocation B's listed total

#### Scenario: Determinism survives discount application

- **WHEN** the optimizer runs twice on the same breakdown and a
  catalog whose packages carry `bundle_discounts`
- **THEN** both runs return equal `PurchaseList` instances, including
  identical `cost_incl_vat`, `subtotal_incl_vat`, and
  `total_cost_incl_vat` values
