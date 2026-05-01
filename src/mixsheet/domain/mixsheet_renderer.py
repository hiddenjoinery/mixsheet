"""Pure rendering of a :class:`ComponentBreakdown` into a mix-sheet view.

Given a frozen :class:`~mixsheet.domain.calculator.ComponentBreakdown`,
:func:`render_component_mixsheet` returns a frozen
:class:`ComponentMixSheetView` carrying the same component context
decorated with display-rounded string fields. Quantities follow the
threshold rule from :mod:`mixsheet.domain.display`; density renders to
two decimals so workbench headers stay legible.

Like :mod:`mixsheet.domain.renderer`, this module never mutates inputs,
performs no I/O, and is deterministic across repeated calls.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from mixsheet.domain.display import (
    QUANTITY_DECIMALS_HIGH,
    QUANTITY_DECIMALS_LOW,
    QUANTITY_THRESHOLD,
)

if TYPE_CHECKING:
    from mixsheet.domain.calculator import ComponentBreakdown

DENSITY_DECIMALS: int = 2


class MixSheetMaterialRow(BaseModel):
    """One material row in a :class:`ComponentMixSheetView`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)
    weight_per_component_kg: Decimal
    weight_per_component_kg_display: str
    weight_kg: Decimal
    weight_kg_display: str


class ComponentMixSheetView(BaseModel):
    """A component breakdown reshaped for mix-sheet display."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    component_id: str = Field(min_length=1)
    component_name: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)
    preset_name: str = Field(min_length=1)
    density_kg_per_l: Decimal
    density_kg_per_l_display: str
    quantity: int = Field(ge=1)
    volume_per_component_l: Decimal
    volume_per_component_l_display: str
    net_volume_l: Decimal
    net_volume_l_display: str
    weight_per_component_kg: Decimal
    weight_per_component_kg_display: str
    total_weight_kg: Decimal
    total_weight_kg_display: str
    materials: list[MixSheetMaterialRow]


def _format_quantity(value: Decimal) -> str:
    """Format a quantity using the per-cell threshold rule and half-up rounding."""
    decimals = QUANTITY_DECIMALS_LOW if abs(value) <= QUANTITY_THRESHOLD else QUANTITY_DECIMALS_HIGH
    quant = Decimal(10) ** -decimals
    rounded = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"{rounded:.{decimals}f}"


def _format_density(value: Decimal) -> str:
    """Format a density value to ``DENSITY_DECIMALS`` half-up."""
    quant = Decimal(10) ** -DENSITY_DECIMALS
    rounded = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"{rounded:.{DENSITY_DECIMALS}f}"


def render_component_mixsheet(
    component_breakdown: ComponentBreakdown,
    *,
    component_name: str,
) -> ComponentMixSheetView:
    """Reshape a :class:`ComponentBreakdown` into a frozen mix-sheet view.

    Echoes every numeric field at full ``Decimal`` precision and adds
    display-rounded string companions per cell. Material rows preserve
    the input order. The ``component_name`` argument carries the
    human-readable label that ``ComponentBreakdown`` does not store.
    """
    materials = [
        MixSheetMaterialRow(
            material_id=row.material_id,
            material_name=row.material_name,
            weight_per_component_kg=row.weight_per_component_kg,
            weight_per_component_kg_display=_format_quantity(row.weight_per_component_kg),
            weight_kg=row.weight_kg,
            weight_kg_display=_format_quantity(row.weight_kg),
        )
        for row in component_breakdown.materials
    ]
    return ComponentMixSheetView(
        component_id=component_breakdown.component_id,
        component_name=component_name,
        preset_id=component_breakdown.preset_id,
        preset_name=component_breakdown.preset_name,
        density_kg_per_l=component_breakdown.density_kg_per_l,
        density_kg_per_l_display=_format_density(component_breakdown.density_kg_per_l),
        quantity=component_breakdown.quantity,
        volume_per_component_l=component_breakdown.volume_per_component_l,
        volume_per_component_l_display=_format_quantity(
            component_breakdown.volume_per_component_l,
        ),
        net_volume_l=component_breakdown.net_volume_l,
        net_volume_l_display=_format_quantity(component_breakdown.net_volume_l),
        weight_per_component_kg=component_breakdown.weight_per_component_kg,
        weight_per_component_kg_display=_format_quantity(
            component_breakdown.weight_per_component_kg,
        ),
        total_weight_kg=component_breakdown.total_weight_kg,
        total_weight_kg_display=_format_quantity(component_breakdown.total_weight_kg),
        materials=materials,
    )
