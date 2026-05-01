"""Project, Component and PurchaseConfig model unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from mixsheet.domain import (
    Component,
    DimensionsVolume,
    DirectVolume,
    Project,
    PurchaseConfig,
    Strategy,
)

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _component(
    *,
    cid: str = "c",
    quantity: int = 1,
    preset_id: str = "epoxy-mix",
    preset_version: str = "1.1.0",
    volume_l: str = "10.0",
) -> Component:
    return Component(
        id=cid,
        name=f"Component {cid}",
        quantity=quantity,
        volume=DirectVolume(volume_l=Decimal(volume_l)),
        preset_id=preset_id,
        preset_version=preset_version,
    )


class TestComponent:
    def test_computes_net_volume_across_quantity(self) -> None:
        component = Component(
            id="bed",
            name="Bed",
            quantity=3,
            volume=DirectVolume(volume_l=Decimal("12.5")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        assert component.net_volume_l == Decimal("37.5")

    def test_dimensions_volume_drives_net_volume(self) -> None:
        component = Component(
            id="bed",
            name="Bed",
            quantity=2,
            volume=DimensionsVolume(
                length_mm=Decimal("800"),
                width_mm=Decimal("400"),
                height_mm=Decimal("120"),
            ),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        assert component.net_volume_l == Decimal("76.8")

    def test_rejects_quantity_below_one(self) -> None:
        with pytest.raises(ValidationError):
            Component(
                id="bed",
                name="Bed",
                quantity=0,
                volume=DirectVolume(volume_l=Decimal("1")),
                preset_id="x",
                preset_version="1.0.0",
            )

    def test_rejects_a_missing_preset_version(self) -> None:
        with pytest.raises(ValidationError):
            Component.model_validate(
                {
                    "id": "bed",
                    "name": "Bed",
                    "quantity": 1,
                    "volume": {"mode": "direct", "volume_l": Decimal("1")},
                    "preset_id": "x",
                },
            )


class TestPurchaseConfig:
    def test_defaults_match_documented_values(self) -> None:
        config = PurchaseConfig()
        assert config.overage_pct == Decimal("0.10")
        assert config.strategy is Strategy.CHEAPEST
        assert config.excluded_materials == []

    def test_rejects_negative_overage(self) -> None:
        with pytest.raises(ValidationError):
            PurchaseConfig(overage_pct=Decimal("-0.05"))


class TestProject:
    def test_accepts_a_single_component_project(self) -> None:
        project = Project(
            id="p1",
            name="Project",
            shape="single",
            created_at=NOW,
            updated_at=NOW,
            components=[_component()],
        )
        assert project.shape == "single"

    def test_accepts_a_machine_project_with_two_components(self) -> None:
        project = Project(
            id="p1",
            name="Project",
            shape="machine",
            created_at=NOW,
            updated_at=NOW,
            components=[_component(cid="a"), _component(cid="b")],
        )
        assert len(project.components) == 2

    def test_rejects_a_single_shape_project_with_multiple_components(self) -> None:
        with pytest.raises(ValidationError, match="exactly one component"):
            Project(
                id="p1",
                name="Project",
                shape="single",
                created_at=NOW,
                updated_at=NOW,
                components=[_component(cid="a"), _component(cid="b")],
            )

    def test_rejects_an_unsupported_schema_version(self) -> None:
        with pytest.raises(ValidationError):
            Project.model_validate(
                {
                    "schema_version": 2,
                    "id": "p1",
                    "name": "Project",
                    "shape": "single",
                    "created_at": NOW,
                    "updated_at": NOW,
                    "components": [_component().model_dump()],
                    "purchase": {},
                },
            )

    def test_rejects_naive_datetimes(self) -> None:
        naive = datetime(2026, 5, 1, 12, 0)
        with pytest.raises(ValidationError, match="timezone-aware"):
            Project(
                id="p1",
                name="Project",
                shape="single",
                created_at=naive,
                updated_at=naive,
                components=[_component()],
            )
