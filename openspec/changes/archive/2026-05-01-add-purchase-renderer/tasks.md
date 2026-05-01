## 1. Renderer module skeleton

- [x] 1.1 Create `src/mixsheet/domain/renderer.py` with module docstring describing pure-rendering contract and reference to `mixsheet.domain.display`.
- [x] 1.2 Add frozen `PurchaseAllocationView` model (raw `Decimal` weight + count plus formatted strings).
- [x] 1.3 Add frozen `PurchaseLineItemView` model carrying `material_id`, `material_name`, raw + formatted `required_kg`, `required_with_overage_kg`, `purchased_kg`, `waste_kg`, `allocation_cost_incl_vat`, `package_count`, and `allocations`.
- [x] 1.4 Add frozen `SupplierGroupView` model (`supplier_id`, `line_items`, raw + formatted `subtotal_incl_vat`, `item_count`).
- [x] 1.5 Add frozen `PurchaseListView` model (`suppliers`, raw + formatted `total_cost_incl_vat`, `total_waste_kg`).

## 2. Display formatting helpers

- [x] 2.1 Add a private `_format_quantity(value: Decimal) -> str` that picks `QUANTITY_DECIMALS_LOW` or `QUANTITY_DECIMALS_HIGH` based on `QUANTITY_THRESHOLD` and rounds half-up.
- [x] 2.2 Add a private `_format_price(value: Decimal) -> str` that rounds at `PRICE_DECIMALS` half-up and prepends `"€ "`.

## 3. Renderer function

- [x] 3.1 Implement `render_purchase_list(purchase_list: PurchaseList) -> PurchaseListView` that fans each `PurchaseAllocation` out into one `PurchaseLineItemView` placed under the matching `SupplierGroupView`.
- [x] 3.2 Compute `allocation_cost_incl_vat` per row as `package_price_incl_vat * count` at full `Decimal` precision; for single-supplier line items the row's cost equals the parent line item's `cost_incl_vat`.
- [x] 3.3 Carry supplier subtotals straight from the input (no recompute) onto each `SupplierGroupView`.
- [x] 3.4 Sort `suppliers` alphabetically by `supplier_id`; preserve input `line_items` order within each group.
- [x] 3.5 Carry `total_cost_incl_vat` and `total_waste_kg` straight from the input onto `PurchaseListView` (no recompute).
- [x] 3.6 Handle the empty `PurchaseList` (no line items, no suppliers) without raising — return an empty view with zero totals.

## 4. Public surface

- [x] 4.1 Re-export `render_purchase_list`, `PurchaseListView`, `SupplierGroupView`, `PurchaseLineItemView`, and `PurchaseAllocationView` from `src/mixsheet/domain/__init__.py`.

## 5. Tests

- [x] 5.1 Create `tests/domain/test_renderer.py`.
- [x] 5.2 Test the single-supplier, single-allocation path (frozen result, fields populated).
- [x] 5.3 Test cross-supplier line-item fan-out: one line item with allocations from suppliers `A` and `B` produces two rows under their respective groups, each row carrying its own `allocation_cost_incl_vat`.
- [x] 5.4 Test single-supplier multi-package allocation: one row with `package_count == 2` and the parent line item's full cost.
- [x] 5.5 Test alphabetical supplier ordering (`bcs`, `acme`, `delta` → `acme`, `bcs`, `delta`).
- [x] 5.6 Test that line-item ordering inside a group preserves the input `line_items` order.
- [x] 5.7 Test the per-cell quantity threshold: 9.99 → `"10.0"`, 10.00 → `"10.0"`, 10.01 → `"10"`, mixed-magnitude column keeps per-cell precision.
- [x] 5.8 Test the price formatting: `Decimal("30")` → `"€ 30.00"`, `Decimal("30.005")` → `"€ 30.01"`.
- [x] 5.9 Test raw/formatted parity: raw `Decimal("12.345678")` survives unrounded next to its formatted string.
- [x] 5.10 Test supplier-subtotal echo and the `sum(rows) == subtotal` invariant.
- [x] 5.11 Test grand-total echo and the `sum(suppliers) == total_cost_incl_vat` invariant.
- [x] 5.12 Test the empty-input path returns an empty view with `"€ 0.00"` / `"0.0"` displays.
- [x] 5.13 Test determinism: two calls with the same input return equal views.

## 6. Validation

- [x] 6.1 Run `uv run ruff check --fix` and `uv run ruff format` on the touched files.
- [x] 6.2 Run `uv run pyright` and resolve any type errors.
- [x] 6.3 Run `uv run pytest` and confirm all renderer tests pass.
- [x] 6.4 Run `openspec validate add-purchase-renderer` and resolve any warnings.
- [x] 6.5 Tick off the purchase-rendering milestone in `docs/ROADMAP.md`.
