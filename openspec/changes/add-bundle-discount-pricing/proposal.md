## Why

The catalog records `price_incl_vat` per `SupplierPackage`, but real
suppliers price aggressively in tiers: RG Faserverbund publishes
staffel discounts on every epoxy resin and hardener SKU (5–15% off
from the second canister), and the catalog had no way to record either
those discounts or the productpage URL the user clicks through to
verify a price. Without discount data the optimizer overstates cost
whenever a recipe needs ≥ 2 of any RG package, and without product
URLs the user cannot trace a price back to the supplier listing.

This change closes both gaps. It records `product_url` and tiered
`bundle_discounts` on every `SupplierPackage`, and it teaches
`optimize_purchase` to apply the matching staffel when scoring an
allocation so the cost reported to the user matches what the supplier
will actually charge at checkout.

## What Changes

**`domain-models` capability (data carrier — already implemented):**

- Extend `SupplierPackage` with `product_url: HttpUrl | None` (default
  `None`) and `bundle_discounts: list[BundleDiscount]` (default empty).
- Add a frozen `BundleDiscount` model carrying `min_quantity: int ≥ 2`
  and `discount_pct: Decimal` in the open interval `(0, 1)`.
- Validate that a package's `bundle_discounts` are listed strictly
  ascending on both `min_quantity` and `discount_pct`.
- Re-export `BundleDiscount` from `mixsheet.domain`.

**`purchase-optimization` capability (optimizer wiring — not yet
implemented):**

- When evaluating an allocation, the optimizer SHALL apply, per
  package, the highest matching `BundleDiscount` tier whose
  `min_quantity ≤ count` and discount the package's contribution to
  the allocation cost by `(1 - discount_pct)`.
- The reported `cost_incl_vat` on `PurchaseLineItem`,
  `SupplierSubtotal`, and `PurchaseList.total_cost_incl_vat` SHALL
  reflect those discounted package prices, not the listed
  `price_incl_vat`.
- The `Strategy.CHEAPEST` and `Strategy.BULK_VALUE` objectives SHALL
  rank against discounted cost, not listed cost. `MINIMAL_WASTE`
  remains a waste-minimising selection but its tertiary cost
  tie-breaker SHALL also use discounted cost.
- Determinism is preserved: tier application is a pure function of
  `(package, count)` and the catalog.

Non-goals:

- No changes to YAML file shape beyond the additive package fields.
- No multi-supplier basket discounts, freight tiers, or coupon codes —
  only per-SKU tiered staffels.
- No surfacing of discount details in the Rich/Excel renderer in this
  change. The renderer keeps showing total cost only; tier-attribution
  output is a follow-up if needed.
- No automatic price-refresh from supplier websites. A separate
  agent skill handles periodic price/staffel verification.

## Capabilities

### Modified Capabilities

- `domain-models` — `SupplierPackage` carries optional `product_url`
  and `bundle_discounts`; new `BundleDiscount` value object.
- `purchase-optimization` — allocation cost is computed from
  per-package discounted prices when a `BundleDiscount` tier matches
  the chosen `count`.

## Impact

- `src/mixsheet/domain/catalog.py` — `BundleDiscount` model and two
  fields on `SupplierPackage` (already landed in this change's data
  step).
- `src/mixsheet/data/suppliers.yaml` — every package now carries a
  `product_url`; every RG Faserverbund package carries
  `bundle_discounts` (already landed).
- `src/mixsheet/domain/optimizer.py` — discount-aware cost computation
  inside the candidate-allocation enumerator (pending).
- `tests/domain/test_catalog_models.py` — coverage for the new fields
  and ascending-tier validator (already landed).
- `tests/domain/test_optimizer.py` — new scenarios for tier
  application, multi-tier selection, and determinism with discounts
  (pending).
- `CHANGELOG.md` — `Added` and `Changed` bullets for the data step
  (already landed); a follow-up `Changed` bullet when the optimizer
  step lands.
- No project file format change. No CLI surface change.
