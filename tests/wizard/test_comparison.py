"""Strategy comparison runs the optimiser per strategy and detects ties."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from mixsheet.domain.project import Component, DirectVolume, Project, PurchaseConfig
from mixsheet.domain.strategy import Strategy
from mixsheet.wizard import comparison as comparison_module
from mixsheet.wizard.comparison import build_comparison_table

if TYPE_CHECKING:
    import pytest

    from mixsheet.domain import Catalog


def _project(catalog: Catalog) -> Project:
    preset = catalog.presets[0]
    return Project(
        schema_version=1,
        id="demo",
        name="Demo",
        shape="single",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        components=[
            Component(
                id="part",
                name="Part",
                quantity=1,
                volume=DirectVolume(volume_l=Decimal("3.46")),
                preset_id=preset.id,
                preset_version=preset.version,
            ),
        ],
        purchase=PurchaseConfig(excluded_materials=["water"]),
    )


def test_build_comparison_returns_one_row_per_strategy(catalog: Catalog) -> None:
    table = build_comparison_table(_project(catalog), catalog)
    assert [row.strategy for row in table.rows] == [
        Strategy.CHEAPEST,
        Strategy.BULK_VALUE,
        Strategy.MINIMAL_WASTE,
    ]


def test_build_comparison_invokes_optimizer_once_per_strategy(
    catalog: Catalog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Strategy] = []
    real = comparison_module.optimize_purchase

    def counting(*args: object, strategy: Strategy, **kwargs: object) -> object:
        calls.append(strategy)
        return real(*args, strategy=strategy, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(comparison_module, "optimize_purchase", counting)
    build_comparison_table(_project(catalog), catalog)
    assert calls == [Strategy.CHEAPEST, Strategy.BULK_VALUE, Strategy.MINIMAL_WASTE]


def test_build_comparison_marks_ties(catalog: Catalog) -> None:
    table = build_comparison_table(_project(catalog), catalog)
    by_strategy = {row.strategy: row for row in table.rows}
    cheapest = by_strategy[Strategy.CHEAPEST]
    minimal_waste = by_strategy[Strategy.MINIMAL_WASTE]
    if (
        cheapest.total_cost_incl_vat == minimal_waste.total_cost_incl_vat
        and cheapest.total_waste_kg == minimal_waste.total_waste_kg
    ):
        assert Strategy.MINIMAL_WASTE in cheapest.same_as
        assert Strategy.CHEAPEST in minimal_waste.same_as
    else:
        assert Strategy.MINIMAL_WASTE not in cheapest.same_as
