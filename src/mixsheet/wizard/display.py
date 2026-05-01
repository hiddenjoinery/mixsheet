"""Rich rendering helpers used by both ``mixsheet new`` and ``mixsheet open``.

These helpers print the post-input recap blocks (volume summary, mix
sheet preview, strategy comparison, purchase list preview). They never
mutate inputs and return ``None``; the wizard files call them between
domain calls.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from rich.table import Table

from mixsheet.domain.display import (
    PRICE_DECIMALS,
    QUANTITY_DECIMALS_HIGH,
    QUANTITY_DECIMALS_LOW,
    QUANTITY_THRESHOLD,
)

if TYPE_CHECKING:
    from rich.console import Console

    from mixsheet.domain.calculator import ComponentBreakdown
    from mixsheet.domain.mixsheet_renderer import ComponentMixSheetView
    from mixsheet.domain.project import Volume
    from mixsheet.domain.renderer import PurchaseListView
    from mixsheet.wizard.comparison import StrategyComparison


def _format_quantity(value: Decimal) -> str:
    decimals = QUANTITY_DECIMALS_LOW if abs(value) <= QUANTITY_THRESHOLD else QUANTITY_DECIMALS_HIGH
    quant = Decimal(10) ** -decimals
    rounded = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"{rounded:.{decimals}f}"


def _format_price(value: Decimal) -> str:
    quant = Decimal(10) ** -PRICE_DECIMALS
    rounded = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"€ {rounded:.{PRICE_DECIMALS}f}"


def show_volume_summary(console: Console, volume: Volume, quantity: int) -> None:
    """Print the per-component / quantity / net volume recap."""
    per = volume.volume_l
    net = per * Decimal(quantity)
    console.print(f"  Volume per component: {_format_quantity(per)} L")
    console.print(f"  Quantity:             {quantity}")
    console.print(f"  Net volume:           {_format_quantity(net)} L")


def show_mix_sheet(console: Console, view: ComponentMixSheetView) -> None:
    """Print the per-component mix sheet table."""
    console.print(
        f"  {view.component_name} — {view.preset_name} — {view.quantity} piece(s)"
        f" — {view.volume_per_component_l_display} L → {view.total_weight_kg_display} kg",
    )
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Material")
    table.add_column("Required", justify="right")
    for row in view.materials:
        table.add_row(row.material_name, f"{row.weight_kg_display} kg")
    table.add_row("Total", f"{view.total_weight_kg_display} kg", style="bold")
    console.print(table)


def show_strategy_comparison(console: Console, comparison: StrategyComparison) -> None:
    """Print the strategy comparison table with tie markers."""
    table = Table(show_header=True, header_style="bold", title="Strategy comparison")
    table.add_column("Strategy")
    table.add_column("Total cost", justify="right")
    table.add_column("Total waste", justify="right")
    table.add_column("Lines", justify="right")
    table.add_column("Note")
    for row in comparison.rows:
        same = "same as " + ", ".join(other.value for other in row.same_as) if row.same_as else ""
        table.add_row(
            row.strategy.value,
            _format_price(row.total_cost_incl_vat),
            f"{_format_quantity(row.total_waste_kg)} kg",
            str(row.line_count),
            same,
        )
    console.print(table)


def show_aggregated_breakdown(
    console: Console,
    component_breakdowns: list[ComponentBreakdown],
) -> None:
    """Print the per-component aggregate table for machine projects."""
    if len(component_breakdowns) <= 1:
        return
    table = Table(show_header=True, header_style="bold", title="Aggregated totals")
    table.add_column("Component")
    table.add_column("Preset")
    table.add_column("Volume", justify="right")
    table.add_column("Required kg", justify="right")
    total_volume = Decimal("0")
    total_weight = Decimal("0")
    for breakdown in component_breakdowns:
        table.add_row(
            breakdown.component_id,
            breakdown.preset_name,
            f"{_format_quantity(breakdown.net_volume_l)} L",
            f"{_format_quantity(breakdown.total_weight_kg)} kg",
        )
        total_volume += breakdown.net_volume_l
        total_weight += breakdown.total_weight_kg
    table.add_row(
        "Total",
        "",
        f"{_format_quantity(total_volume)} L",
        f"{_format_quantity(total_weight)} kg",
        style="bold",
    )
    console.print(table)


def show_purchase_list(console: Console, view: PurchaseListView) -> None:
    """Print the rolled-up purchase list table."""
    table = Table(show_header=True, header_style="bold", title="Purchase list")
    table.add_column("Material")
    table.add_column("Required", justify="right")
    table.add_column("Purchased", justify="right")
    table.add_column("Waste", justify="right")
    table.add_column("Suppliers")
    table.add_column("Cost", justify="right")
    for material in view.materials:
        table.add_row(
            material.material_name,
            f"{material.required_kg_display} kg",
            f"{material.purchased_kg_display} kg",
            f"{material.waste_kg_display} kg",
            material.suppliers,
            material.cost_incl_vat_display,
        )
    table.add_row(
        "Total",
        "",
        "",
        f"{view.total_waste_kg_display} kg",
        "",
        view.total_cost_incl_vat_display,
        style="bold",
    )
    console.print(table)
