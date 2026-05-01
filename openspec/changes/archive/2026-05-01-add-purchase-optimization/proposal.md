## Why

The `calculator` and `project-aggregation` capabilities give the user a
mix-sheet view of *what to pour*. Mix Sheet's flow promises a fourth,
load-bearing step: turn that demand into *what to buy*, picking
supplier packages that minimise either cost, waste, or unit price.
Until this capability exists, the CLI can compute material weights but
cannot answer the user's actual question — "go to which supplier with
which list".

## What Changes

- Add a new pure capability `purchase-optimization` that, given a
  `ProjectBreakdown` and a `Catalog`, returns a frozen `PurchaseList`
  with one `PurchaseLineItem` per material, supplier subtotals, and
  grand totals.
- Apply `project.purchase.overage_pct` to each material's net weight
  *before* package selection so the chosen packages cover the buffered
  demand, not the bare mix-sheet demand.
- Implement three picking strategies declared by the existing
  `Strategy` enum: `cheapest`, `minimal_waste`, `bulk_value`.
- Allow each `PurchaseLineItem` to carry **multiple** `(package,
  count)` allocations — including across suppliers — so the optimizer
  can combine, e.g., one 25 kg sack with one 5 kg bag from a different
  supplier when that beats the strategy objective.
- Skip materials listed in `purchase.excluded_materials` silently.
  Raise `UnpurchasableMaterialError` when a non-excluded material has
  zero matching packages in the catalog (fail-fast).
- Make ranking deterministic: strategy objective → total cost (cents)
  → tuple of package ids alphabetically. No supplier consolidation.
- Define `waste_kg = purchased_kg − required_with_overage_kg` so
  reported waste is what spills *above* the user's own buffer, not the
  buffer itself.
- Expose the optimizer through `mixsheet.domain` (`optimize_purchase`,
  `PurchaseList`, `PurchaseLineItem`, `PurchaseAllocation`,
  `SupplierSubtotal`, `UnpurchasableMaterialError`).

Non-goals:

- No CLI wizard wiring, no Rich rendering, no file export — those
  capabilities land in follow-up changes.
- No min-order, shipping cost, or supplier surcharges. The catalog
  models do not carry that data and the change does not add it.
- No re-use of an in-house bag (e.g. partial leftovers from a previous
  run). The user always shops the full demand.

## Capabilities

### New Capabilities

- `purchase-optimization`: pure function over a `ProjectBreakdown` and
  `Catalog` that emits a `PurchaseList` with strategy-driven package
  allocations, overage-aware demand, supplier subtotals, and grand
  totals.

### Modified Capabilities

(none)

## Impact

- New module `src/mixsheet/domain/optimizer.py` with the public
  function `optimize_purchase` and its result models.
- `mixsheet.domain.__init__` re-exports the new public surface.
- New tests under `tests/domain/test_optimizer.py` covering each
  strategy, multi-package allocations, cross-supplier mixing, overage
  application, excluded-material handling, the unpurchasable-material
  error, and determinism.
- No catalog schema changes. No project schema changes.
- `docs/ROADMAP.md` ticks off the purchase-optimization milestone.
