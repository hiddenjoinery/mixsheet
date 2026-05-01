"""Pure project aggregation across components.

Given a :class:`~mixsheet.domain.project.Project` and a
:class:`~mixsheet.domain.catalog.Catalog`, :func:`aggregate_project`
returns a frozen :class:`ProjectBreakdown` carrying per-component
breakdowns plus per-material totals with source attribution. The
aggregator never quantises and never applies ``purchase.overage_pct``
or ``purchase.excluded_materials`` — those concerns belong to the
purchase optimizer.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from mixsheet.domain.calculator import ComponentBreakdown, calculate_component

if TYPE_CHECKING:
    from mixsheet.domain.catalog import Catalog
    from mixsheet.domain.project import Project


class AggregatedMaterialSource(BaseModel):
    """One component's contribution to an :class:`AggregatedMaterial`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    component_id: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)
    weight_kg: Decimal


class AggregatedMaterial(BaseModel):
    """A material summed across every contributing component."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)
    total_weight_kg: Decimal
    sources: list[AggregatedMaterialSource] = Field(min_length=1)


class ProjectBreakdown(BaseModel):
    """A project's aggregated mix-sheet view: totals, components, materials."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    shape: Literal["single", "machine"]
    components: list[ComponentBreakdown] = Field(min_length=1)
    total_net_volume_l: Decimal
    total_weight_kg: Decimal
    materials: list[AggregatedMaterial]


def aggregate_project(project: Project, catalog: Catalog) -> ProjectBreakdown:
    """Aggregate a project into a frozen :class:`ProjectBreakdown`.

    Calls :func:`~mixsheet.domain.calculator.calculate_component` once
    per component (in ``project.components`` order) and sums the
    resulting per-material weights. ``purchase.overage_pct`` and
    ``purchase.excluded_materials`` are intentionally ignored — the
    aggregator's contract is the mix-sheet view.

    Raises:
        UnknownPresetError: propagated from the calculator when a
            component references a preset missing from the catalog.

    """
    component_breakdowns: list[ComponentBreakdown] = [
        calculate_component(component, catalog) for component in project.components
    ]

    sources_by_material: dict[str, list[AggregatedMaterialSource]] = {}
    name_by_material: dict[str, str] = {}
    for component_breakdown in component_breakdowns:
        for row in component_breakdown.materials:
            sources_by_material.setdefault(row.material_id, []).append(
                AggregatedMaterialSource(
                    component_id=component_breakdown.component_id,
                    preset_id=component_breakdown.preset_id,
                    weight_kg=row.weight_kg,
                ),
            )
            name_by_material.setdefault(row.material_id, row.material_name)

    materials = [
        AggregatedMaterial(
            material_id=material_id,
            material_name=name_by_material[material_id],
            total_weight_kg=sum(
                (source.weight_kg for source in sources),
                start=Decimal("0"),
            ),
            sources=sources,
        )
        for material_id, sources in sources_by_material.items()
    ]
    materials.sort(key=lambda material: material.material_name.casefold())

    total_net_volume_l = sum(
        (breakdown.net_volume_l for breakdown in component_breakdowns),
        start=Decimal("0"),
    )
    total_weight_kg = sum(
        (breakdown.total_weight_kg for breakdown in component_breakdowns),
        start=Decimal("0"),
    )

    return ProjectBreakdown(
        project_id=project.id,
        project_name=project.name,
        shape=project.shape,
        components=component_breakdowns,
        total_net_volume_l=total_net_volume_l,
        total_weight_kg=total_weight_kg,
        materials=materials,
    )
