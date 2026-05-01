## Why

The `purchase-optimization` capability emits a frozen `PurchaseList`
carrying full-`Decimal` arithmetic, supplier subtotals, and grand
totals — the right contract for the calculator core, but the wrong
shape for human display. Soon two consumers will need the same
formatted view of that list: the Rich CLI table that closes the wizard
and the Excel export written to disk. Building precision rounding,
supplier grouping, and waste/cost formatting twice — once per consumer
— guarantees drift the first time a column changes. A single pure
renderer in the domain layer keeps both surfaces in lockstep and
testable without Rich or openpyxl in scope.

## What Changes

- Add a new pure capability `purchase-rendering` that exposes
  `render_purchase_list(purchase_list, *, ...) -> PurchaseListView`,
  a frozen Pydantic view model designed to feed Rich tables and the
  upcoming Excel export.
- Apply the display-precision rules from `mixsheet.domain.display`
  (`QUANTITY_DECIMALS_LOW/HIGH`, `QUANTITY_THRESHOLD`,
  `PRICE_DECIMALS`, `PERCENT_DECIMALS`) when producing the formatted
  string fields of the view, while keeping the original `Decimal`
  values alongside for callers that need full precision (Excel).
- Group line items by `supplier_id` in the view, with one
  `SupplierGroupView` per supplier carrying its line items, the
  matching `SupplierSubtotal`, and a stable, deterministic ordering
  (suppliers sorted alphabetically by id; line items inside a group
  preserving the input `PurchaseList.line_items` order).
- Surface the grand totals (`total_cost_incl_vat`, `total_waste_kg`)
  as both raw `Decimal` and formatted strings on the view.
- Expose the renderer through `mixsheet.domain` (`render_purchase_list`,
  `PurchaseListView`, `SupplierGroupView`, `PurchaseLineItemView`,
  `PurchaseAllocationView`).

Non-goals:

- No Rich or openpyxl code lives in this capability. The view is a
  plain frozen Pydantic model; rendering targets pick it up later.
- No new precision rules. The renderer consumes
  `mixsheet.domain.display` as-is; if a constant is missing, that is a
  separate change against `domain-models`.
- No reshape of the `PurchaseList` or any catalog/project model.
- No localisation, currency conversion, or unit conversion. Strings
  are produced in the source currency (€) and SI units (kg).

## Capabilities

### New Capabilities

- `purchase-rendering`: pure function that converts a `PurchaseList`
  into a frozen `PurchaseListView` grouped by supplier, with both
  full-precision `Decimal` fields and display-rounded string fields
  derived from `mixsheet.domain.display`.

### Modified Capabilities

(none)

## Impact

- New module `src/mixsheet/domain/renderer.py` with
  `render_purchase_list` and the view models.
- `mixsheet.domain.__init__` re-exports the new public surface.
- New tests under `tests/domain/test_renderer.py` covering
  display-precision rounding at the threshold, supplier grouping and
  ordering, line-item ordering preservation, raw-vs-formatted parity,
  and determinism.
- No catalog schema changes. No project schema changes. No CLI wiring
  in this change — `cli.py` continues to be a stub until the wizard
  capability lands.
- `docs/ROADMAP.md` ticks off the purchase-rendering milestone.
