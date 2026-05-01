"""Tests for the Excel writers in :mod:`mixsheet.export.excel`."""

from __future__ import annotations

import sys
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from openpyxl import load_workbook

from mixsheet.domain import (
    ComponentBreakdown,
    ComponentMixSheetView,
    MaterialBreakdownRow,
    PurchaseAllocation,
    PurchaseLineItem,
    PurchaseList,
    SupplierSubtotal,
    render_component_mixsheet,
    render_purchase_list,
)
from mixsheet.export import (
    MissingExcelExtraError,
    ProjectHeader,
    write_mixsheet_workbook,
    write_purchase_workbook,
)
from mixsheet.export.excel import _safe_tab_name

if TYPE_CHECKING:
    from pathlib import Path


def _project_header() -> ProjectHeader:
    return ProjectHeader(
        project_name="Router gantry",
        generation_date="2026-05-01",
        strategy="cheapest",
        overage_display="10%",
    )


def _line_item(  # noqa: PLR0913
    *,
    material_id: str,
    material_name: str,
    required_kg: str,
    purchased_kg: str,
    waste_kg: str,
    cost_incl_vat: str,
    allocations: list[PurchaseAllocation],
) -> PurchaseLineItem:
    return PurchaseLineItem(
        material_id=material_id,
        material_name=material_name,
        required_kg=Decimal(required_kg),
        required_with_overage_kg=Decimal(required_kg),
        purchased_kg=Decimal(purchased_kg),
        waste_kg=Decimal(waste_kg),
        cost_incl_vat=Decimal(cost_incl_vat),
        allocations=allocations,
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


def _single_supplier_purchase_list() -> PurchaseList:
    return _purchase_list(
        line_items=[
            _line_item(
                material_id="cement",
                material_name="Cement",
                required_kg="9.6",
                purchased_kg="9.6",
                waste_kg="0",
                cost_incl_vat="36.00",
                allocations=[
                    _allocation(
                        package_id="acme-9p6",
                        supplier_id="acme",
                        weight_kg="9.6",
                        price_incl_vat="36.00",
                        count=1,
                    ),
                ],
            ),
        ],
        suppliers=[
            SupplierSubtotal(
                supplier_id="acme",
                subtotal_incl_vat=Decimal("36.00"),
                item_count=1,
            ),
        ],
        total_cost_incl_vat="36.00",
        total_waste_kg="0",
    )


def _cross_supplier_purchase_list() -> PurchaseList:
    return _purchase_list(
        line_items=[
            _line_item(
                material_id="cement",
                material_name="Cement",
                required_kg="124",
                purchased_kg="124",
                waste_kg="0",
                cost_incl_vat="150.00",
                allocations=[
                    _allocation(
                        package_id="acme-100",
                        supplier_id="acme",
                        weight_kg="100",
                        price_incl_vat="120.00",
                        count=1,
                    ),
                    _allocation(
                        package_id="beta-24",
                        supplier_id="beta",
                        weight_kg="24",
                        price_incl_vat="30.00",
                        count=1,
                    ),
                ],
            ),
        ],
        suppliers=[
            SupplierSubtotal(
                supplier_id="acme",
                subtotal_incl_vat=Decimal("120.00"),
                item_count=1,
            ),
            SupplierSubtotal(
                supplier_id="beta",
                subtotal_incl_vat=Decimal("30.00"),
                item_count=1,
            ),
        ],
        total_cost_incl_vat="150.00",
        total_waste_kg="0",
    )


def _component_view(component_id: str, component_name: str) -> ComponentMixSheetView:
    breakdown = ComponentBreakdown(
        component_id=component_id,
        preset_id="epoxy-mix",
        preset_name="Epoxy granite",
        density_kg_per_l=Decimal("1.91"),
        quantity=1,
        volume_per_component_l=Decimal("3.46"),
        net_volume_l=Decimal("3.46"),
        weight_per_component_kg=Decimal("6.30"),
        total_weight_kg=Decimal("6.30"),
        materials=[
            MaterialBreakdownRow(
                material_id="cement",
                material_name="Cement",
                weight_per_component_kg=Decimal("0.62"),
                weight_kg=Decimal("0.62"),
            ),
        ],
    )
    return render_component_mixsheet(breakdown, component_name=component_name)


class TestSafeTabName:
    def test_truncates_to_31_chars(self) -> None:
        used: set[str] = set()
        name = "Acme Industrial Supplies and Concrete Mix Co."

        result = _safe_tab_name(name, "fallback", used)

        assert len(result) == 31
        assert name.startswith(result)

    def test_sanitises_forbidden_characters(self) -> None:
        used: set[str] = set()

        result = _safe_tab_name("bed/main", "fallback", used)

        assert result == "bed_main"

    def test_collision_appends_numeric_suffix(self) -> None:
        used: set[str] = set()
        long_name = "Acme Industrial Supplies and Concrete Mix Co."

        first = _safe_tab_name(long_name, "fallback-a", used)
        second = _safe_tab_name(long_name, "fallback-b", used)

        assert len(first) == 31
        assert len(second) == 31
        assert second.endswith("~2")
        assert first != second

    def test_falls_back_to_id_when_name_empty(self) -> None:
        used: set[str] = set()

        result = _safe_tab_name("   ", "supplier-id", used)

        assert result == "supplier-id"


class TestPurchaseWorkbook:
    def test_writes_file_with_overview_and_one_supplier_sheet(self, tmp_path: Path) -> None:
        view = render_purchase_list(_single_supplier_purchase_list())
        path = tmp_path / "purchase.xlsx"

        write_purchase_workbook(view, _project_header(), path)

        assert path.exists()
        wb = load_workbook(path)
        assert wb.sheetnames[0] == "Overview"
        assert wb.sheetnames[1:] == ["acme"]

    def test_overview_carries_per_material_row_with_formats(self, tmp_path: Path) -> None:
        view = render_purchase_list(_single_supplier_purchase_list())
        path = tmp_path / "purchase.xlsx"

        write_purchase_workbook(view, _project_header(), path)

        wb = load_workbook(path)
        overview = wb["Overview"]
        material_row = next(
            row for row in overview.iter_rows(values_only=False) if row[0].value == "Cement"
        )
        assert material_row[1].value == 9.6
        assert material_row[1].number_format == "0.0"
        assert material_row[5].value == 36.0
        assert "€" in material_row[5].number_format

    def test_cross_supplier_overview_lists_both_suppliers(self, tmp_path: Path) -> None:
        view = render_purchase_list(_cross_supplier_purchase_list())
        path = tmp_path / "purchase.xlsx"

        write_purchase_workbook(view, _project_header(), path)

        wb = load_workbook(path)
        overview = wb["Overview"]
        material_row = next(
            row for row in overview.iter_rows(values_only=True) if row and row[0] == "Cement"
        )
        assert material_row[4] == "acme + beta"

    def test_supplier_sheets_carry_only_their_slice(self, tmp_path: Path) -> None:
        view = render_purchase_list(_cross_supplier_purchase_list())
        path = tmp_path / "purchase.xlsx"

        write_purchase_workbook(view, _project_header(), path)

        wb = load_workbook(path)
        assert wb.sheetnames == ["Overview", "acme", "beta"]
        acme = wb["acme"]
        material_rows = [
            row for row in acme.iter_rows(values_only=True) if row and row[0] == "Cement"
        ]
        assert len(material_rows) == 1

    def test_high_quantity_uses_zero_decimals_format(self, tmp_path: Path) -> None:
        view = render_purchase_list(_cross_supplier_purchase_list())
        path = tmp_path / "purchase.xlsx"

        write_purchase_workbook(view, _project_header(), path)

        wb = load_workbook(path)
        overview = wb["Overview"]
        material_row = next(
            row for row in overview.iter_rows(values_only=False) if row[0].value == "Cement"
        )
        assert material_row[1].value == 124
        assert material_row[1].number_format == "0"

    def test_empty_view_yields_overview_only(self, tmp_path: Path) -> None:
        empty = _purchase_list(
            line_items=[],
            suppliers=[],
            total_cost_incl_vat="0",
            total_waste_kg="0",
        )
        view = render_purchase_list(empty)
        path = tmp_path / "purchase.xlsx"

        write_purchase_workbook(view, _project_header(), path)

        wb = load_workbook(path)
        assert wb.sheetnames == ["Overview"]

    def test_reproducible_across_calls(self, tmp_path: Path) -> None:
        view = render_purchase_list(_single_supplier_purchase_list())
        path_a = tmp_path / "a.xlsx"
        path_b = tmp_path / "b.xlsx"

        write_purchase_workbook(view, _project_header(), path_a)
        write_purchase_workbook(view, _project_header(), path_b)

        cells_a = _all_cells(path_a)
        cells_b = _all_cells(path_b)
        assert cells_a == cells_b


class TestMixsheetWorkbook:
    def test_one_sheet_per_component_in_input_order(self, tmp_path: Path) -> None:
        views = [_component_view("bed", "Bed"), _component_view("cross-slide", "Cross slide")]
        path = tmp_path / "mixsheets.xlsx"

        write_mixsheet_workbook(views, _project_header(), path)

        wb = load_workbook(path)
        assert wb.sheetnames == ["Bed", "Cross slide"]

    def test_component_sheet_header_carries_view_data(self, tmp_path: Path) -> None:
        views = [_component_view("bed", "Bed")]
        path = tmp_path / "mixsheets.xlsx"

        write_mixsheet_workbook(views, _project_header(), path)

        wb = load_workbook(path)
        sheet = wb["Bed"]
        labels = {row[0]: row[1] for row in sheet.iter_rows(values_only=True) if row[0]}
        assert labels["Project"] == "Router gantry"
        assert labels["Component"] == "Bed"
        assert labels["Preset"] == "Epoxy granite"
        assert labels["Quantity"] == 1

    def test_empty_views_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "mixsheets.xlsx"

        with pytest.raises(ValueError, match="at least one component view"):
            write_mixsheet_workbook([], _project_header(), path)


class TestMissingExtra:
    def test_missing_xlsxwriter_raises_with_install_hint(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setitem(sys.modules, "xlsxwriter", None)
        view = render_purchase_list(_single_supplier_purchase_list())
        path = tmp_path / "purchase.xlsx"

        with pytest.raises(MissingExcelExtraError) as excinfo:
            write_purchase_workbook(view, _project_header(), path)

        assert "uv add mixsheet[export]" in str(excinfo.value)


def _all_cells(path: Path) -> dict[str, list[tuple[object, str]]]:
    wb = load_workbook(path)
    result: dict[str, list[tuple[object, str]]] = {}
    for name in wb.sheetnames:
        sheet = wb[name]
        result[name] = [
            (cell.value, cell.number_format) for row in sheet.iter_rows() for cell in row
        ]
    return result
