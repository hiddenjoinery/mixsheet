"""Tests for the pure purchase optimiser."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from mixsheet.domain import (
    BundleDiscount,
    Catalog,
    DirectVolume,
    Material,
    MaterialProportion,
    MixPreset,
    PurchaseConfig,
    Strategy,
    Supplier,
    SupplierPackage,
    UnpurchasableMaterialError,
    aggregate_project,
    optimize_purchase,
)
from mixsheet.domain.aggregator import (
    AggregatedMaterial,
    AggregatedMaterialSource,
    ProjectBreakdown,
)
from mixsheet.domain.calculator import (
    ComponentBreakdown,
    MaterialBreakdownRow,
)
from mixsheet.domain.optimizer import CatalogTooBroadError
from mixsheet.domain.project import Component, Project

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _material(material_id: str, name: str | None = None) -> Material:
    return Material(id=material_id, name=name or material_id.title(), category="binder")


def _supplier(supplier_id: str, name: str | None = None) -> Supplier:
    return Supplier(id=supplier_id, name=name or supplier_id.title())


def _package(  # noqa: PLR0913
    *,
    pid: str,
    material_id: str,
    supplier_id: str,
    weight_kg: str,
    price_incl_vat: str,
    bundle_discounts: list[BundleDiscount] | None = None,
) -> SupplierPackage:
    return SupplierPackage(
        id=pid,
        material_id=material_id,
        supplier_id=supplier_id,
        weight_kg=Decimal(weight_kg),
        price_incl_vat=Decimal(price_incl_vat),
        bundle_discounts=bundle_discounts or [],
    )


def _tier(min_quantity: int, discount_pct: str) -> BundleDiscount:
    return BundleDiscount(min_quantity=min_quantity, discount_pct=Decimal(discount_pct))


def _catalog(
    *,
    materials: list[Material],
    presets: list[MixPreset] | None = None,
    suppliers: list[Supplier] | None = None,
    packages: list[SupplierPackage] | None = None,
) -> Catalog:
    return Catalog(
        catalog_version="2026-05-01",
        materials=materials,
        presets=presets or [],
        suppliers=suppliers or [],
        packages=packages or [],
    )


def _row(material_id: str, name: str, weight_kg: str) -> MaterialBreakdownRow:
    return MaterialBreakdownRow(
        material_id=material_id,
        material_name=name,
        weight_kg=Decimal(weight_kg),
        weight_per_component_kg=Decimal(weight_kg),
    )


def _component_breakdown(
    *,
    component_id: str = "c1",
    preset_id: str = "p1",
    rows: list[MaterialBreakdownRow],
) -> ComponentBreakdown:
    total = sum((row.weight_kg for row in rows), start=Decimal("0"))
    return ComponentBreakdown(
        component_id=component_id,
        preset_id=preset_id,
        preset_name="P1",
        density_kg_per_l=Decimal("1.0"),
        quantity=1,
        volume_per_component_l=total,
        net_volume_l=total,
        weight_per_component_kg=total,
        total_weight_kg=total,
        materials=rows,
    )


def _aggregated(
    *,
    material_id: str,
    name: str,
    weight_kg: str,
    component_id: str = "c1",
    preset_id: str = "p1",
) -> AggregatedMaterial:
    return AggregatedMaterial(
        material_id=material_id,
        material_name=name,
        total_weight_kg=Decimal(weight_kg),
        sources=[
            AggregatedMaterialSource(
                component_id=component_id,
                preset_id=preset_id,
                weight_kg=Decimal(weight_kg),
            ),
        ],
    )


def _breakdown(
    *,
    materials: list[AggregatedMaterial],
    component_id: str = "c1",
    preset_id: str = "p1",
) -> ProjectBreakdown:
    rows = [_row(m.material_id, m.material_name, str(m.total_weight_kg)) for m in materials]
    component = _component_breakdown(
        component_id=component_id,
        preset_id=preset_id,
        rows=rows,
    )
    total_weight = sum((m.total_weight_kg for m in materials), start=Decimal("0"))
    return ProjectBreakdown(
        project_id="test-project",
        project_name="Test project",
        shape="single",
        components=[component],
        total_net_volume_l=total_weight,
        total_weight_kg=total_weight,
        materials=materials,
    )


class TestPurchaseListContract:
    def test_returns_frozen_purchase_list_for_single_material(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="10")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="acme-cement-25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30.00",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        assert result.model_config.get("frozen") is True
        with pytest.raises(ValueError, match="frozen"):
            result.line_items[0].allocations[0].package_id = "x"  # type: ignore[misc]

        assert len(result.line_items) == 1
        line_item = result.line_items[0]
        assert line_item.allocations[0].package_id == "acme-cement-25"
        assert line_item.allocations[0].count == 1
        assert line_item.purchased_kg == Decimal("25")
        assert line_item.cost_incl_vat == Decimal("30.00")
        assert result.total_cost_incl_vat == Decimal("30.00")

    def test_does_not_mutate_inputs_and_is_reproducible(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="12")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="acme-cement-25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30.00",
                ),
                _package(
                    pid="acme-cement-5",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="5",
                    price_incl_vat="8.00",
                ),
            ],
        )
        breakdown_snapshot = breakdown.model_dump()
        catalog_snapshot = catalog.model_dump()

        result_a = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )
        result_b = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        assert breakdown.model_dump() == breakdown_snapshot
        assert catalog.model_dump() == catalog_snapshot
        assert result_a == result_b


class TestOverageApplication:
    def test_zero_overage_covers_exact_net_weight(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="10")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert line_item.required_with_overage_kg == Decimal("10")
        assert line_item.purchased_kg >= Decimal("10")

    def test_ten_percent_overage_inflates_required_weight(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="10")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0.10"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert line_item.required_with_overage_kg == Decimal("11.0")
        assert line_item.purchased_kg >= Decimal("11.0")

    def test_six_decimal_required_weight_keeps_full_precision(self) -> None:
        breakdown = _breakdown(
            materials=[
                _aggregated(material_id="cement", name="Cement", weight_kg="12.345678"),
            ],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p15",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="15",
                    price_incl_vat="20",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert line_item.required_kg == Decimal("12.345678")
        assert line_item.required_with_overage_kg == Decimal("12.345678")
        assert line_item.purchased_kg == Decimal("15")


class TestMultiPackageAllocation:
    def test_minimal_waste_combines_25_and_5_kg(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="28")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
                _package(
                    pid="p05",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="5",
                    price_incl_vat="8",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.MINIMAL_WASTE,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert {alloc.package_id: alloc.count for alloc in line_item.allocations} == {
            "p05": 1,
            "p25": 1,
        }
        assert line_item.purchased_kg == Decimal("30")
        assert line_item.waste_kg == Decimal("2")

    def test_single_allocation_when_one_package_optimal(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="20")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="25",
                ),
                _package(
                    pid="p05",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="5",
                    price_incl_vat="7",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert len(line_item.allocations) == 1
        assert line_item.allocations[0].package_id == "p25"
        assert line_item.allocations[0].count == 1


class TestCrossSupplierMixing:
    def test_allocations_span_two_suppliers(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="28")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("a"), _supplier("b")],
            packages=[
                _package(
                    pid="a-25",
                    material_id="cement",
                    supplier_id="a",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
                _package(
                    pid="b-05",
                    material_id="cement",
                    supplier_id="b",
                    weight_kg="5",
                    price_incl_vat="6",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        suppliers_used = {alloc.supplier_id for alloc in line_item.allocations}
        assert suppliers_used == {"a", "b"}
        assert line_item.purchased_kg == Decimal("30")
        assert line_item.cost_incl_vat == Decimal("36")


class TestExclusions:
    def test_excluded_material_with_packages_is_dropped(self) -> None:
        breakdown = _breakdown(
            materials=[
                _aggregated(material_id="cement", name="Cement", weight_kg="10"),
                _aggregated(material_id="water", name="Water", weight_kg="2"),
            ],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement"), _material("water", "Water")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
                _package(
                    pid="w-5",
                    material_id="water",
                    supplier_id="acme",
                    weight_kg="5",
                    price_incl_vat="2",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=["water"],
        )

        ids = [line_item.material_id for line_item in result.line_items]
        assert ids == ["cement"]
        assert result.total_cost_incl_vat == Decimal("30")

    def test_excluded_material_without_packages_does_not_raise(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="water", name="Water", weight_kg="2")],
        )
        catalog = _catalog(
            materials=[_material("water", "Water")],
            suppliers=[],
            packages=[],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=["water"],
        )

        assert result.line_items == []
        assert result.total_cost_incl_vat == Decimal("0")

    def test_non_excluded_material_without_packages_raises(self) -> None:
        breakdown = _breakdown(
            materials=[
                _aggregated(material_id="phantom-fines", name="Phantom", weight_kg="5"),
            ],
        )
        catalog = _catalog(
            materials=[_material("phantom-fines", "Phantom")],
            suppliers=[],
            packages=[],
        )

        with pytest.raises(UnpurchasableMaterialError, match="phantom-fines"):
            optimize_purchase(
                breakdown,
                catalog,
                strategy=Strategy.CHEAPEST,
                overage_pct=Decimal("0"),
                excluded_materials=[],
            )


class TestStrategies:
    def _two_size_catalog(
        self,
        *,
        big_price: str = "30",
        small_price: str = "13",
    ) -> Catalog:
        return _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p10",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="10",
                    price_incl_vat=small_price,
                ),
                _package(
                    pid="p25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat=big_price,
                ),
            ],
        )

    def test_cheapest_picks_lower_total_cost(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="20")],
        )
        catalog = self._two_size_catalog()

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert {alloc.package_id: alloc.count for alloc in line_item.allocations} == {"p10": 2}
        assert line_item.cost_incl_vat == Decimal("26")

    def test_minimal_waste_picks_lowest_overshoot_at_higher_cost(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="28")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
                _package(
                    pid="p05",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="5",
                    price_incl_vat="8",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.MINIMAL_WASTE,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert line_item.purchased_kg == Decimal("30")
        assert line_item.cost_incl_vat == Decimal("38")
        assert line_item.waste_kg == Decimal("2")

    def test_bulk_value_prefers_lower_price_per_kg(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="20")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="25",
                ),
                _package(
                    pid="p05",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="5",
                    price_incl_vat="7",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.BULK_VALUE,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert {alloc.package_id: alloc.count for alloc in line_item.allocations} == {"p25": 1}


class TestTieBreaking:
    def test_identical_objectives_resolve_by_sorted_package_id_tuple(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="10")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("a"), _supplier("b")],
            packages=[
                _package(
                    pid="alpha",
                    material_id="cement",
                    supplier_id="a",
                    weight_kg="10",
                    price_incl_vat="15",
                ),
                _package(
                    pid="beta",
                    material_id="cement",
                    supplier_id="b",
                    weight_kg="10",
                    price_incl_vat="15",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert [alloc.package_id for alloc in line_item.allocations] == ["alpha"]


class TestSupplierSubtotalsAndTotals:
    def test_cross_supplier_line_item_yields_two_subtotals(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="28")],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("a"), _supplier("b")],
            packages=[
                _package(
                    pid="a-25",
                    material_id="cement",
                    supplier_id="a",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
                _package(
                    pid="b-05",
                    material_id="cement",
                    supplier_id="b",
                    weight_kg="5",
                    price_incl_vat="6",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        subtotals = {sub.supplier_id: sub for sub in result.suppliers}
        assert subtotals["a"].subtotal_incl_vat == Decimal("30")
        assert subtotals["a"].item_count == 1
        assert subtotals["b"].subtotal_incl_vat == Decimal("6")
        assert subtotals["b"].item_count == 1

    def test_grand_totals_equal_sum_of_line_items(self) -> None:
        breakdown = _breakdown(
            materials=[
                _aggregated(material_id="cement", name="Cement", weight_kg="10"),
                _aggregated(material_id="sand", name="Sand", weight_kg="20"),
            ],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement"), _material("sand", "Sand")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="cement-25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
                _package(
                    pid="sand-25",
                    material_id="sand",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="20",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        assert result.total_cost_incl_vat == sum(
            (line_item.cost_incl_vat for line_item in result.line_items),
            start=Decimal("0"),
        )
        assert result.total_waste_kg == sum(
            (line_item.waste_kg for line_item in result.line_items),
            start=Decimal("0"),
        )
        assert len(result.suppliers) == 1
        assert result.suppliers[0].subtotal_incl_vat == Decimal("50")
        assert result.suppliers[0].item_count == 2


class TestLineItemOrdering:
    def test_order_matches_breakdown_materials(self) -> None:
        breakdown = _breakdown(
            materials=[
                _aggregated(material_id="aggregate", name="Aggregate fines", weight_kg="5"),
                _aggregated(material_id="cement", name="Cement", weight_kg="10"),
                _aggregated(material_id="quartz", name="Quartz sand", weight_kg="8"),
            ],
        )
        catalog = _catalog(
            materials=[
                _material("aggregate", "Aggregate fines"),
                _material("cement", "Cement"),
                _material("quartz", "Quartz sand"),
            ],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="agg-25",
                    material_id="aggregate",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="20",
                ),
                _package(
                    pid="cement-25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
                _package(
                    pid="quartz-25",
                    material_id="quartz",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="15",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        assert [line_item.material_id for line_item in result.line_items] == [
            "aggregate",
            "cement",
            "quartz",
        ]


class TestFullPrecisionBoundary:
    def test_required_and_purchased_kg_not_quantised(self) -> None:
        breakdown = _breakdown(
            materials=[
                _aggregated(
                    material_id="cement",
                    name="Cement",
                    weight_kg="12.345678",
                ),
            ],
        )
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="p15",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="15",
                    price_incl_vat="20",
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert line_item.required_kg == Decimal("12.345678")
        assert line_item.required_with_overage_kg == Decimal("12.345678")
        assert line_item.purchased_kg == Decimal("15")


class TestCatalogTooBroad:
    def test_more_than_thirty_two_packages_raises(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="cement", name="Cement", weight_kg="10")],
        )
        packages = [
            _package(
                pid=f"p-{idx:02d}",
                material_id="cement",
                supplier_id="acme",
                weight_kg=str(idx + 1),
                price_incl_vat=str(idx + 1),
            )
            for idx in range(33)
        ]
        catalog = _catalog(
            materials=[_material("cement", "Cement")],
            suppliers=[_supplier("acme")],
            packages=packages,
        )

        with pytest.raises(CatalogTooBroadError, match="cement"):
            optimize_purchase(
                breakdown,
                catalog,
                strategy=Strategy.CHEAPEST,
                overage_pct=Decimal("0"),
                excluded_materials=[],
            )


class TestAggregatorIntegration:
    def test_runs_against_real_aggregator_output(self) -> None:
        materials = [
            _material("cement", "Cement"),
            _material("sand", "Sand"),
        ]
        preset = MixPreset(
            id="simple",
            name="Simple",
            version="1.0.0",
            density_kg_per_l=Decimal("1.0"),
            materials=[
                MaterialProportion(material_id="cement", proportion=Decimal("0.4")),
                MaterialProportion(material_id="sand", proportion=Decimal("0.6")),
            ],
        )
        catalog = _catalog(
            materials=materials,
            presets=[preset],
            suppliers=[_supplier("acme")],
            packages=[
                _package(
                    pid="cement-25",
                    material_id="cement",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="30",
                ),
                _package(
                    pid="sand-25",
                    material_id="sand",
                    supplier_id="acme",
                    weight_kg="25",
                    price_incl_vat="20",
                ),
            ],
        )
        component = Component(
            id="bed",
            name="Bed",
            quantity=1,
            volume=DirectVolume(volume_l=Decimal("50")),
            preset_id="simple",
            preset_version="1.0.0",
        )
        project = Project(
            id="bed",
            name="Bed",
            shape="single",
            created_at=NOW,
            updated_at=NOW,
            components=[component],
            purchase=PurchaseConfig(),
        )
        breakdown = aggregate_project(project, catalog)

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0.10"),
            excluded_materials=[],
        )

        cement = next(li for li in result.line_items if li.material_id == "cement")
        sand = next(li for li in result.line_items if li.material_id == "sand")
        assert cement.required_kg == Decimal("20.0")
        assert cement.required_with_overage_kg == Decimal("22.00")
        assert sand.required_kg == Decimal("30.0")
        assert sand.required_with_overage_kg == Decimal("33.00")


class TestBundleDiscountPricing:
    def test_single_unit_ignores_all_tiers(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="resin", name="Resin", weight_kg="20")],
        )
        catalog = _catalog(
            materials=[_material("resin", "Resin")],
            suppliers=[_supplier("rg")],
            packages=[
                _package(
                    pid="resin-25",
                    material_id="resin",
                    supplier_id="rg",
                    weight_kg="25",
                    price_incl_vat="340.98",
                    bundle_discounts=[_tier(2, "0.05")],
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert line_item.allocations[0].count == 1
        assert line_item.cost_incl_vat == Decimal("340.98")
        assert result.suppliers[0].subtotal_incl_vat == Decimal("340.98")
        assert result.total_cost_incl_vat == Decimal("340.98")

    def test_threshold_quantity_applies_lowest_tier(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="resin", name="Resin", weight_kg="40")],
        )
        catalog = _catalog(
            materials=[_material("resin", "Resin")],
            suppliers=[_supplier("rg")],
            packages=[
                _package(
                    pid="resin-25",
                    material_id="resin",
                    supplier_id="rg",
                    weight_kg="25",
                    price_incl_vat="100.00",
                    bundle_discounts=[_tier(2, "0.05")],
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert line_item.allocations[0].count == 2
        # 100.00 → 9500 cents discounted unit * 2 = €190.00.
        assert line_item.cost_incl_vat == Decimal("190.00")
        assert result.total_cost_incl_vat == Decimal("190.00")

    def test_highest_qualifying_tier_wins(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="resin", name="Resin", weight_kg="100")],
        )
        catalog = _catalog(
            materials=[_material("resin", "Resin")],
            suppliers=[_supplier("rg")],
            packages=[
                _package(
                    pid="resin-25",
                    material_id="resin",
                    supplier_id="rg",
                    weight_kg="25",
                    price_incl_vat="340.98",
                    bundle_discounts=[
                        _tier(2, "0.05"),
                        _tier(3, "0.10"),
                        _tier(4, "0.15"),
                    ],
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        line_item = result.line_items[0]
        assert line_item.allocations[0].count == 4
        # 340.98 → 28983 cents discounted unit (15% tier) * 4 = €1159.32.
        assert line_item.cost_incl_vat == Decimal("1159.32")

    def test_tiers_apply_per_package_independently(self) -> None:
        breakdown = _breakdown(
            materials=[
                _aggregated(material_id="resin", name="Resin", weight_kg="100"),
                _aggregated(material_id="hardener", name="Hardener", weight_kg="30"),
            ],
        )
        catalog = _catalog(
            materials=[
                _material("resin", "Resin"),
                _material("hardener", "Hardener"),
            ],
            suppliers=[_supplier("rg")],
            packages=[
                _package(
                    pid="resin-25",
                    material_id="resin",
                    supplier_id="rg",
                    weight_kg="25",
                    price_incl_vat="340.98",
                    bundle_discounts=[
                        _tier(2, "0.05"),
                        _tier(3, "0.10"),
                        _tier(4, "0.15"),
                    ],
                ),
                _package(
                    pid="hardener-7-5",
                    material_id="hardener",
                    supplier_id="rg",
                    weight_kg="7.5",
                    price_incl_vat="100.00",
                    bundle_discounts=[_tier(2, "0.05")],
                ),
            ],
        )

        result = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        resin = next(li for li in result.line_items if li.material_id == "resin")
        hardener = next(li for li in result.line_items if li.material_id == "hardener")
        assert resin.allocations[0].count == 4
        assert hardener.allocations[0].count == 4
        # resin: 28983 * 4 = €1159.32 (15% tier).
        assert resin.cost_incl_vat == Decimal("1159.32")
        # hardener: 9500 * 4 = €380.00 (5% tier — only one published).
        assert hardener.cost_incl_vat == Decimal("380.00")
        rg_subtotal = next(s for s in result.suppliers if s.supplier_id == "rg")
        assert rg_subtotal.subtotal_incl_vat == Decimal("1539.32")
        assert result.total_cost_incl_vat == Decimal("1539.32")

    def test_determinism_under_discounts(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="resin", name="Resin", weight_kg="100")],
        )
        catalog = _catalog(
            materials=[_material("resin", "Resin")],
            suppliers=[_supplier("rg")],
            packages=[
                _package(
                    pid="resin-25",
                    material_id="resin",
                    supplier_id="rg",
                    weight_kg="25",
                    price_incl_vat="340.98",
                    bundle_discounts=[
                        _tier(2, "0.05"),
                        _tier(3, "0.10"),
                        _tier(4, "0.15"),
                    ],
                ),
                _package(
                    pid="resin-5",
                    material_id="resin",
                    supplier_id="rg",
                    weight_kg="5",
                    price_incl_vat="80.00",
                    bundle_discounts=[_tier(2, "0.05")],
                ),
            ],
        )

        result_a = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )
        result_b = optimize_purchase(
            breakdown,
            catalog,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        assert result_a == result_b

    def test_discount_flips_cheapest_choice(self) -> None:
        breakdown = _breakdown(
            materials=[_aggregated(material_id="resin", name="Resin", weight_kg="30")],
        )

        def _packages(discount: list[BundleDiscount]) -> list[SupplierPackage]:
            return [
                _package(
                    pid="big",
                    material_id="resin",
                    supplier_id="rg",
                    weight_kg="25",
                    price_incl_vat="30.00",
                    bundle_discounts=discount,
                ),
                _package(
                    pid="small",
                    material_id="resin",
                    supplier_id="rg",
                    weight_kg="10",
                    price_incl_vat="25.00",
                ),
            ]

        # Baseline cheapest = big + small (35 kg @ €55). With 15% off the big
        # at count = 2 the 2*big allocation drops to €51.00 and wins.
        catalog_without_discount = _catalog(
            materials=[_material("resin", "Resin")],
            suppliers=[_supplier("rg")],
            packages=_packages([]),
        )
        catalog_with_discount = _catalog(
            materials=[_material("resin", "Resin")],
            suppliers=[_supplier("rg")],
            packages=_packages([_tier(2, "0.15")]),
        )

        baseline = optimize_purchase(
            breakdown,
            catalog_without_discount,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )
        discounted = optimize_purchase(
            breakdown,
            catalog_with_discount,
            strategy=Strategy.CHEAPEST,
            overage_pct=Decimal("0"),
            excluded_materials=[],
        )

        baseline_counts = {
            alloc.package_id: alloc.count for alloc in baseline.line_items[0].allocations
        }
        discounted_counts = {
            alloc.package_id: alloc.count for alloc in discounted.line_items[0].allocations
        }
        assert baseline_counts == {"big": 1, "small": 1}
        assert baseline.total_cost_incl_vat == Decimal("55.00")
        assert discounted_counts == {"big": 2}
        assert discounted.total_cost_incl_vat == Decimal("51.00")
