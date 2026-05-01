## Context

The `calculator` and `project-aggregation` capabilities already produce
a frozen `ProjectBreakdown` with full-precision `Decimal` per-material
totals. The remaining piece is turning that demand vector into a
`PurchaseList`: for each material, choose a multiset of supplier
packages whose combined weight covers
`required_kg × (1 + overage_pct)` and that ranks best under the
project's `Strategy`.

A legacy implementation lives in
`mixsheet_backup/backend/src/mixsheet/services/optimizer.py`. It is
**not** the basis for this work — the constraints below differ from
that prototype:

- Legacy picks one SKU + count per material; this design must combine
  multiple `(package, count)` allocations, including across suppliers.
- Legacy considers only `min_count` and `min_count + 1`; this design
  must explore the full feasible allocation space within bounded cost.
- Legacy quantises `required_kg` to two decimals on the line item;
  this design preserves full `Decimal` precision in arithmetic and
  rounds only at the renderer.
- Legacy ignores excluded materials at the caller site; this design
  centralises that filter inside the optimizer.

## Goals / Non-Goals

**Goals**

- Pure, deterministic, side-effect-free function:
  `optimize_purchase(breakdown, catalog, *, strategy, overage_pct,
  excluded_materials) -> PurchaseList`.
- Three strategies (`cheapest`, `minimal_waste`, `bulk_value`) with
  identical signature and identical determinism contract.
- Multi-package allocation per material, across suppliers, with
  exact-integer arithmetic for ranking.
- Fail-fast on any non-excluded material that has no purchasable
  package.

**Non-Goals**

- No CLI, Rich rendering, or file export — that lands in follow-up
  changes.
- No catalog or project-schema changes.
- No min-order, shipping, or supplier surcharge support — the catalog
  doesn't carry that data.
- No supplier consolidation heuristic.

## Decisions

### Decision 1 — Per-material allocation as a bounded integer search

Each material's selection is independent: pick a multiset of `(package,
count)` over the candidate packages for that material so that the
combined weight ≥ `required_with_overage_kg`, then rank by the
strategy's objective.

We do **not** call this a knapsack — the demand is a *cover*
constraint (≥), not a capacity constraint (≤). The size of the search
is bounded by:

- `K` = number of candidate packages for this material (typically
  ≤ 10 in the bundled catalog),
- `N_max(p)` = `ceil(required_with_overage_kg / weight(p)) + 1` per
  package — i.e. one count beyond the minimum cover, since strategies
  may prefer a larger but cheaper or lower-waste combination.

Concretely, the optimizer enumerates the cartesian product of
`(0..N_max(p))` across packages, prunes branches whose partial weight
exceeds `required_with_overage_mg + max_package_weight_mg` (any such
allocation is dominated by one with a single package removed — still
feasible and strictly cheaper under every strategy), and selects the
best feasible allocation. A naïve `2 × required_mg` cap was rejected
because it discards the only feasible allocation when a single
candidate package alone exceeds twice the demand (e.g. 5 kg demand
against a 25 kg sack).

**Alternatives considered**

- *Greedy single-package selection (legacy)*: rejected — fails the
  multi-package and cross-supplier requirement, and `minimal_waste`
  systematically picks worse than optimal.
- *MILP via PuLP/OR-tools*: rejected — heavyweight dependency for a
  domain whose realistic instance has ≤ 10 packages and ≤ 20 materials.
- *Branch-and-bound with strategy-specific bounds*: deferred — pure
  enumeration with bound pruning is fast enough at expected scale and
  trivial to verify against an exhaustive oracle in tests.

### Decision 2 — Internal arithmetic in integer milligrams and cents

Floating-point is forbidden by the project's Python rules and by the
calculator's existing precision contract. The optimizer converts each
material's `required_with_overage_kg` and each candidate package's
`weight_kg` to integer **milligrams** (×1 000 000 from kg) and prices
to integer **cents** (×100 from euro), uses those for ranking and
comparison, then maps the chosen allocation back to `Decimal` for the
output models.

Milligrams (not grams as in legacy) preserve enough precision to
encode `required_kg` with up to six decimal places — the limit set by
the calculator's full-precision arithmetic for realistically sized
projects.

### Decision 3 — Strategy objective tuples

Each strategy reduces to a totally-ordered tuple over the integer
representation. Lower is better.

- `cheapest`: `(total_cost_cents, total_waste_mg, allocation_id_tuple)`
- `minimal_waste`: `(total_waste_mg, total_cost_cents, allocation_id_tuple)`
- `bulk_value`: `(weighted_price_per_kg_milli, total_cost_cents, allocation_id_tuple)`
  where `weighted_price_per_kg_milli =
  sum(package.price_cents × count) ÷ sum(package.weight_mg × count)`
  scaled to cents-per-kg as an integer (round-half-up to milli-cents).

`allocation_id_tuple` is the lexicographically-sorted tuple of
`package_id` strings repeated by `count`. This guarantees a fully
deterministic winner under any tie.

### Decision 4 — Overage applied before package selection

The optimizer multiplies the aggregator's per-material
`total_weight_kg` by `(1 + overage_pct)` and treats that as the cover
target. `waste_kg = purchased_kg − required_with_overage_kg`. Two
consequences worth highlighting:

- The overage **is** purchased — packages cover the buffered demand,
  not the bare mix-sheet demand.
- Reported waste reflects only what spills *above* the buffer. A
  user with `overage_pct = 0.10` who buys exactly 10 % over their
  pour weight sees `waste_kg = 0`, which matches their intent.

### Decision 5 — Exclusions and unpurchasable materials

Materials in `purchase.excluded_materials` are skipped — no line item
is emitted, and they don't contribute to grand totals. Any other
material with zero candidate packages raises
`UnpurchasableMaterialError(material_id)` immediately. Catching that
error is the caller's responsibility (the wizard offers to add the
material to the exclusion list).

### Decision 6 — Public surface lives in `mixsheet.domain.optimizer`

New module, re-exported through `mixsheet.domain.__init__` alongside
the existing aggregator/calculator surface. The function signature is
keyword-only for `strategy`, `overage_pct`, and `excluded_materials`
so callers cannot accidentally swap the last three positional
arguments.

### Decision 7 — Output models live next to the function

`PurchaseList`, `PurchaseLineItem`, `PurchaseAllocation`, and
`SupplierSubtotal` are frozen Pydantic v2 models with `extra="forbid"`.
`PurchaseLineItem.allocations` is a non-empty list of
`PurchaseAllocation(package_id, supplier_id, package_weight_kg,
package_price_incl_vat, count)`. Renderers iterate that list to
display "1 × 25 kg @ €X + 1 × 5 kg @ €Y" without re-deriving package
data from the catalog.

## Risks / Trade-offs

- *Combinatorial blow-up on large catalogs* → mitigation: `N_max(p)`
  bound + partial-weight pruning + a hard cap of `K ≤ 32` candidate
  packages per material before the search begins (raises
  `CatalogTooBroadError` if exceeded). The bundled catalog is far
  below that ceiling; this is a defensive guard, not an expected
  path.
- *Strategy ties producing surprising winners* → mitigation: the
  `allocation_id_tuple` tertiary key makes ties resolve to the
  lexicographically smallest package id set, which is stable and
  testable.
- *Floating-point creep through Pydantic deserialisation* →
  mitigation: all internal math runs on integer mg/cents; `Decimal`
  is only used at the model boundary, where the existing
  `safe_load_decimal` already prevents float ingestion.
- *Drift between aggregator's `materials` and optimizer's view*
  (e.g. a material disappears from the breakdown due to upstream
  filtering) → mitigation: optimizer iterates the breakdown's
  `materials` list directly, never re-reads the project; aggregator
  documents that excluded materials remain in the breakdown.

## Open Questions

None at proposal time. Questions answered up front:

- Multi-package per material: yes, including cross-supplier.
- Missing package handling: skip if excluded, raise otherwise.
- Tie-breaking: strategy → cost → package-id tuple; no supplier
  consolidation.
- Overage application: before selection, included in `purchased_kg`.
- Strategies: all three (`cheapest`, `minimal_waste`, `bulk_value`).
- Output: line items + supplier subtotals + grand totals.
- Waste basis: `purchased_kg − required_with_overage_kg`.
