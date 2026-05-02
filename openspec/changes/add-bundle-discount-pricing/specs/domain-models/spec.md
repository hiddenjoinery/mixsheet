## MODIFIED Requirements

### Requirement: Supplier and package models

The system SHALL represent a supplier as a strict, frozen value object
with `id` and `name`. A supplier package SHALL be a strict, frozen
value object with `id`, `material_id`, `supplier_id`, `weight_kg`
(`Decimal > 0`), `price_incl_vat` (`Decimal ≥ 0`), an optional
`product_url` (validated as a well-formed HTTP(S) URL), and a
possibly empty `bundle_discounts` list of `BundleDiscount`. Every
package's `material_id` MUST resolve to a material in the same
catalog and its `supplier_id` MUST resolve to a supplier in the same
catalog.

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

#### Scenario: Loads a package with a product URL and bundle discounts

- **WHEN** a catalog declares a package with `product_url:
  https://www.r-g.de/en/art/100133` and a non-empty `bundle_discounts`
  list
- **THEN** the package loads, exposes `product_url` as a parsed URL,
  and exposes `bundle_discounts` as a list of `BundleDiscount`
  instances in the order written

#### Scenario: Rejects a malformed product URL

- **WHEN** a package declares `product_url: not-a-url`
- **THEN** the catalog loader raises a validation error referencing
  the URL field

## ADDED Requirements

### Requirement: Bundle discount value object

The system SHALL represent a single staffel tier as a strict, frozen
value object holding `min_quantity` (integer ≥ 2) and `discount_pct`
(`Decimal` strictly greater than `0` and strictly less than `1`).
Within a single package, `bundle_discounts` MUST list tiers in
strictly ascending order on both `min_quantity` and `discount_pct`.

#### Scenario: Accepts a strictly ascending tier list

- **WHEN** a package declares
  `bundle_discounts: [{min_quantity: 2, discount_pct: 0.05},
  {min_quantity: 4, discount_pct: 0.15}]`
- **THEN** the package loads with two `BundleDiscount` rows in that
  order

#### Scenario: Rejects a tier with min_quantity below two

- **WHEN** a tier declares `min_quantity: 1`
- **THEN** validation fails with a message stating min_quantity must
  be at least 2

#### Scenario: Rejects a discount_pct at or above one

- **WHEN** a tier declares `discount_pct: 1.0`
- **THEN** validation fails with a message stating discount_pct must
  be less than 1

#### Scenario: Rejects a zero discount_pct

- **WHEN** a tier declares `discount_pct: 0`
- **THEN** validation fails with a message stating discount_pct must
  be greater than 0

#### Scenario: Rejects descending min_quantity across tiers

- **WHEN** a package declares two tiers with `min_quantity` values
  `[4, 2]`
- **THEN** validation fails with a message stating tiers must list
  min_quantity in strictly ascending order

#### Scenario: Rejects a non-increasing discount_pct across tiers

- **WHEN** a package declares two tiers with `discount_pct` values
  `[0.10, 0.10]` at ascending `min_quantity`
- **THEN** validation fails with a message stating tiers must list
  discount_pct in strictly ascending order
