"""Excel writers for The Mix Sheet's purchase and mix-sheet artifacts.

The writers consume frozen domain views (:class:`PurchaseListView`,
:class:`ComponentMixSheetView`) plus a :class:`ProjectHeader` and produce
``.xlsx`` workbooks. They never call into the domain layer, never read
any other files, and never mutate inputs.

``xlsxwriter`` is an optional extra; both writers import it lazily inside
the function body. When it is not installed they raise
:class:`MissingExcelExtraError` whose message names the install command
(``uv add mixsheet[export]``) so users see a focused, actionable error.

Per-cell number formats mirror the renderer's threshold rule from
:mod:`mixsheet.domain.display`: quantities use ``"0.0"`` at or below
``QUANTITY_THRESHOLD`` and ``"0"`` strictly above; prices always use
:data:`PRICE_FORMAT`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from mixsheet.domain.display import QUANTITY_THRESHOLD

if TYPE_CHECKING:
    from decimal import Decimal
    from pathlib import Path

    from mixsheet.domain.mixsheet_renderer import ComponentMixSheetView
    from mixsheet.domain.renderer import PurchaseListView


PRICE_FORMAT = "€ #,##0.00"
DENSITY_FORMAT = "0.00"
QUANTITY_FORMAT_LOW = "0.0"
QUANTITY_FORMAT_HIGH = "0"
MAX_TAB_LENGTH = 31
FORBIDDEN_TAB_CHARS = "[]:*?/\\"
INSTALL_HINT = "uv add mixsheet[export]"


class MissingExcelExtraError(ImportError):
    """Raised when ``xlsxwriter`` is not installed in the active environment."""

    def __init__(self) -> None:
        """Build the error with a focused install hint."""
        super().__init__(
            f"xlsxwriter is required for Excel export. Install with '{INSTALL_HINT}'.",
        )


class ProjectHeader(BaseModel):
    """Run-config strings stamped on every workbook header block."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_name: str = Field(min_length=1)
    generation_date: str = Field(min_length=1)
    strategy: str = Field(min_length=1)
    overage_display: str = Field(min_length=1)


def _import_xlsxwriter() -> Any:
    try:
        import xlsxwriter  # noqa: PLC0415
    except ImportError as exc:
        raise MissingExcelExtraError from exc
    return xlsxwriter


def _quantity_format(value: Decimal) -> str:
    """Return the per-cell quantity format string for ``value``."""
    if abs(value) <= QUANTITY_THRESHOLD:
        return QUANTITY_FORMAT_LOW
    return QUANTITY_FORMAT_HIGH


def _sanitise_tab(raw: str) -> str:
    cleaned = raw
    for char in FORBIDDEN_TAB_CHARS:
        cleaned = cleaned.replace(char, "_")
    return cleaned


def _safe_tab_name(name: str, fallback_id: str, used: set[str]) -> str:
    """Return a unique, Excel-safe tab name within the 31-char budget."""
    base = name.strip() or fallback_id
    sanitised = _sanitise_tab(base)
    candidate = sanitised[:MAX_TAB_LENGTH]
    if candidate not in used:
        used.add(candidate)
        return candidate
    suffix_index = 2
    while True:
        suffix = f"~{suffix_index}"
        truncated = sanitised[: MAX_TAB_LENGTH - len(suffix)] + suffix
        if truncated not in used:
            used.add(truncated)
            return truncated
        suffix_index += 1


def _decimal_to_number(value: Decimal) -> float:
    """Cast a ``Decimal`` to ``float`` at the xlsxwriter boundary."""
    return float(value)


def write_purchase_workbook(
    view: PurchaseListView,
    project_header: ProjectHeader,
    output_path: Path,
) -> None:
    """Write the purchase workbook (Overview + one sheet per supplier).

    The Overview sheet carries a header block, a per-material table, a
    per-supplier table, and grand totals. One sheet follows per supplier
    in the view's order (alphabetical by ``supplier_id``). Quantity cells
    use ``"0.0"`` or ``"0"`` per cell; price cells use
    :data:`PRICE_FORMAT`.
    """
    xlsxwriter = _import_xlsxwriter()
    workbook = xlsxwriter.Workbook(str(output_path))
    try:
        bold = workbook.add_format({"bold": True})
        price_fmt = workbook.add_format({"num_format": PRICE_FORMAT})
        qty_low_fmt = workbook.add_format({"num_format": QUANTITY_FORMAT_LOW})
        qty_high_fmt = workbook.add_format({"num_format": QUANTITY_FORMAT_HIGH})

        def qty_format(value: Decimal) -> Any:
            if abs(value) <= QUANTITY_THRESHOLD:
                return qty_low_fmt
            return qty_high_fmt

        _write_overview_sheet(
            workbook=workbook,
            view=view,
            project_header=project_header,
            bold=bold,
            price_fmt=price_fmt,
            qty_format=qty_format,
        )
        used_tabs: set[str] = {"Overview"}
        for group in view.suppliers:
            tab = _safe_tab_name(group.supplier_id, group.supplier_id, used_tabs)
            _write_supplier_sheet(
                workbook=workbook,
                tab=tab,
                group=group,
                project_header=project_header,
                bold=bold,
                price_fmt=price_fmt,
                qty_format=qty_format,
            )
    finally:
        workbook.close()


def _write_overview_sheet(  # noqa: PLR0913
    *,
    workbook: Any,
    view: PurchaseListView,
    project_header: ProjectHeader,
    bold: Any,
    price_fmt: Any,
    qty_format: Any,
) -> None:
    sheet = workbook.add_worksheet("Overview")
    row = 0
    sheet.write(row, 0, "Project", bold)
    sheet.write(row, 1, project_header.project_name)
    row += 1
    sheet.write(row, 0, "Strategy", bold)
    sheet.write(row, 1, project_header.strategy)
    row += 1
    sheet.write(row, 0, "Overage", bold)
    sheet.write(row, 1, project_header.overage_display)
    row += 1
    sheet.write(row, 0, "Generated", bold)
    sheet.write(row, 1, project_header.generation_date)
    row += 2

    materials_header = ["Material", "Required", "Purchased", "Waste", "Suppliers", "Cost"]
    for col, label in enumerate(materials_header):
        sheet.write(row, col, label, bold)
    row += 1
    for material in view.materials:
        sheet.write(row, 0, material.material_name)
        sheet.write_number(
            row,
            1,
            _decimal_to_number(material.required_kg),
            qty_format(material.required_kg),
        )
        sheet.write_number(
            row,
            2,
            _decimal_to_number(material.purchased_kg),
            qty_format(material.purchased_kg),
        )
        sheet.write_number(
            row,
            3,
            _decimal_to_number(material.waste_kg),
            qty_format(material.waste_kg),
        )
        sheet.write(row, 4, material.suppliers)
        sheet.write_number(
            row,
            5,
            _decimal_to_number(material.cost_incl_vat),
            price_fmt,
        )
        row += 1
    row += 1

    suppliers_header = ["Supplier", "Items", "Subtotal"]
    for col, label in enumerate(suppliers_header):
        sheet.write(row, col, label, bold)
    row += 1
    for group in view.suppliers:
        sheet.write(row, 0, group.supplier_id)
        sheet.write_number(row, 1, group.item_count)
        sheet.write_number(
            row,
            2,
            _decimal_to_number(group.subtotal_incl_vat),
            price_fmt,
        )
        row += 1
    row += 1

    sheet.write(row, 0, "Total cost", bold)
    sheet.write_number(
        row,
        1,
        _decimal_to_number(view.total_cost_incl_vat),
        price_fmt,
    )
    row += 1
    sheet.write(row, 0, "Total waste", bold)
    sheet.write_number(
        row,
        1,
        _decimal_to_number(view.total_waste_kg),
        qty_format(view.total_waste_kg),
    )


def _write_supplier_sheet(  # noqa: PLR0913
    *,
    workbook: Any,
    tab: str,
    group: Any,
    project_header: ProjectHeader,
    bold: Any,
    price_fmt: Any,
    qty_format: Any,
) -> None:
    sheet = workbook.add_worksheet(tab)
    sheet.write(0, 0, group.supplier_id, bold)
    sheet.write(0, 1, project_header.project_name)
    row = 2
    header = ["Material", "Package", "Count", "€ each", "€ row"]
    for col, label in enumerate(header):
        sheet.write(row, col, label, bold)
    row += 1
    for line_item in group.line_items:
        allocation = line_item.allocations[0]
        sheet.write(row, 0, line_item.material_name)
        sheet.write_number(
            row,
            1,
            _decimal_to_number(allocation.package_weight_kg),
            qty_format(allocation.package_weight_kg),
        )
        sheet.write_number(row, 2, line_item.package_count)
        sheet.write_number(
            row,
            3,
            _decimal_to_number(allocation.package_price_incl_vat),
            price_fmt,
        )
        sheet.write_number(
            row,
            4,
            _decimal_to_number(line_item.allocation_cost_incl_vat),
            price_fmt,
        )
        row += 1
    sheet.write(row, 0, "Subtotal", bold)
    sheet.write_number(
        row,
        4,
        _decimal_to_number(group.subtotal_incl_vat),
        price_fmt,
    )


def write_mixsheet_workbook(
    views: list[ComponentMixSheetView],
    project_header: ProjectHeader,
    output_path: Path,
) -> None:
    """Write the mix-sheet workbook (one sheet per component, in input order).

    Each sheet carries a header block (project, component, preset name +
    version, density, quantity, volume per component, net volume, weight
    per component, total weight) and a single material table.
    """
    if not views:
        msg = "write_mixsheet_workbook requires at least one component view"
        raise ValueError(msg)
    xlsxwriter = _import_xlsxwriter()
    workbook = xlsxwriter.Workbook(str(output_path))
    try:
        bold = workbook.add_format({"bold": True})
        density_fmt = workbook.add_format({"num_format": DENSITY_FORMAT})
        qty_low_fmt = workbook.add_format({"num_format": QUANTITY_FORMAT_LOW})
        qty_high_fmt = workbook.add_format({"num_format": QUANTITY_FORMAT_HIGH})

        def qty_format(value: Decimal) -> Any:
            if abs(value) <= QUANTITY_THRESHOLD:
                return qty_low_fmt
            return qty_high_fmt

        used_tabs: set[str] = set()
        for view in views:
            tab = _safe_tab_name(view.component_name, view.component_id, used_tabs)
            _write_component_sheet(
                workbook=workbook,
                tab=tab,
                view=view,
                project_header=project_header,
                bold=bold,
                density_fmt=density_fmt,
                qty_format=qty_format,
            )
    finally:
        workbook.close()


def _write_component_sheet(  # noqa: PLR0913
    *,
    workbook: Any,
    tab: str,
    view: ComponentMixSheetView,
    project_header: ProjectHeader,
    bold: Any,
    density_fmt: Any,
    qty_format: Any,
) -> None:
    sheet = workbook.add_worksheet(tab)
    row = 0
    header_pairs: list[tuple[str, Any, Any]] = [
        ("Project", project_header.project_name, None),
        ("Component", view.component_name, None),
        ("Preset", view.preset_name, None),
        ("Density", _decimal_to_number(view.density_kg_per_l), density_fmt),
        ("Quantity", view.quantity, None),
        (
            "Volume per component",
            _decimal_to_number(view.volume_per_component_l),
            qty_format(view.volume_per_component_l),
        ),
        (
            "Net volume",
            _decimal_to_number(view.net_volume_l),
            qty_format(view.net_volume_l),
        ),
        (
            "Weight per component",
            _decimal_to_number(view.weight_per_component_kg),
            qty_format(view.weight_per_component_kg),
        ),
        (
            "Total weight",
            _decimal_to_number(view.total_weight_kg),
            qty_format(view.total_weight_kg),
        ),
    ]
    for label, value, fmt in header_pairs:
        sheet.write(row, 0, label, bold)
        if isinstance(value, str):
            sheet.write(row, 1, value)
        elif fmt is None:
            sheet.write_number(row, 1, value)
        else:
            sheet.write_number(row, 1, value, fmt)
        row += 1
    row += 1

    sheet.write(row, 0, "Material", bold)
    sheet.write(row, 1, "Required", bold)
    row += 1
    for material in view.materials:
        sheet.write(row, 0, material.material_name)
        sheet.write_number(
            row,
            1,
            _decimal_to_number(material.weight_kg),
            qty_format(material.weight_kg),
        )
        row += 1
    sheet.write(row, 0, "Total", bold)
    sheet.write_number(
        row,
        1,
        _decimal_to_number(view.total_weight_kg),
        qty_format(view.total_weight_kg),
    )
