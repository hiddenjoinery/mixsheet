"""Tests for the pure purchase-list renderer."""

from __future__ import annotations

from decimal import Decimal

import pytest

from mixsheet.domain import (
    PurchaseAllocation,
    PurchaseLineItem,
    PurchaseList,
    PurchaseListView,
    SupplierSubtotal,
    render_purchase_list,
)


def _allocation(
    *,
    package_id: str,
    supplier_id: str,
    weight_kg: str,
    price_incl_vat: str,
    count: int,
) -> PurchaseAllocation:
    return PurchaseAllocation(
        package_id=package_id,
        supplier_id=supplier_id,
        package_weight_kg=Decimal(weight_kg),
        package_price_incl_vat=Decimal(price_incl_vat),
        count=count,
    )


def _line_item(  # noqa: PLR0913
    *,
    material_id: str,
    material_name: str,
    required_kg: str,
    required_with_overage_kg: str,
    purchased_kg: str,
    waste_kg: str,
    cost_incl_vat: str,
    allocations: list[PurchaseAllocation],
) -> PurchaseLineItem:
    return PurchaseLineItem(
        material_id=material_id,
        material_name=material_name,
        required_kg=Decimal(required_kg),
        required_with_overage_kg=Decimal(required_with_overage_kg),
        purchased_kg=Decimal(purchased_kg),
        waste_kg=Decimal(waste_kg),
        cost_incl_vat=Decimal(cost_incl_vat),
        allocations=allocations,
    )


def _subtotal(*, supplier_id: str, subtotal: str, item_count: int) -> SupplierSubtotal:
    return SupplierSubtotal(
        supplier_id=supplier_id,
        subtotal_incl_vat=Decimal(subtotal),
        item_count=item_count,
    )


def _purchase_list(
    *,
    line_items: list[PurchaseLineItem],
    suppliers: list[SupplierSubtotal],
    total_cost_incl_vat: str,
    total_waste_kg: str,
) -> PurchaseList:
    return PurchaseList(
        line_items=line_items,
        suppliers=suppliers,
        total_cost_incl_vat=Decimal(total_cost_incl_vat),
        total_waste_kg=Decimal(total_waste_kg),
    )


class TestSingleSupplierSingleAllocation:
    def test_returns_frozen_view_with_populated_fields(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="20",
                    required_with_overage_kg="20",
                    purchased_kg="25",
                    waste_kg="5",
                    cost_incl_vat="30.00",
                    allocations=[
                        _allocation(
                            package_id="acme-25",
                            supplier_id="acme",
                            weight_kg="25",
                            price_incl_vat="30.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="acme", subtotal="30.00", item_count=1)],
            total_cost_incl_vat="30.00",
            total_waste_kg="5",
        )

        view = render_purchase_list(purchase_list)

        assert view.model_config.get("frozen") is True
        with pytest.raises(ValueError, match="frozen"):
            view.suppliers[0].line_items[0].material_id = "x"  # type: ignore[misc]

        assert len(view.suppliers) == 1
        group = view.suppliers[0]
        assert group.supplier_id == "acme"
        assert len(group.line_items) == 1
        row = group.line_items[0]
        assert row.material_id == "cement"
        assert row.material_name == "Cement"
        assert row.package_count == 1
        assert row.allocation_cost_incl_vat == Decimal("30.00")
        assert row.allocation_cost_incl_vat_display == "€ 30.00"
        assert len(row.allocations) == 1
        assert row.allocations[0].package_id == "acme-25"


class TestCrossSupplierFanOut:
    def test_cross_supplier_line_item_splits_into_two_rows(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="28",
                    required_with_overage_kg="28",
                    purchased_kg="30",
                    waste_kg="2",
                    cost_incl_vat="36.00",
                    allocations=[
                        _allocation(
                            package_id="a-25",
                            supplier_id="A",
                            weight_kg="25",
                            price_incl_vat="30.00",
                            count=1,
                        ),
                        _allocation(
                            package_id="b-05",
                            supplier_id="B",
                            weight_kg="5",
                            price_incl_vat="6.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[
                _subtotal(supplier_id="A", subtotal="30.00", item_count=1),
                _subtotal(supplier_id="B", subtotal="6.00", item_count=1),
            ],
            total_cost_incl_vat="36.00",
            total_waste_kg="2",
        )

        view = render_purchase_list(purchase_list)

        groups = {group.supplier_id: group for group in view.suppliers}
        assert set(groups) == {"A", "B"}
        assert len(groups["A"].line_items) == 1
        assert len(groups["B"].line_items) == 1
        assert groups["A"].line_items[0].material_id == "cement"
        assert groups["A"].line_items[0].allocation_cost_incl_vat == Decimal("30.00")
        assert groups["B"].line_items[0].material_id == "cement"
        assert groups["B"].line_items[0].allocation_cost_incl_vat == Decimal("6.00")


class TestSingleSupplierMultiPackageAllocation:
    def test_one_row_with_package_count_two_and_full_cost(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="40",
                    required_with_overage_kg="40",
                    purchased_kg="50",
                    waste_kg="10",
                    cost_incl_vat="60.00",
                    allocations=[
                        _allocation(
                            package_id="acme-25",
                            supplier_id="acme",
                            weight_kg="25",
                            price_incl_vat="30.00",
                            count=2,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="acme", subtotal="60.00", item_count=2)],
            total_cost_incl_vat="60.00",
            total_waste_kg="10",
        )

        view = render_purchase_list(purchase_list)

        group = view.suppliers[0]
        assert len(group.line_items) == 1
        row = group.line_items[0]
        assert row.package_count == 2
        assert row.allocation_cost_incl_vat == Decimal("60.00")
        assert row.allocation_cost_incl_vat == purchase_list.line_items[0].cost_incl_vat


class TestSupplierOrdering:
    def test_alphabetical_supplier_ordering(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id=mat,
                    material_name=mat.title(),
                    required_kg="5",
                    required_with_overage_kg="5",
                    purchased_kg="5",
                    waste_kg="0",
                    cost_incl_vat="5.00",
                    allocations=[
                        _allocation(
                            package_id=f"{sup}-pkg",
                            supplier_id=sup,
                            weight_kg="5",
                            price_incl_vat="5.00",
                            count=1,
                        ),
                    ],
                )
                for mat, sup in [("m1", "bcs"), ("m2", "acme"), ("m3", "delta")]
            ],
            suppliers=[
                _subtotal(supplier_id="bcs", subtotal="5.00", item_count=1),
                _subtotal(supplier_id="acme", subtotal="5.00", item_count=1),
                _subtotal(supplier_id="delta", subtotal="5.00", item_count=1),
            ],
            total_cost_incl_vat="15.00",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        assert [group.supplier_id for group in view.suppliers] == [
            "acme",
            "bcs",
            "delta",
        ]


class TestLineItemOrdering:
    def test_preserves_input_order_within_group(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="aggregate-fines",
                    material_name="Aggregate fines",
                    required_kg="5",
                    required_with_overage_kg="5",
                    purchased_kg="5",
                    waste_kg="0",
                    cost_incl_vat="5.00",
                    allocations=[
                        _allocation(
                            package_id="A-agg",
                            supplier_id="A",
                            weight_kg="5",
                            price_incl_vat="5.00",
                            count=1,
                        ),
                    ],
                ),
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="10",
                    required_with_overage_kg="10",
                    purchased_kg="10",
                    waste_kg="0",
                    cost_incl_vat="12.00",
                    allocations=[
                        _allocation(
                            package_id="B-cement",
                            supplier_id="B",
                            weight_kg="10",
                            price_incl_vat="12.00",
                            count=1,
                        ),
                    ],
                ),
                _line_item(
                    material_id="quartz-sand",
                    material_name="Quartz sand",
                    required_kg="8",
                    required_with_overage_kg="8",
                    purchased_kg="8",
                    waste_kg="0",
                    cost_incl_vat="8.00",
                    allocations=[
                        _allocation(
                            package_id="A-quartz",
                            supplier_id="A",
                            weight_kg="8",
                            price_incl_vat="8.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[
                _subtotal(supplier_id="A", subtotal="13.00", item_count=2),
                _subtotal(supplier_id="B", subtotal="12.00", item_count=1),
            ],
            total_cost_incl_vat="25.00",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        groups = {group.supplier_id: group for group in view.suppliers}
        assert [row.material_id for row in groups["A"].line_items] == [
            "aggregate-fines",
            "quartz-sand",
        ]
        assert [row.material_id for row in groups["B"].line_items] == ["cement"]


class TestQuantityFormatting:
    def _row_with_purchased(self, purchased_kg: str) -> PurchaseListView:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="m",
                    material_name="M",
                    required_kg=purchased_kg,
                    required_with_overage_kg=purchased_kg,
                    purchased_kg=purchased_kg,
                    waste_kg="0",
                    cost_incl_vat="0.00",
                    allocations=[
                        _allocation(
                            package_id="p",
                            supplier_id="s",
                            weight_kg=purchased_kg,
                            price_incl_vat="0.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="s", subtotal="0.00", item_count=1)],
            total_cost_incl_vat="0.00",
            total_waste_kg="0",
        )
        return render_purchase_list(purchase_list)

    def test_9_99_rounds_to_one_decimal(self) -> None:
        view = self._row_with_purchased("9.99")
        assert view.suppliers[0].line_items[0].purchased_kg_display == "10.0"

    def test_10_00_uses_one_decimal(self) -> None:
        view = self._row_with_purchased("10.00")
        assert view.suppliers[0].line_items[0].purchased_kg_display == "10.0"

    def test_10_01_rounds_to_zero_decimals(self) -> None:
        view = self._row_with_purchased("10.01")
        assert view.suppliers[0].line_items[0].purchased_kg_display == "10"

    def test_mixed_magnitude_column_keeps_per_cell_precision(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="small",
                    material_name="Small",
                    required_kg="9.6",
                    required_with_overage_kg="9.6",
                    purchased_kg="9.6",
                    waste_kg="0",
                    cost_incl_vat="0.00",
                    allocations=[
                        _allocation(
                            package_id="p1",
                            supplier_id="s",
                            weight_kg="9.6",
                            price_incl_vat="0.00",
                            count=1,
                        ),
                    ],
                ),
                _line_item(
                    material_id="big",
                    material_name="Big",
                    required_kg="124",
                    required_with_overage_kg="124",
                    purchased_kg="124",
                    waste_kg="0",
                    cost_incl_vat="0.00",
                    allocations=[
                        _allocation(
                            package_id="p2",
                            supplier_id="s",
                            weight_kg="124",
                            price_incl_vat="0.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="s", subtotal="0.00", item_count=2)],
            total_cost_incl_vat="0.00",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        rows = view.suppliers[0].line_items
        displays = {row.material_id: row.purchased_kg_display for row in rows}
        assert displays == {"small": "9.6", "big": "124"}


class TestPriceFormatting:
    def _view_with_total(self, total: str) -> PurchaseListView:
        purchase_list = _purchase_list(
            line_items=[],
            suppliers=[],
            total_cost_incl_vat=total,
            total_waste_kg="0",
        )
        return render_purchase_list(purchase_list)

    def test_decimal_30_formats_with_two_decimals(self) -> None:
        view = self._view_with_total("30")
        assert view.total_cost_incl_vat_display == "€ 30.00"

    def test_30_005_rounds_half_up(self) -> None:
        view = self._view_with_total("30.005")
        assert view.total_cost_incl_vat_display == "€ 30.01"


class TestRawAndFormattedParity:
    def test_raw_decimal_preserves_full_precision(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="12.345678",
                    required_with_overage_kg="12.345678",
                    purchased_kg="15",
                    waste_kg="2.654322",
                    cost_incl_vat="20.00",
                    allocations=[
                        _allocation(
                            package_id="p",
                            supplier_id="s",
                            weight_kg="15",
                            price_incl_vat="20.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="s", subtotal="20.00", item_count=1)],
            total_cost_incl_vat="20.00",
            total_waste_kg="2.654322",
        )

        view = render_purchase_list(purchase_list)

        row = view.suppliers[0].line_items[0]
        assert row.required_kg == Decimal("12.345678")
        assert row.required_kg_display == "12"
        assert row.allocation_cost_incl_vat == Decimal("20.00")
        assert row.allocation_cost_incl_vat_display == "€ 20.00"


class TestSupplierSubtotalEcho:
    def test_subtotal_carried_through_and_rows_sum(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="20",
                    required_with_overage_kg="20",
                    purchased_kg="25",
                    waste_kg="5",
                    cost_incl_vat="30.00",
                    allocations=[
                        _allocation(
                            package_id="p25",
                            supplier_id="A",
                            weight_kg="25",
                            price_incl_vat="30.00",
                            count=1,
                        ),
                    ],
                ),
                _line_item(
                    material_id="sand",
                    material_name="Sand",
                    required_kg="50",
                    required_with_overage_kg="50",
                    purchased_kg="50",
                    waste_kg="0",
                    cost_incl_vat="70.00",
                    allocations=[
                        _allocation(
                            package_id="p50",
                            supplier_id="A",
                            weight_kg="25",
                            price_incl_vat="35.00",
                            count=2,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="A", subtotal="100.00", item_count=3)],
            total_cost_incl_vat="100.00",
            total_waste_kg="5",
        )

        view = render_purchase_list(purchase_list)

        group = view.suppliers[0]
        assert group.subtotal_incl_vat == Decimal("100.00")
        assert group.item_count == 3
        assert group.subtotal_incl_vat_display == "€ 100.00"
        rows_sum = sum(
            (row.allocation_cost_incl_vat for row in group.line_items),
            start=Decimal("0"),
        )
        assert rows_sum == group.subtotal_incl_vat


class TestGrandTotalEcho:
    def test_grand_total_carried_through_and_supplier_sum_matches(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="20",
                    required_with_overage_kg="20",
                    purchased_kg="25",
                    waste_kg="5",
                    cost_incl_vat="30.00",
                    allocations=[
                        _allocation(
                            package_id="A-25",
                            supplier_id="A",
                            weight_kg="25",
                            price_incl_vat="30.00",
                            count=1,
                        ),
                    ],
                ),
                _line_item(
                    material_id="sand",
                    material_name="Sand",
                    required_kg="20",
                    required_with_overage_kg="20",
                    purchased_kg="20",
                    waste_kg="0",
                    cost_incl_vat="20.00",
                    allocations=[
                        _allocation(
                            package_id="B-20",
                            supplier_id="B",
                            weight_kg="20",
                            price_incl_vat="20.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[
                _subtotal(supplier_id="A", subtotal="30.00", item_count=1),
                _subtotal(supplier_id="B", subtotal="20.00", item_count=1),
            ],
            total_cost_incl_vat="50.00",
            total_waste_kg="5",
        )

        view = render_purchase_list(purchase_list)

        assert view.total_cost_incl_vat == Decimal("50.00")
        assert view.total_cost_incl_vat_display == "€ 50.00"
        assert view.total_waste_kg == Decimal("5")
        assert view.total_waste_kg_display == "5.0"
        suppliers_sum = sum(
            (group.subtotal_incl_vat for group in view.suppliers),
            start=Decimal("0"),
        )
        assert suppliers_sum == view.total_cost_incl_vat


class TestEmptyPurchaseList:
    def test_empty_input_produces_empty_view(self) -> None:
        purchase_list = _purchase_list(
            line_items=[],
            suppliers=[],
            total_cost_incl_vat="0",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        assert view.suppliers == []
        assert view.total_cost_incl_vat == Decimal("0")
        assert view.total_cost_incl_vat_display == "€ 0.00"
        assert view.total_waste_kg == Decimal("0")
        assert view.total_waste_kg_display == "0.0"


class TestMaterialsSummary:
    def test_length_matches_input_and_preserves_order(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="aggregate",
                    material_name="Aggregate",
                    required_kg="5",
                    required_with_overage_kg="5",
                    purchased_kg="5",
                    waste_kg="0",
                    cost_incl_vat="5.00",
                    allocations=[
                        _allocation(
                            package_id="acme-5",
                            supplier_id="acme",
                            weight_kg="5",
                            price_incl_vat="5.00",
                            count=1,
                        ),
                    ],
                ),
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="10",
                    required_with_overage_kg="10",
                    purchased_kg="10",
                    waste_kg="0",
                    cost_incl_vat="12.00",
                    allocations=[
                        _allocation(
                            package_id="acme-10",
                            supplier_id="acme",
                            weight_kg="10",
                            price_incl_vat="12.00",
                            count=1,
                        ),
                    ],
                ),
                _line_item(
                    material_id="sand",
                    material_name="Sand",
                    required_kg="8",
                    required_with_overage_kg="8",
                    purchased_kg="8",
                    waste_kg="0",
                    cost_incl_vat="8.00",
                    allocations=[
                        _allocation(
                            package_id="acme-8",
                            supplier_id="acme",
                            weight_kg="8",
                            price_incl_vat="8.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="acme", subtotal="25.00", item_count=3)],
            total_cost_incl_vat="25.00",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        assert [row.material_id for row in view.materials] == [
            "aggregate",
            "cement",
            "sand",
        ]

    def test_single_supplier_reports_one_supplier_id(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="50",
                    required_with_overage_kg="50",
                    purchased_kg="50",
                    waste_kg="0",
                    cost_incl_vat="60.00",
                    allocations=[
                        _allocation(
                            package_id="acme-25",
                            supplier_id="acme",
                            weight_kg="25",
                            price_incl_vat="30.00",
                            count=2,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="acme", subtotal="60.00", item_count=2)],
            total_cost_incl_vat="60.00",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        assert view.materials[0].suppliers == "acme"

    def test_cross_supplier_joins_alphabetically(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="30",
                    required_with_overage_kg="30",
                    purchased_kg="30",
                    waste_kg="0",
                    cost_incl_vat="36.00",
                    allocations=[
                        _allocation(
                            package_id="bcs-25",
                            supplier_id="bcs",
                            weight_kg="25",
                            price_incl_vat="30.00",
                            count=1,
                        ),
                        _allocation(
                            package_id="acme-5",
                            supplier_id="acme",
                            weight_kg="5",
                            price_incl_vat="6.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[
                _subtotal(supplier_id="acme", subtotal="6.00", item_count=1),
                _subtotal(supplier_id="bcs", subtotal="30.00", item_count=1),
            ],
            total_cost_incl_vat="36.00",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        assert view.materials[0].suppliers == "acme + bcs"

    def test_raw_and_formatted_parity(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="9.6",
                    required_with_overage_kg="9.6",
                    purchased_kg="9.6",
                    waste_kg="0",
                    cost_incl_vat="36",
                    allocations=[
                        _allocation(
                            package_id="acme-9p6",
                            supplier_id="acme",
                            weight_kg="9.6",
                            price_incl_vat="36",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="acme", subtotal="36.00", item_count=1)],
            total_cost_incl_vat="36.00",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        summary = view.materials[0]
        assert summary.purchased_kg == Decimal("9.6")
        assert summary.purchased_kg_display == "9.6"
        assert summary.cost_incl_vat == Decimal("36")
        assert summary.cost_incl_vat_display == "€ 36.00"

    def test_empty_input_yields_empty_materials(self) -> None:
        purchase_list = _purchase_list(
            line_items=[],
            suppliers=[],
            total_cost_incl_vat="0",
            total_waste_kg="0",
        )

        view = render_purchase_list(purchase_list)

        assert view.materials == []


class TestDeterminism:
    def test_two_calls_with_equal_input_return_equal_views(self) -> None:
        purchase_list = _purchase_list(
            line_items=[
                _line_item(
                    material_id="cement",
                    material_name="Cement",
                    required_kg="20",
                    required_with_overage_kg="22",
                    purchased_kg="25",
                    waste_kg="3",
                    cost_incl_vat="30.00",
                    allocations=[
                        _allocation(
                            package_id="acme-25",
                            supplier_id="acme",
                            weight_kg="25",
                            price_incl_vat="30.00",
                            count=1,
                        ),
                    ],
                ),
            ],
            suppliers=[_subtotal(supplier_id="acme", subtotal="30.00", item_count=1)],
            total_cost_incl_vat="30.00",
            total_waste_kg="3",
        )

        view_a = render_purchase_list(purchase_list)
        view_b = render_purchase_list(purchase_list)

        assert view_a == view_b
