"""Tests for the pure component mix-sheet renderer."""

from __future__ import annotations

from decimal import Decimal

import pytest

from mixsheet.domain import (
    ComponentBreakdown,
    ComponentMixSheetView,
    MaterialBreakdownRow,
    render_component_mixsheet,
)


def _row(
    *, material_id: str, material_name: str, weight_per_component_kg: str, weight_kg: str
) -> MaterialBreakdownRow:
    return MaterialBreakdownRow(
        material_id=material_id,
        material_name=material_name,
        weight_per_component_kg=Decimal(weight_per_component_kg),
        weight_kg=Decimal(weight_kg),
    )


def _breakdown(  # noqa: PLR0913
    *,
    component_id: str = "bed",
    preset_id: str = "epoxy-mix",
    preset_name: str = "Epoxy granite",
    density_kg_per_l: str = "1.91",
    quantity: int = 1,
    volume_per_component_l: str = "3.46",
    net_volume_l: str = "3.46",
    weight_per_component_kg: str = "6.30",
    total_weight_kg: str = "6.30",
    materials: list[MaterialBreakdownRow] | None = None,
) -> ComponentBreakdown:
    return ComponentBreakdown(
        component_id=component_id,
        preset_id=preset_id,
        preset_name=preset_name,
        density_kg_per_l=Decimal(density_kg_per_l),
        quantity=quantity,
        volume_per_component_l=Decimal(volume_per_component_l),
        net_volume_l=Decimal(net_volume_l),
        weight_per_component_kg=Decimal(weight_per_component_kg),
        total_weight_kg=Decimal(total_weight_kg),
        materials=materials
        or [
            _row(
                material_id="cement",
                material_name="Cement",
                weight_per_component_kg="1.00",
                weight_kg="1.00",
            ),
        ],
    )


class TestFrozenSingleComponent:
    def test_returns_frozen_view_with_populated_header_and_materials(self) -> None:
        breakdown = _breakdown(
            materials=[
                _row(
                    material_id="cement",
                    material_name="Cement",
                    weight_per_component_kg="0.62",
                    weight_kg="0.62",
                ),
            ],
        )

        view = render_component_mixsheet(breakdown, component_name="Riser")

        assert isinstance(view, ComponentMixSheetView)
        assert view.model_config.get("frozen") is True
        with pytest.raises(ValueError, match="frozen"):
            view.component_id = "x"  # type: ignore[misc]
        assert view.component_id == "bed"
        assert view.component_name == "Riser"
        assert view.preset_id == "epoxy-mix"
        assert view.preset_name == "Epoxy granite"
        assert len(view.materials) == 1
        assert view.materials[0].material_id == "cement"


class TestMaterialOrderAndPerRowValues:
    def test_preserves_material_order_and_carries_raw_and_display(self) -> None:
        breakdown = _breakdown(
            materials=[
                _row(
                    material_id="aggregate",
                    material_name="Aggregate",
                    weight_per_component_kg="2.5",
                    weight_kg="2.5",
                ),
                _row(
                    material_id="cement",
                    material_name="Cement",
                    weight_per_component_kg="1.00",
                    weight_kg="1.00",
                ),
                _row(
                    material_id="epoxy",
                    material_name="Epoxy",
                    weight_per_component_kg="12.345678",
                    weight_kg="12.345678",
                ),
            ],
        )

        view = render_component_mixsheet(breakdown, component_name="Riser")

        assert [row.material_id for row in view.materials] == [
            "aggregate",
            "cement",
            "epoxy",
        ]
        epoxy = view.materials[2]
        assert epoxy.weight_kg == Decimal("12.345678")
        assert epoxy.weight_kg_display == "12"


class TestQuantityThreshold:
    def test_volume_at_threshold_uses_one_decimal(self) -> None:
        breakdown = _breakdown(
            volume_per_component_l="9.6",
            net_volume_l="9.6",
            weight_per_component_kg="124",
            total_weight_kg="124",
        )

        view = render_component_mixsheet(breakdown, component_name="Riser")

        assert view.volume_per_component_l_display == "9.6"
        assert view.total_weight_kg_display == "124"


class TestDensityFormat:
    def test_density_191_renders_to_two_decimals(self) -> None:
        breakdown = _breakdown(density_kg_per_l="1.91")

        view = render_component_mixsheet(breakdown, component_name="Riser")

        assert view.density_kg_per_l == Decimal("1.91")
        assert view.density_kg_per_l_display == "1.91"

    def test_density_2_pads_to_two_decimals(self) -> None:
        breakdown = _breakdown(density_kg_per_l="2")

        view = render_component_mixsheet(breakdown, component_name="Riser")

        assert view.density_kg_per_l_display == "2.00"


class TestTotalWeightEcho:
    def test_total_weight_carried_through_at_full_precision(self) -> None:
        breakdown = _breakdown(total_weight_kg="6.300000", weight_per_component_kg="6.300000")

        view = render_component_mixsheet(breakdown, component_name="Riser")

        assert view.total_weight_kg == Decimal("6.300000")
        assert view.total_weight_kg_display == "6.3"


class TestReproducibilityAndNonMutation:
    def test_two_calls_with_equal_input_return_equal_views(self) -> None:
        breakdown = _breakdown()

        view_a = render_component_mixsheet(breakdown, component_name="Riser")
        view_b = render_component_mixsheet(breakdown, component_name="Riser")

        assert view_a == view_b

    def test_input_breakdown_is_not_mutated(self) -> None:
        breakdown = _breakdown()
        snapshot = breakdown.model_dump()

        render_component_mixsheet(breakdown, component_name="Riser")

        assert breakdown.model_dump() == snapshot
