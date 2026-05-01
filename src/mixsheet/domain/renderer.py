"""Pure rendering of a :class:`PurchaseList` into a display-ready view.

Given a frozen :class:`~mixsheet.domain.optimizer.PurchaseList`,
:func:`render_purchase_list` returns a frozen :class:`PurchaseListView`
regrouped by supplier and decorated with display-rounded string fields.
The renderer consumes the precision constants from
:mod:`mixsheet.domain.display` (`QUANTITY_DECIMALS_LOW/HIGH`,
`QUANTITY_THRESHOLD`, `PRICE_DECIMALS`) and applies them per cell using
``ROUND_HALF_UP``. Raw ``Decimal`` values are preserved alongside the
formatted strings so Excel cells can use native numeric formats.

The renderer imports nothing outside :mod:`mixsheet.domain`; it never
mutates inputs and is deterministic across repeated calls.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from mixsheet.domain.display import (
    PRICE_DECIMALS,
    QUANTITY_DECIMALS_HIGH,
    QUANTITY_DECIMALS_LOW,
    QUANTITY_THRESHOLD,
)

if TYPE_CHECKING:
    from mixsheet.domain.optimizer import (
        PurchaseAllocation,
        PurchaseLineItem,
        PurchaseList,
    )


class PurchaseAllocationView(BaseModel):
    """One supplier package in a rendered line item, with formatted strings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    package_id: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    package_weight_kg: Decimal
    package_weight_kg_display: str
    package_price_incl_vat: Decimal
    package_price_incl_vat_display: str
    count: int = Field(ge=1)


class PurchaseLineItemView(BaseModel):
    """One supplier-scoped row for a material in the rendered purchase list."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)
    required_kg: Decimal
    required_kg_display: str
    required_with_overage_kg: Decimal
    required_with_overage_kg_display: str
    purchased_kg: Decimal
    purchased_kg_display: str
    waste_kg: Decimal
    waste_kg_display: str
    allocation_cost_incl_vat: Decimal
    allocation_cost_incl_vat_display: str
    package_count: int = Field(ge=1)
    allocations: list[PurchaseAllocationView] = Field(min_length=1)


class SupplierGroupView(BaseModel):
    """All rows attributed to one supplier, plus that supplier's subtotal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    supplier_id: str = Field(min_length=1)
    line_items: list[PurchaseLineItemView]
    subtotal_incl_vat: Decimal
    subtotal_incl_vat_display: str
    item_count: int = Field(ge=1)


class PurchaseLineItemSummaryView(BaseModel):
    """Per-material rolled-up summary mirroring the parent ``PurchaseLineItem``.

    Exposes the line item's totals (raw ``Decimal`` plus formatted strings)
    and a deterministic ``suppliers`` string for the Overview tab.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)
    required_kg: Decimal
    required_kg_display: str
    required_with_overage_kg: Decimal
    required_with_overage_kg_display: str
    purchased_kg: Decimal
    purchased_kg_display: str
    waste_kg: Decimal
    waste_kg_display: str
    cost_incl_vat: Decimal
    cost_incl_vat_display: str
    suppliers: str = Field(min_length=1)


class PurchaseListView(BaseModel):
    """A purchase list reshaped for human display: supplier groups + totals."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    suppliers: list[SupplierGroupView]
    materials: list[PurchaseLineItemSummaryView]
    total_cost_incl_vat: Decimal
    total_cost_incl_vat_display: str
    total_waste_kg: Decimal
    total_waste_kg_display: str


def _format_quantity(value: Decimal) -> str:
    """Format a quantity using the per-cell threshold rule and half-up rounding."""
    decimals = QUANTITY_DECIMALS_LOW if abs(value) <= QUANTITY_THRESHOLD else QUANTITY_DECIMALS_HIGH
    quant = Decimal(10) ** -decimals
    rounded = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"{rounded:.{decimals}f}"


def _format_price(value: Decimal) -> str:
    """Format a monetary value at ``PRICE_DECIMALS`` half-up, prefixed with ``€``."""
    quant = Decimal(10) ** -PRICE_DECIMALS
    rounded = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"€ {rounded:.{PRICE_DECIMALS}f}"


def _allocation_view(allocation: PurchaseAllocation) -> PurchaseAllocationView:
    """Project a :class:`PurchaseAllocation` onto its view counterpart."""
    return PurchaseAllocationView(
        package_id=allocation.package_id,
        supplier_id=allocation.supplier_id,
        package_weight_kg=allocation.package_weight_kg,
        package_weight_kg_display=_format_quantity(allocation.package_weight_kg),
        package_price_incl_vat=allocation.package_price_incl_vat,
        package_price_incl_vat_display=_format_price(
            allocation.package_price_incl_vat,
        ),
        count=allocation.count,
    )


def _line_item_view(
    line_item: PurchaseLineItem,
    allocation: PurchaseAllocation,
) -> PurchaseLineItemView:
    """Build one supplier-scoped row from a parent line item and one allocation."""
    allocation_cost = allocation.package_price_incl_vat * allocation.count
    return PurchaseLineItemView(
        material_id=line_item.material_id,
        material_name=line_item.material_name,
        required_kg=line_item.required_kg,
        required_kg_display=_format_quantity(line_item.required_kg),
        required_with_overage_kg=line_item.required_with_overage_kg,
        required_with_overage_kg_display=_format_quantity(
            line_item.required_with_overage_kg,
        ),
        purchased_kg=line_item.purchased_kg,
        purchased_kg_display=_format_quantity(line_item.purchased_kg),
        waste_kg=line_item.waste_kg,
        waste_kg_display=_format_quantity(line_item.waste_kg),
        allocation_cost_incl_vat=allocation_cost,
        allocation_cost_incl_vat_display=_format_price(allocation_cost),
        package_count=allocation.count,
        allocations=[_allocation_view(allocation)],
    )


def _summary_view(line_item: PurchaseLineItem) -> PurchaseLineItemSummaryView:
    """Project a parent ``PurchaseLineItem`` onto its rolled-up summary view."""
    supplier_ids = sorted({allocation.supplier_id for allocation in line_item.allocations})
    return PurchaseLineItemSummaryView(
        material_id=line_item.material_id,
        material_name=line_item.material_name,
        required_kg=line_item.required_kg,
        required_kg_display=_format_quantity(line_item.required_kg),
        required_with_overage_kg=line_item.required_with_overage_kg,
        required_with_overage_kg_display=_format_quantity(
            line_item.required_with_overage_kg,
        ),
        purchased_kg=line_item.purchased_kg,
        purchased_kg_display=_format_quantity(line_item.purchased_kg),
        waste_kg=line_item.waste_kg,
        waste_kg_display=_format_quantity(line_item.waste_kg),
        cost_incl_vat=line_item.cost_incl_vat,
        cost_incl_vat_display=_format_price(line_item.cost_incl_vat),
        suppliers=" + ".join(supplier_ids),
    )


def render_purchase_list(purchase_list: PurchaseList) -> PurchaseListView:
    """Reshape a :class:`PurchaseList` into a frozen, display-ready view.

    Each :class:`PurchaseAllocation` becomes one
    :class:`PurchaseLineItemView` placed under the
    :class:`SupplierGroupView` matching its ``supplier_id``. Suppliers
    are sorted alphabetically; rows inside a supplier group preserve the
    input ``line_items`` order. Subtotals and grand totals are echoed
    from the input without recomputation.
    """
    rows_by_supplier: dict[str, list[PurchaseLineItemView]] = {}
    for line_item in purchase_list.line_items:
        for allocation in line_item.allocations:
            rows_by_supplier.setdefault(allocation.supplier_id, []).append(
                _line_item_view(line_item, allocation),
            )

    suppliers = [
        SupplierGroupView(
            supplier_id=subtotal.supplier_id,
            line_items=rows_by_supplier.get(subtotal.supplier_id, []),
            subtotal_incl_vat=subtotal.subtotal_incl_vat,
            subtotal_incl_vat_display=_format_price(subtotal.subtotal_incl_vat),
            item_count=subtotal.item_count,
        )
        for subtotal in sorted(
            purchase_list.suppliers,
            key=lambda sub: sub.supplier_id,
        )
    ]

    materials = [_summary_view(line_item) for line_item in purchase_list.line_items]

    return PurchaseListView(
        suppliers=suppliers,
        materials=materials,
        total_cost_incl_vat=purchase_list.total_cost_incl_vat,
        total_cost_incl_vat_display=_format_price(purchase_list.total_cost_incl_vat),
        total_waste_kg=purchase_list.total_waste_kg,
        total_waste_kg_display=_format_quantity(purchase_list.total_waste_kg),
    )
