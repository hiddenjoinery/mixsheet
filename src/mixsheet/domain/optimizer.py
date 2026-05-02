"""Pure purchase optimisation across catalog packages.

Given a frozen :class:`~mixsheet.domain.aggregator.ProjectBreakdown`
and a :class:`~mixsheet.domain.catalog.Catalog`,
:func:`optimize_purchase` returns a frozen :class:`PurchaseList` that
describes how to cover each material's buffered demand with a multiset
of supplier packages, ranked by the chosen :class:`Strategy`.

The optimiser is deterministic, never quantises, and runs all ranking
arithmetic on integer milligrams and integer cents to keep
floating-point out of the comparison path.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import TYPE_CHECKING, NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from mixsheet.domain.strategy import Strategy

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from mixsheet.domain.aggregator import ProjectBreakdown
    from mixsheet.domain.catalog import BundleDiscount, Catalog, SupplierPackage

MG_PER_KG = Decimal("1000000")
CENTS_PER_EUR = Decimal("100")
MAX_CANDIDATES_PER_MATERIAL = 32


class UnpurchasableMaterialError(ValueError):
    """Raised when a non-excluded material has no candidate packages."""

    def __init__(self, material_id: str) -> None:
        """Build the error from the offending material id."""
        self.material_id = material_id
        super().__init__(f"no purchasable package for material {material_id!r}")


class CatalogTooBroadError(ValueError):
    """Raised when one material has more candidate packages than the cap.

    The optimiser enumerates allocations per material; an unrealistically
    broad catalog risks combinatorial blow-up. The cap is a defensive
    guard, not an expected path.
    """

    def __init__(self, material_id: str, count: int) -> None:
        """Build the error from the offending material id and candidate count."""
        self.material_id = material_id
        self.count = count
        super().__init__(
            f"material {material_id!r} has {count} candidate packages, "
            f"exceeding the cap of {MAX_CANDIDATES_PER_MATERIAL}",
        )


class PurchaseAllocation(BaseModel):
    """One supplier package and its integer count within a line item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    package_id: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    package_weight_kg: Decimal
    package_price_incl_vat: Decimal
    count: int = Field(ge=1)


class PurchaseLineItem(BaseModel):
    """A material's full purchase: one or more package allocations and totals."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)
    required_kg: Decimal
    required_with_overage_kg: Decimal
    purchased_kg: Decimal
    waste_kg: Decimal
    cost_incl_vat: Decimal
    allocations: list[PurchaseAllocation] = Field(min_length=1)


class SupplierSubtotal(BaseModel):
    """Per-supplier roll-up across every allocation in a purchase list."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    supplier_id: str = Field(min_length=1)
    subtotal_incl_vat: Decimal
    item_count: int = Field(ge=1)


class PurchaseList(BaseModel):
    """A project-wide purchase list: line items, supplier subtotals, totals."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    line_items: list[PurchaseLineItem]
    suppliers: list[SupplierSubtotal]
    total_cost_incl_vat: Decimal
    total_waste_kg: Decimal


class _PackageCandidate(NamedTuple):
    """Internal candidate package projected to integer mg/cents."""

    package_id: str
    supplier_id: str
    weight_mg: int
    price_cents: int
    package: SupplierPackage


class _Allocation(NamedTuple):
    """One feasible (counts, purchased_mg, cost_cents) tuple."""

    counts: tuple[int, ...]
    purchased_mg: int
    cost_cents: int


def _to_milligrams(kg: Decimal) -> int:
    """Convert a kilogram :class:`Decimal` to integer milligrams (half-up)."""
    return int((kg * MG_PER_KG).to_integral_value(rounding=ROUND_HALF_UP))


def _to_cents(eur: Decimal) -> int:
    """Convert a euro :class:`Decimal` to integer cents (half-up)."""
    return int((eur * CENTS_PER_EUR).to_integral_value(rounding=ROUND_HALF_UP))


def _matching_tier(package: SupplierPackage, count: int) -> BundleDiscount | None:
    """Return the highest qualifying ``BundleDiscount`` for ``count`` units.

    Tiers on a package are stored in strictly ascending ``min_quantity``;
    the last one whose threshold has been crossed wins.
    """
    matched: BundleDiscount | None = None
    for tier in package.bundle_discounts:
        if tier.min_quantity > count:
            break
        matched = tier
    return matched


def _discounted_price_cents(package: SupplierPackage, count: int) -> int:
    """Return the integer cents for ``count`` units of ``package``.

    Applies the highest matching :class:`BundleDiscount` tier, if any, by
    rounding the discounted per-unit price half-up to the cent and
    multiplying by ``count``. Keeps the optimizer's ranking arithmetic on
    integer cents and deterministic across runs.
    """
    if count == 0:
        return 0
    base_cents = _to_cents(package.price_incl_vat)
    tier = _matching_tier(package, count)
    if tier is None:
        return base_cents * count
    discounted_unit_cents = int(
        (Decimal(base_cents) * (Decimal("1") - tier.discount_pct)).to_integral_value(
            rounding=ROUND_HALF_UP,
        ),
    )
    return discounted_unit_cents * count


def _candidates_for(material_id: str, catalog: Catalog) -> list[_PackageCandidate]:
    """Return the deterministic candidate list for one material.

    Packages are filtered to ``material_id`` and sorted by ``package.id``
    so the search and tie-breaker see a stable order. Raises
    :class:`CatalogTooBroadError` past the per-material cap.
    """
    matching = [pkg for pkg in catalog.packages if pkg.material_id == material_id]
    if len(matching) > MAX_CANDIDATES_PER_MATERIAL:
        raise CatalogTooBroadError(material_id, len(matching))
    matching.sort(key=lambda pkg: pkg.id)
    return [
        _PackageCandidate(
            package_id=pkg.id,
            supplier_id=pkg.supplier_id,
            weight_mg=_to_milligrams(pkg.weight_kg),
            price_cents=_to_cents(pkg.price_incl_vat),
            package=pkg,
        )
        for pkg in matching
    ]


def _enumerate_allocations(
    candidates: list[_PackageCandidate],
    required_mg: int,
) -> Iterator[_Allocation]:
    """Yield every feasible allocation that covers ``required_mg``.

    The search is a depth-first walk over per-package counts in
    ``0..N_max(p)`` where ``N_max(p) = ceil(required_mg / weight_mg) + 1``.
    Any branch whose partial weight already exceeds ``required_mg +
    max_package_weight_mg`` is pruned: such an allocation is dominated
    by one with a single package removed (which is still feasible and
    strictly cheaper under every strategy).

    Per-package costs come from :func:`_discounted_price_cents` so any
    ``BundleDiscount`` tier on a package is reflected in the candidate's
    ``cost_cents``.
    """
    n = len(candidates)
    n_max = [math.ceil(required_mg / c.weight_mg) + 1 for c in candidates]
    max_package_weight = max(c.weight_mg for c in candidates)
    weight_cap = required_mg + max_package_weight
    cost_table = [
        [_discounted_price_cents(c.package, k) for k in range(n_max[i] + 1)]
        for i, c in enumerate(candidates)
    ]

    def dfs(
        idx: int,
        partial_weight: int,
        partial_cost: int,
        counts: list[int],
    ) -> Iterator[_Allocation]:
        if partial_weight > weight_cap:
            return
        if idx == n:
            if partial_weight >= required_mg:
                yield _Allocation(
                    counts=tuple(counts),
                    purchased_mg=partial_weight,
                    cost_cents=partial_cost,
                )
            return
        candidate = candidates[idx]
        for k in range(n_max[idx] + 1):
            counts.append(k)
            yield from dfs(
                idx + 1,
                partial_weight + k * candidate.weight_mg,
                partial_cost + cost_table[idx][k],
                counts,
            )
            counts.pop()

    yield from dfs(0, 0, 0, [])


def _allocation_id_tuple(
    candidates: list[_PackageCandidate],
    counts: tuple[int, ...],
) -> tuple[str, ...]:
    """Return the sorted tuple of ``package_id`` repeated by ``count``."""
    ids: list[str] = []
    for candidate, count in zip(candidates, counts, strict=True):
        ids.extend([candidate.package_id] * count)
    return tuple(sorted(ids))


def _objective_key(
    strategy: Strategy,
    allocation: _Allocation,
    required_mg: int,
    candidates: list[_PackageCandidate],
) -> tuple[object, ...]:
    """Return the strategy ranking tuple; lower wins.

    Tertiary key is the lexicographically sorted ``package_id`` tuple
    so ties resolve deterministically.
    """
    waste_mg = allocation.purchased_mg - required_mg
    id_tuple = _allocation_id_tuple(candidates, allocation.counts)
    if strategy is Strategy.CHEAPEST:
        return (allocation.cost_cents, waste_mg, id_tuple)
    if strategy is Strategy.MINIMAL_WASTE:
        return (waste_mg, allocation.cost_cents, id_tuple)
    weighted_price = Fraction(allocation.cost_cents, allocation.purchased_mg)
    return (weighted_price, allocation.cost_cents, id_tuple)


def _pick_best(
    strategy: Strategy,
    allocations: Iterable[_Allocation],
    required_mg: int,
    candidates: list[_PackageCandidate],
) -> _Allocation:
    """Return the allocation with the smallest objective tuple."""
    return min(
        allocations,
        key=lambda alloc: _objective_key(strategy, alloc, required_mg, candidates),
    )


def _build_line_item(  # noqa: PLR0913
    material_id: str,
    material_name: str,
    required_kg: Decimal,
    required_with_overage_kg: Decimal,
    candidates: list[_PackageCandidate],
    allocation: _Allocation,
) -> PurchaseLineItem:
    """Materialise the chosen allocation into a frozen :class:`PurchaseLineItem`."""
    chosen = [
        PurchaseAllocation(
            package_id=candidate.package_id,
            supplier_id=candidate.supplier_id,
            package_weight_kg=candidate.package.weight_kg,
            package_price_incl_vat=candidate.package.price_incl_vat,
            count=count,
        )
        for candidate, count in zip(candidates, allocation.counts, strict=True)
        if count > 0
    ]
    chosen.sort(key=lambda alloc: alloc.package_id)
    purchased_kg = sum(
        (alloc.package_weight_kg * alloc.count for alloc in chosen),
        start=Decimal("0"),
    )
    cost_incl_vat = Decimal(allocation.cost_cents) / CENTS_PER_EUR
    waste_kg = purchased_kg - required_with_overage_kg
    return PurchaseLineItem(
        material_id=material_id,
        material_name=material_name,
        required_kg=required_kg,
        required_with_overage_kg=required_with_overage_kg,
        purchased_kg=purchased_kg,
        waste_kg=waste_kg,
        cost_incl_vat=cost_incl_vat,
        allocations=chosen,
    )


def _supplier_subtotals(
    line_items: list[PurchaseLineItem],
    package_lookup: dict[str, SupplierPackage],
) -> list[SupplierSubtotal]:
    """Aggregate allocations into per-supplier subtotals sorted by supplier id.

    ``package_lookup`` resolves an allocation's ``package_id`` back to its
    catalog ``SupplierPackage`` so any ``BundleDiscount`` tier is applied
    to the per-allocation contribution before it is rolled up.
    """
    cost_by_supplier: dict[str, Decimal] = {}
    count_by_supplier: dict[str, int] = {}
    for line_item in line_items:
        for allocation in line_item.allocations:
            supplier_id = allocation.supplier_id
            package = package_lookup[allocation.package_id]
            allocation_cost = (
                Decimal(_discounted_price_cents(package, allocation.count)) / CENTS_PER_EUR
            )
            cost_by_supplier[supplier_id] = (
                cost_by_supplier.get(supplier_id, Decimal("0")) + allocation_cost
            )
            count_by_supplier[supplier_id] = (
                count_by_supplier.get(supplier_id, 0) + allocation.count
            )
    return [
        SupplierSubtotal(
            supplier_id=supplier_id,
            subtotal_incl_vat=cost_by_supplier[supplier_id],
            item_count=count_by_supplier[supplier_id],
        )
        for supplier_id in sorted(cost_by_supplier)
    ]


def optimize_purchase(
    breakdown: ProjectBreakdown,
    catalog: Catalog,
    *,
    strategy: Strategy,
    overage_pct: Decimal,
    excluded_materials: Iterable[str],
) -> PurchaseList:
    """Pick supplier packages that cover each material's buffered demand.

    Iterates ``breakdown.materials`` in order, skipping any material in
    ``excluded_materials``. For every other material the function
    inflates ``total_weight_kg`` by ``overage_pct``, enumerates the
    feasible package allocations under the per-material candidate cap,
    and selects the smallest objective tuple under ``strategy``.

    Raises:
        UnpurchasableMaterialError: a non-excluded material has zero
            candidate packages in the catalog.
        CatalogTooBroadError: a material has more candidate packages
            than :data:`MAX_CANDIDATES_PER_MATERIAL`.

    """
    excluded = frozenset(excluded_materials)
    overage_multiplier = Decimal("1") + overage_pct

    line_items: list[PurchaseLineItem] = []
    for material in breakdown.materials:
        if material.material_id in excluded:
            continue
        candidates = _candidates_for(material.material_id, catalog)
        if not candidates:
            raise UnpurchasableMaterialError(material.material_id)

        required_kg = material.total_weight_kg
        required_with_overage_kg = required_kg * overage_multiplier
        required_mg = _to_milligrams(required_with_overage_kg)

        allocation = _pick_best(
            strategy,
            _enumerate_allocations(candidates, required_mg),
            required_mg,
            candidates,
        )
        line_items.append(
            _build_line_item(
                material_id=material.material_id,
                material_name=material.material_name,
                required_kg=required_kg,
                required_with_overage_kg=required_with_overage_kg,
                candidates=candidates,
                allocation=allocation,
            ),
        )

    package_lookup = {pkg.id: pkg for pkg in catalog.packages}
    suppliers = _supplier_subtotals(line_items, package_lookup)
    total_cost_incl_vat = sum(
        (line_item.cost_incl_vat for line_item in line_items),
        start=Decimal("0"),
    )
    total_waste_kg = sum(
        (line_item.waste_kg for line_item in line_items),
        start=Decimal("0"),
    )
    return PurchaseList(
        line_items=line_items,
        suppliers=suppliers,
        total_cost_incl_vat=total_cost_incl_vat,
        total_waste_kg=total_waste_kg,
    )
