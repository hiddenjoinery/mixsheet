## 1. Catalog data carrier

- [x] 1.1 Add frozen `BundleDiscount(min_quantity: int ≥ 2, discount_pct: Decimal ∈ (0,1))` Pydantic model in `src/mixsheet/domain/catalog.py`.
- [x] 1.2 Extend `SupplierPackage` with `product_url: HttpUrl | None = None` and `bundle_discounts: list[BundleDiscount] = []`.
- [x] 1.3 Add a `model_validator(mode="after")` on `SupplierPackage` that rejects non-strictly-ascending `min_quantity` and non-strictly-ascending `discount_pct` across the tier list.
- [x] 1.4 Re-export `BundleDiscount` from `src/mixsheet/domain/__init__.py`.
- [x] 1.5 Populate every package in `src/mixsheet/data/suppliers.yaml` with its `product_url`. Populate `bundle_discounts` for every RG Faserverbund package using the staffels published on r-g.de (see proposal).
- [x] 1.6 Realign two list prices to the supplier's current page: `epoxy-resin-25kg` €341.21 → €340.98; `hardener-gl2-20kg` €404.97 → €404.87.

## 2. Tests for the data carrier

- [x] 2.1 Cover loading a package with both new fields populated.
- [x] 2.2 Cover rejection of a malformed `product_url`.
- [x] 2.3 Cover rejection of descending `min_quantity` and non-increasing `discount_pct`.
- [x] 2.4 Cover the boundary cases of `BundleDiscount`: `min_quantity = 1` rejected, `discount_pct = 0` rejected, `discount_pct = 1` rejected.

## 3. Optimizer wiring

- [ ] 3.1 Add a private `_discounted_price_cents(package, count) -> int` helper that selects the highest matching tier and returns the rounded cents.
- [ ] 3.2 Update `_enumerate_allocations` so each candidate's `cost_cents` is the sum across `(package, count)` pairs of `_discounted_price_cents(package, count)`.
- [ ] 3.3 Verify all three strategies still satisfy their objective definitions with discounted cost — `CHEAPEST` and `BULK_VALUE` directly, `MINIMAL_WASTE` only via its cost tertiary tie-break.
- [ ] 3.4 Confirm `PurchaseLineItem.cost_incl_vat`, `SupplierSubtotal.subtotal_incl_vat`, and `PurchaseList.total_cost_incl_vat` all carry discounted values and the `Decimal` boundary preserves cent precision.
- [ ] 3.5 No new public surface; no signature change on `optimize_purchase`.

## 4. Tests for optimizer wiring

- [ ] 4.1 Allocation of 1 unit of an RG package is unaffected (no tier applies).
- [ ] 4.2 Allocation of 2 units of `epoxy-resin-25kg` charges 5% off the list price; total cost matches the hand-computed value to the cent.
- [ ] 4.3 Allocation of 4 units of `epoxy-resin-25kg` charges the 15% tier, not the 5% tier (highest-applicable rule).
- [ ] 4.4 In a mixed allocation `[(epoxy-resin-25kg, 4), (hardener-gl2-7.5kg, 4)]`, each package gets its own tier independently.
- [ ] 4.5 Determinism: running the optimizer twice with the same discounted catalog yields equal `PurchaseList`.
- [ ] 4.6 `CHEAPEST` flips its allocation choice when the discount makes a previously losing allocation now strictly cheaper.

## 5. Quality gates

- [x] 5.1 `uv run ruff check --fix src tests` and `uv run ruff format src tests` pass on the data step.
- [x] 5.2 `uv run pyright` clean on the data step.
- [x] 5.3 `uv run pytest -q` green on the data step.
- [ ] 5.4 Full lint, format, type, and test cycle re-run after the optimizer step.
- [ ] 5.5 `openspec validate add-bundle-discount-pricing --strict` passes.

## 6. Documentation

- [x] 6.1 Add `Added` and `Changed` CHANGELOG bullets for the data step.
- [ ] 6.2 Add a `Changed` CHANGELOG bullet for the optimizer step describing the cost-reporting shift.
