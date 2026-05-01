"""Tests for the pure project aggregator."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from mixsheet.domain import (
    AggregatedMaterial,
    AggregatedMaterialSource,
    AreaHeightVolume,
    Catalog,
    Component,
    DimensionsVolume,
    DirectVolume,
    Material,
    MaterialProportion,
    MixPreset,
    Project,
    ProjectBreakdown,
    PurchaseConfig,
    UnknownPresetError,
    aggregate_project,
    calculate_component,
    load_bundled_catalog,
)

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _component(  # noqa: PLR0913
    *,
    cid: str = "c1",
    name: str | None = None,
    quantity: int = 1,
    volume: DimensionsVolume | AreaHeightVolume | DirectVolume,
    preset_id: str,
    preset_version: str = "1.0.0",
) -> Component:
    return Component(
        id=cid,
        name=name or f"Component {cid}",
        quantity=quantity,
        volume=volume,
        preset_id=preset_id,
        preset_version=preset_version,
    )


def _project(
    *,
    components: list[Component],
    shape: str = "machine",
    pid: str = "router-gantry-2026-05",
    name: str = "Router gantry",
    purchase: PurchaseConfig | None = None,
) -> Project:
    return Project(
        id=pid,
        name=name,
        shape=shape,  # type: ignore[arg-type]
        created_at=NOW,
        updated_at=NOW,
        components=components,
        purchase=purchase or PurchaseConfig(),
    )


def _custom_catalog(
    *,
    materials: list[Material],
    presets: list[MixPreset],
    catalog_version: str = "2026-05-01",
) -> Catalog:
    return Catalog(
        catalog_version=catalog_version,
        materials=materials,
        presets=presets,
        suppliers=[],
        packages=[],
    )


@pytest.fixture
def bundled_catalog() -> Catalog:
    return load_bundled_catalog()


class TestSingleComponentProject:
    def test_single_component_pass_through(self, bundled_catalog: Catalog) -> None:
        component = _component(
            cid="bed",
            name="Bed",
            volume=DimensionsVolume(
                length_mm=Decimal("800"),
                width_mm=Decimal("400"),
                height_mm=Decimal("120"),
            ),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        project = _project(components=[component], shape="single", pid="bed-only", name="Bed only")

        breakdown = aggregate_project(project, bundled_catalog)
        component_breakdown = calculate_component(component, bundled_catalog)

        assert breakdown.shape == "single"
        assert breakdown.project_id == "bed-only"
        assert breakdown.project_name == "Bed only"
        assert len(breakdown.components) == 1
        assert breakdown.components[0] == component_breakdown
        assert breakdown.total_net_volume_l == component_breakdown.net_volume_l
        assert breakdown.total_weight_kg == component_breakdown.total_weight_kg
        assert len(breakdown.materials) == len(component_breakdown.materials)
        for material in breakdown.materials:
            assert len(material.sources) == 1
            assert material.sources[0].component_id == "bed"
            assert material.sources[0].preset_id == "epoxy-mix"


class TestMachineProjectAggregation:
    def test_two_components_different_presets_share_one_material(
        self,
        bundled_catalog: Catalog,
    ) -> None:
        bed = _component(
            cid="bed",
            name="Bed",
            volume=DimensionsVolume(
                length_mm=Decimal("800"),
                width_mm=Decimal("400"),
                height_mm=Decimal("120"),
            ),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        cross_slide = _component(
            cid="cross-slide",
            name="Cross slide",
            volume=AreaHeightVolume(
                area_mm2=Decimal("240000"),
                height_mm=Decimal("80"),
            ),
            preset_id="gantry-beam-dynamic-fill",
        )
        project = _project(components=[bed, cross_slide])

        breakdown = aggregate_project(project, bundled_catalog)

        assert breakdown.shape == "machine"
        assert [c.component_id for c in breakdown.components] == ["bed", "cross-slide"]

        durigid = next(m for m in breakdown.materials if m.material_id == "durigid-1-3")
        assert [s.component_id for s in durigid.sources] == ["bed", "cross-slide"]
        assert [s.preset_id for s in durigid.sources] == [
            "epoxy-mix",
            "gantry-beam-dynamic-fill",
        ]
        bed_breakdown = calculate_component(bed, bundled_catalog)
        cross_breakdown = calculate_component(cross_slide, bundled_catalog)
        bed_durigid = next(r for r in bed_breakdown.materials if r.material_id == "durigid-1-3")
        cross_durigid = next(r for r in cross_breakdown.materials if r.material_id == "durigid-1-3")
        assert durigid.sources[0].weight_kg == bed_durigid.weight_kg
        assert durigid.sources[1].weight_kg == cross_durigid.weight_kg
        assert durigid.total_weight_kg == bed_durigid.weight_kg + cross_durigid.weight_kg

    def test_two_components_same_preset_two_source_entries(self) -> None:
        catalog = _custom_catalog(
            materials=[
                Material(id="cement", name="Cement", category="binder"),
                Material(id="sand", name="Sand", category="aggregate"),
            ],
            presets=[
                MixPreset(
                    id="simple",
                    name="Simple",
                    version="1.0.0",
                    density_kg_per_l=Decimal("1.0"),
                    materials=[
                        MaterialProportion(material_id="cement", proportion=Decimal("0.3")),
                        MaterialProportion(material_id="sand", proportion=Decimal("0.7")),
                    ],
                ),
            ],
        )
        a = _component(
            cid="a",
            volume=DirectVolume(volume_l=Decimal("10")),
            preset_id="simple",
        )
        b = _component(
            cid="b",
            volume=DirectVolume(volume_l=Decimal("10")),
            preset_id="simple",
        )
        project = _project(components=[a, b])

        breakdown = aggregate_project(project, catalog)

        cement = next(m for m in breakdown.materials if m.material_id == "cement")
        assert len(cement.sources) == 2
        assert [s.component_id for s in cement.sources] == ["a", "b"]
        assert cement.sources[0].weight_kg == Decimal("3.0")
        assert cement.sources[1].weight_kg == Decimal("3.0")
        assert cement.total_weight_kg == Decimal("6.0")


class TestOrdering:
    def test_materials_sorted_alphabetically_independent_of_preset_order(self) -> None:
        catalog = _custom_catalog(
            materials=[
                Material(id="quartz", name="Quartz sand", category="aggregate"),
                Material(id="aggregate-fines", name="Aggregate fines", category="aggregate"),
                Material(id="hardener", name="Hardener", category="additive"),
            ],
            presets=[
                MixPreset(
                    id="mix",
                    name="Out-of-order",
                    version="1.0.0",
                    density_kg_per_l=Decimal("1.0"),
                    materials=[
                        MaterialProportion(material_id="quartz", proportion=Decimal("0.5")),
                        MaterialProportion(
                            material_id="aggregate-fines",
                            proportion=Decimal("0.3"),
                        ),
                        MaterialProportion(material_id="hardener", proportion=Decimal("0.2")),
                    ],
                ),
            ],
        )
        a = _component(
            cid="a",
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="mix",
        )
        b = _component(
            cid="b",
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="mix",
        )
        project = _project(components=[a, b])

        breakdown = aggregate_project(project, catalog)

        names = [m.material_name for m in breakdown.materials]
        assert names == ["Aggregate fines", "Hardener", "Quartz sand"]
        for material in breakdown.materials:
            assert [s.component_id for s in material.sources] == ["a", "b"]


class TestPrecision:
    def test_does_not_quantise_aggregated_totals(self) -> None:
        catalog = _custom_catalog(
            materials=[
                Material(id="alpha", name="Alpha", category="binder"),
                Material(id="bravo", name="Bravo", category="aggregate"),
                Material(id="charlie", name="Charlie", category="aggregate"),
            ],
            presets=[
                MixPreset(
                    id="thirds",
                    name="Thirds",
                    version="1.0.0",
                    density_kg_per_l=Decimal("1"),
                    materials=[
                        MaterialProportion(material_id="alpha", proportion=Decimal("0.3333")),
                        MaterialProportion(material_id="bravo", proportion=Decimal("0.3333")),
                        MaterialProportion(material_id="charlie", proportion=Decimal("0.3334")),
                    ],
                ),
            ],
        )
        a = _component(
            cid="a",
            volume=DirectVolume(volume_l=Decimal("1") / Decimal("7")),
            preset_id="thirds",
        )
        b = _component(
            cid="b",
            volume=DirectVolume(volume_l=Decimal("1") / Decimal("11")),
            preset_id="thirds",
        )
        project = _project(components=[a, b])

        breakdown = aggregate_project(project, catalog)

        for material in breakdown.materials:
            quantised = material.total_weight_kg.quantize(Decimal("0.01"))
            assert material.total_weight_kg != quantised

    def test_material_totals_reconcile_with_project_total(
        self,
        bundled_catalog: Catalog,
    ) -> None:
        bed = _component(
            cid="bed",
            volume=DirectVolume(volume_l=Decimal("38.4")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        slide = _component(
            cid="slide",
            volume=DirectVolume(volume_l=Decimal("19.2")),
            preset_id="gantry-beam-dynamic-fill",
        )
        project = _project(components=[bed, slide])

        breakdown = aggregate_project(project, bundled_catalog)

        materials_total = sum(
            (m.total_weight_kg for m in breakdown.materials),
            start=Decimal("0"),
        )
        assert materials_total == breakdown.total_weight_kg

    def test_volume_total_sums_components(self, bundled_catalog: Catalog) -> None:
        bed = _component(
            cid="bed",
            volume=DirectVolume(volume_l=Decimal("38.4")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        slide = _component(
            cid="slide",
            volume=DirectVolume(volume_l=Decimal("19.2")),
            preset_id="gantry-beam-dynamic-fill",
        )
        project = _project(components=[bed, slide])

        breakdown = aggregate_project(project, bundled_catalog)

        assert breakdown.total_net_volume_l == Decimal("57.6")


class TestPurchaseFieldsIgnored:
    def test_excluded_materials_still_present(self, bundled_catalog: Catalog) -> None:
        component = _component(
            cid="plate",
            volume=DirectVolume(volume_l=Decimal("5")),
            preset_id="uhpc-mix",
        )
        project = _project(
            components=[component],
            shape="single",
            pid="plate",
            name="Plate",
            purchase=PurchaseConfig(excluded_materials=["water"]),
        )

        breakdown = aggregate_project(project, bundled_catalog)

        material_ids = {m.material_id for m in breakdown.materials}
        assert "water" in material_ids

    def test_overage_pct_does_not_affect_totals(self, bundled_catalog: Catalog) -> None:
        component = _component(
            cid="bed",
            volume=DirectVolume(volume_l=Decimal("10")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        no_overage = _project(
            components=[component],
            shape="single",
            pid="bed",
            name="Bed",
            purchase=PurchaseConfig(overage_pct=Decimal("0")),
        )
        with_overage = _project(
            components=[component],
            shape="single",
            pid="bed",
            name="Bed",
            purchase=PurchaseConfig(overage_pct=Decimal("0.10")),
        )

        baseline = aggregate_project(no_overage, bundled_catalog)
        inflated = aggregate_project(with_overage, bundled_catalog)

        assert baseline.total_weight_kg == inflated.total_weight_kg
        assert baseline.materials == inflated.materials


class TestErrorPaths:
    def test_unknown_preset_propagates(self, bundled_catalog: Catalog) -> None:
        good = _component(
            cid="good",
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        bad = _component(
            cid="bad",
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="phantom-mix",
        )
        project = _project(components=[good, bad])

        with pytest.raises(UnknownPresetError, match="phantom-mix"):
            aggregate_project(project, bundled_catalog)


class TestPurity:
    def test_does_not_mutate_inputs(self, bundled_catalog: Catalog) -> None:
        bed = _component(
            cid="bed",
            volume=DirectVolume(volume_l=Decimal("10")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        slide = _component(
            cid="slide",
            volume=DirectVolume(volume_l=Decimal("5")),
            preset_id="gantry-beam-dynamic-fill",
        )
        project = _project(components=[bed, slide])

        project_before = project.model_dump()
        catalog_before = bundled_catalog.model_dump()

        first = aggregate_project(project, bundled_catalog)
        second = aggregate_project(project, bundled_catalog)

        assert project.model_dump() == project_before
        assert bundled_catalog.model_dump() == catalog_before
        assert first == second


class TestFrozenResult:
    def test_project_breakdown_is_frozen(self, bundled_catalog: Catalog) -> None:
        component = _component(
            cid="bed",
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        project = _project(components=[component], shape="single", pid="bed", name="Bed")
        breakdown = aggregate_project(project, bundled_catalog)

        with pytest.raises(ValidationError):
            breakdown.total_weight_kg = Decimal("0")  # type: ignore[misc]

    def test_aggregated_material_is_frozen(self) -> None:
        material = AggregatedMaterial(
            material_id="cement",
            material_name="Cement",
            total_weight_kg=Decimal("1"),
            sources=[
                AggregatedMaterialSource(
                    component_id="a",
                    preset_id="p",
                    weight_kg=Decimal("1"),
                ),
            ],
        )
        with pytest.raises(ValidationError):
            material.total_weight_kg = Decimal("2")  # type: ignore[misc]

    def test_aggregated_material_source_is_frozen(self) -> None:
        source = AggregatedMaterialSource(
            component_id="a",
            preset_id="p",
            weight_kg=Decimal("1"),
        )
        with pytest.raises(ValidationError):
            source.weight_kg = Decimal("2")  # type: ignore[misc]


class TestProjectBreakdownContract:
    def test_echoes_project_metadata(self, bundled_catalog: Catalog) -> None:
        component = _component(
            cid="bed",
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        project = _project(
            components=[component],
            shape="machine",
            pid="router-gantry-2026-05",
            name="Router gantry",
        )
        breakdown = ProjectBreakdown.model_validate(
            aggregate_project(project, bundled_catalog).model_dump(),
        )
        assert breakdown.project_id == "router-gantry-2026-05"
        assert breakdown.project_name == "Router gantry"
        assert breakdown.shape == "machine"
