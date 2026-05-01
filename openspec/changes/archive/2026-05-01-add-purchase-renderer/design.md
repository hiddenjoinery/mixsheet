## Context

The purchase-optimization capability already emits a frozen
`PurchaseList` with full-precision `Decimal` weights and prices,
supplier subtotals computed at full precision, and `line_items`
ordered the same as the input breakdown. The next two surfaces that
consume it — a Rich table at the end of the CLI wizard and an Excel
export — need the same shape: rows grouped by supplier, weights and
prices rounded to the project's display rules, totals at the bottom.

Doing that grouping and rounding inside Rich callbacks would
duplicate the logic when the Excel export lands. Putting it in the
domain layer keeps the renderer pure (no Rich, no openpyxl), keeps
the optimizer pure (no display concerns), and lets us assert the
rounding behaviour in unit tests without a Rich console.

The display-precision constants already live in
`mixsheet.domain.display` (`QUANTITY_DECIMALS_LOW = 1`,
`QUANTITY_DECIMALS_HIGH = 0`, `QUANTITY_THRESHOLD = Decimal("10")`,
`PRICE_DECIMALS = 2`, `PERCENT_DECIMALS = 0`). FR-012 already pins
those values; this capability just consumes them.

## Goals / Non-Goals

**Goals:**

- A single pure function `render_purchase_list` that produces a frozen
  view model both Rich and openpyxl can iterate without further
  reshaping.
- Display-precision rounding driven entirely by
  `mixsheet.domain.display` constants, with the threshold-switching
  behaviour (≤ 10 ⇒ 1 decimal, > 10 ⇒ 0 decimals) applied per quantity
  cell.
- Both raw `Decimal` and formatted string fields on every numeric
  cell, so Excel can write numeric cells with cell-level format codes
  if it wants while Rich uses the prebuilt strings.
- Grouping by supplier with deterministic ordering: suppliers
  alphabetically by `supplier_id`; line items inside a group in the
  same order as the input `PurchaseList.line_items` (which already
  matches the breakdown).

**Non-Goals:**

- No Rich rendering, no openpyxl writes — those land in follow-up
  changes (`add-cli-wizard`, `add-excel-export`).
- No new precision rules. The renderer is a pure consumer of
  `mixsheet.domain.display`.
- No localisation. Strings use `"."` as decimal separator and `"€"` as
  currency symbol because that is what the rest of the domain emits;
  the wizard layer can re-format if it ever needs to.
- No filtering, no re-ordering of materials, no recomputation. Inputs
  are trusted.

## Decisions

### Decision: Group by supplier in the view, not in the optimizer

The optimizer keeps emitting line items in breakdown order so a single
`PurchaseLineItem` can carry allocations from multiple suppliers. The
renderer fans those allocations out into supplier groups: each
allocation contributes one row under its `supplier_id`, carrying its
share of the parent line item's required/purchased/cost figures.

**Why over the alternative**: rejected pushing supplier grouping into
the optimizer because that would force a single-supplier-per-line
rule and break the cross-supplier mixing requirement
(`purchase-optimization`, "Cross-supplier package mixing per
material"). Keeping the grouping in the view layer preserves the
optimizer's freedom and matches the way both Rich tables and Excel
sheets actually want the data laid out.

### Decision: Raw `Decimal` plus pre-formatted string per cell

Every numeric cell in the view exposes both the raw `Decimal` and a
formatted string. Rich tables read the string; Excel writes the
`Decimal` and applies a cell-level format. This avoids re-parsing
strings in Excel and keeps Rich free of formatting logic.

**Why over the alternative**: rejected emitting only formatted strings
because Excel would have to parse them back to numbers (lossy); also
rejected emitting only raw `Decimal` because then the Rich path would
need to know the rounding rules, defeating the purpose of this
capability.

### Decision: Quantity threshold applies per cell, not per column

`QUANTITY_THRESHOLD = Decimal("10")` switches between 1 and 0 decimal
places. We apply that switch per cell value rather than picking one
precision per column based on the column's max. Per-cell keeps the
rule local — a 9.6 kg row reads "9.6 kg" even if the column also
contains 124 kg — which is what the user-flow examples in
`docs/user-flow.md` show.

### Decision: Use `ROUND_HALF_UP` for display rounding

Display rounding uses `ROUND_HALF_UP` consistently for weights, prices
and percentages. Rationale: the optimizer already uses
`ROUND_HALF_UP` when projecting to integer milligrams and cents
(`optimizer.py:131-136`); using the same mode in the renderer keeps
display values aligned with the optimizer's internal decisions and
matches user intuition for civilian arithmetic.

### Decision: Frozen Pydantic models with `extra="forbid"`

The view models follow the same `model_config = ConfigDict(frozen=True,
extra="forbid")` pattern as the optimizer's result models. This
matches house style across `domain-models`, `calculator`,
`project-aggregation`, and `purchase-optimization`.

## Risks / Trade-offs

[Risk: Grouping produces duplicate `PurchaseLineItem` rows when one
material draws from two suppliers, and naive readers may double-count
cost.] → Mitigation: the view's per-allocation row carries
`allocation_cost_incl_vat` (its own slice) plus a back-reference to
the parent `material_id`; the supplier subtotal is the source of
truth at the supplier level, and the grand total is the source of
truth project-wide. Tests assert that summing per-row allocation costs
within a supplier equals the supplier subtotal, and across suppliers
equals the grand total.

[Risk: A future precision-rule change in `mixsheet.domain.display`
silently changes Excel-cell numeric values via the formatted-string
path.] → Mitigation: Excel callers consume the raw `Decimal` field,
not the formatted string, so the precision constants only affect the
visual layer. A renderer test pins the formatting at the threshold
(values of 9.99, 10.00, 10.01) so any constant change has to update
the test.

[Risk: Adding a renderer in the domain layer blurs "pure domain" by
mixing presentation with computation.] → Mitigation: the renderer
imports nothing outside `mixsheet.domain` (no Rich, no openpyxl, no
Typer). It produces a value object; downstream surfaces decide how to
display it. This is the same boundary `mixsheet.domain.display`
already lives in.
