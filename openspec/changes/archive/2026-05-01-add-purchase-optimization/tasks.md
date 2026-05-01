## 1. Output models

- [x] 1.1 Add `src/mixsheet/domain/optimizer.py` with frozen Pydantic v2 models `PurchaseAllocation`, `PurchaseLineItem`, `SupplierSubtotal`, `PurchaseList` (all `extra="forbid"`).
- [x] 1.2 Define `UnpurchasableMaterialError` (subclass of `ValueError`) with `material_id` attribute and a message containing the id.
- [x] 1.3 Add `CatalogTooBroadError` for the defensive `K ≤ 32` candidate cap.

## 2. Internal arithmetic helpers

- [x] 2.1 Add private `_to_milligrams(kg: Decimal) -> int` and `_to_cents(eur: Decimal) -> int` helpers using `ROUND_HALF_UP`, with sibling `_kg_from_milligrams` / `_eur_from_cents` for the boundary back to `Decimal`.
- [x] 2.2 Add a `_PackageCandidate` internal dataclass holding `package_id`, `supplier_id`, `weight_mg`, `price_cents`, and the original `SupplierPackage` reference for output reconstruction.

## 3. Per-material allocation search

- [x] 3.1 Implement `_candidates_for(material_id, catalog)` that filters `catalog.packages`, sorts by `package_id` for determinism, and raises `CatalogTooBroadError` past the 32-package cap.
- [x] 3.2 Implement `_enumerate_allocations(candidates, required_mg)` yielding feasible `(counts: tuple[int, ...], purchased_mg: int, cost_cents: int)` tuples with `N_max(p) = ceil(required_mg / weight_mg) + 1` per package and pruning branches whose partial weight already exceeds `2 × required_mg`.
- [x] 3.3 Add `_objective(strategy, allocation)` returning the comparable tuple per Decision 3 — including `weighted_price_per_kg_milli` for `BULK_VALUE`.
- [x] 3.4 Add `_pick_best(allocations, strategy, candidates)` that selects the minimum tuple, with the `allocation_id_tuple` tertiary key derived from `package_id` repeated by `count`.

## 4. Public optimizer entry point

- [x] 4.1 Implement `optimize_purchase(breakdown, catalog, *, strategy, overage_pct, excluded_materials) -> PurchaseList`, iterating `breakdown.materials` in order, applying overage, calling the search, and skipping excluded materials.
- [x] 4.2 Build `PurchaseLineItem` instances from the chosen allocation, populating `required_kg`, `required_with_overage_kg`, `purchased_kg`, `cost_incl_vat`, `waste_kg`, and the `allocations` list (sorted by `package_id`).
- [x] 4.3 Aggregate `SupplierSubtotal` rows, `total_cost_incl_vat`, and `total_waste_kg`; ensure subtotals appear sorted by `supplier_id` for stable output.
- [x] 4.4 Re-export the new public surface from `src/mixsheet/domain/__init__.py` (`optimize_purchase`, `PurchaseList`, `PurchaseLineItem`, `PurchaseAllocation`, `SupplierSubtotal`, `UnpurchasableMaterialError`).

## 5. Tests

- [x] 5.1 Add `tests/domain/test_optimizer.py` covering Requirement 1 (frozen, deterministic, no I/O) with a fixture catalog/breakdown and `model_copy(deep=True)` assertion.
- [x] 5.2 Cover overage application: zero-overage exact cover, 10% overage inflation, full-precision overage on a 6-decimal `total_weight_kg`.
- [x] 5.3 Cover multi-package selection: legacy fails (single SKU), new optimizer combines `25 kg + 5 kg` under `MINIMAL_WASTE`.
- [x] 5.4 Cover cross-supplier mixing: build a catalog with two suppliers offering complementary sizes; assert allocations span both.
- [x] 5.5 Cover exclusions: excluded material with packages — skipped; excluded material without packages — skipped without raising; non-excluded material without packages — `UnpurchasableMaterialError`.
- [x] 5.6 Cover each strategy with a hand-computed expected allocation: `CHEAPEST` cost-vs-waste, `MINIMAL_WASTE` waste-vs-cost, `BULK_VALUE` weighted price-per-kg.
- [x] 5.7 Cover tie-breaking determinism: two allocations with identical objective and cost → resolved by sorted `package_id` tuple.
- [x] 5.8 Cover supplier subtotals and grand totals: cross-supplier line item produces two `SupplierSubtotal` rows; grand totals equal exact `Decimal` sums of line items.
- [x] 5.9 Cover line-item ordering: assert order matches the input breakdown's `materials` list.
- [x] 5.10 Cover full-precision boundary: `required_kg` and `purchased_kg` are not quantised.
- [x] 5.11 Add a defensive test that 32+ candidate packages for one material raises `CatalogTooBroadError`.

## 6. Quality gates

- [x] 6.1 Run `uv run ruff check --fix src tests` and `uv run ruff format src tests`.
- [x] 6.2 Run `uv run pyright` on the new module and tests; resolve any strict-mode issues.
- [x] 6.3 Run `uv run pytest tests/domain/test_optimizer.py -q` and the full `uv run pytest -q` to ensure no regressions in calculator/aggregator.
- [x] 6.4 Run `openspec validate add-purchase-optimization --strict`.

## 7. Documentation

- [x] 7.1 Add an `[Unreleased] / Added` bullet in `CHANGELOG.md` for the purchase-optimization domain capability.
- [x] 7.2 Tick off the purchase-optimization milestone in `docs/ROADMAP.md` and link to the change folder.
- [x] 7.3 Update `src/mixsheet/domain/__init__.py` module docstring to mention the optimizer surface.
