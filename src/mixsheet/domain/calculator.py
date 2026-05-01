"""Pure single-component material breakdown.

Given a :class:`~mixsheet.domain.project.Component` and a
:class:`~mixsheet.domain.catalog.Catalog`, :func:`calculate_component`
returns a frozen :class:`ComponentBreakdown` with full-precision
``Decimal`` weights per material. The calculator never quantises;
display rounding belongs to the renderer layer.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from mixsheet.domain.catalog import Catalog
    from mixsheet.domain.project import Component


class UnknownPresetError(LookupError):
    """Raised when ``component.preset_id`` does not resolve in the catalog."""

    def __init__(self, preset_id: str) -> None:
        """Build the error from the offending preset id."""
        self.preset_id = preset_id
        super().__init__(f"unknown preset id {preset_id!r}")


class MaterialBreakdownRow(BaseModel):
    """One material in a :class:`ComponentBreakdown`, full-precision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)
    weight_kg: Decimal
    weight_per_component_kg: Decimal


class ComponentBreakdown(BaseModel):
    """Per-component material breakdown derived from a preset and a volume."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    component_id: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)
    preset_name: str = Field(min_length=1)
    density_kg_per_l: Decimal
    quantity: int = Field(ge=1)
    volume_per_component_l: Decimal
    net_volume_l: Decimal
    weight_per_component_kg: Decimal
    total_weight_kg: Decimal
    materials: list[MaterialBreakdownRow]


def calculate_component(component: Component, catalog: Catalog) -> ComponentBreakdown:
    """Compute the per-material breakdown for a single component.

    Resolves ``component.preset_id`` against the supplied catalog,
    raising :class:`UnknownPresetError` when the preset is missing.
    The catalog preset is authoritative even when
    ``component.preset_version`` differs from the catalog version;
    mismatch detection lives in
    :func:`~mixsheet.domain.project.load_project`.

    Material rows are sorted case-insensitively by ``material_name``
    for diff-friendly exports. All weights stay at full ``Decimal``
    precision; renderers round at display time.

    Raises:
        UnknownPresetError: if ``component.preset_id`` is not in the catalog.

    """
    preset = catalog.preset_by_id(component.preset_id)
    if preset is None:
        raise UnknownPresetError(component.preset_id)

    volume_per_component_l = component.volume.volume_l
    net_volume_l = volume_per_component_l * Decimal(component.quantity)
    weight_per_component_kg = volume_per_component_l * preset.density_kg_per_l
    total_weight_kg = net_volume_l * preset.density_kg_per_l

    rows: list[MaterialBreakdownRow] = []
    for proportion_row in preset.materials:
        material = catalog.material_by_id(proportion_row.material_id)
        if material is None:  # pragma: no cover - catalog loader guarantees resolution
            msg = f"preset {preset.id!r} references unknown material {proportion_row.material_id!r}"
            raise LookupError(msg)
        rows.append(
            MaterialBreakdownRow(
                material_id=material.id,
                material_name=material.name,
                weight_kg=total_weight_kg * proportion_row.proportion,
                weight_per_component_kg=weight_per_component_kg * proportion_row.proportion,
            ),
        )
    rows.sort(key=lambda row: row.material_name.casefold())

    return ComponentBreakdown(
        component_id=component.id,
        preset_id=preset.id,
        preset_name=preset.name,
        density_kg_per_l=preset.density_kg_per_l,
        quantity=component.quantity,
        volume_per_component_l=volume_per_component_l,
        net_volume_l=net_volume_l,
        weight_per_component_kg=weight_per_component_kg,
        total_weight_kg=total_weight_kg,
        materials=rows,
    )
