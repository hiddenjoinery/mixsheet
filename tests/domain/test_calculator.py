"""Tests for the per-component material calculator."""

from __future__ import annotations

from decimal import Decimal

import pytest

from mixsheet.domain import (
    AreaHeightVolume,
    Catalog,
    Component,
    DimensionsVolume,
    DirectVolume,
    Material,
    MaterialProportion,
    MixPreset,
    UnknownPresetError,
    calculate_component,
    load_bundled_catalog,
)


def _component(  # noqa: PLR0913
    *,
    component_id: str = "c1",
    name: str = "Test component",
    quantity: int = 1,
    volume: DimensionsVolume | AreaHeightVolume | DirectVolume,
    preset_id: str,
    preset_version: str = "1.0.0",
) -> Component:
    return Component(
        id=component_id,
        name=name,
        quantity=quantity,
        volume=volume,
        preset_id=preset_id,
        preset_version=preset_version,
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


def _density(catalog: Catalog, preset_id: str) -> Decimal:
    preset = catalog.preset_by_id(preset_id)
    assert preset is not None, f"preset {preset_id!r} missing from catalog"
    return preset.density_kg_per_l


@pytest.fixture
def bundled_catalog() -> Catalog:
    return load_bundled_catalog()


class TestVolumeModes:
    def test_dimensions_mode_against_epoxy_mix(self, bundled_catalog: Catalog) -> None:
        component = _component(
            volume=DimensionsVolume(
                length_mm=Decimal("800"),
                width_mm=Decimal("400"),
                height_mm=Decimal("120"),
            ),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        breakdown = calculate_component(component, bundled_catalog)
        density = _density(bundled_catalog, "epoxy-mix")
        assert breakdown.volume_per_component_l == Decimal("38.4")
        assert breakdown.net_volume_l == Decimal("38.4")
        assert breakdown.weight_per_component_kg == Decimal("38.4") * density
        assert breakdown.total_weight_kg == Decimal("38.4") * density
        assert breakdown.density_kg_per_l == density
        assert breakdown.preset_name == "Epoxy granite"

    def test_area_height_mode_against_gantry_beam(self, bundled_catalog: Catalog) -> None:
        component = _component(
            volume=AreaHeightVolume(area_mm2=Decimal("240000"), height_mm=Decimal("80")),
            preset_id="gantry-beam-dynamic-fill",
        )
        breakdown = calculate_component(component, bundled_catalog)
        density = _density(bundled_catalog, "gantry-beam-dynamic-fill")
        assert breakdown.volume_per_component_l == Decimal("19.2")
        assert breakdown.total_weight_kg == Decimal("19.2") * density

    def test_direct_mode_quantity_one(self, bundled_catalog: Catalog) -> None:
        component = _component(
            volume=DirectVolume(volume_l=Decimal("12.5")),
            preset_id="pure-epoxy-low-volume",
        )
        breakdown = calculate_component(component, bundled_catalog)
        density = _density(bundled_catalog, "pure-epoxy-low-volume")
        assert breakdown.volume_per_component_l == Decimal("12.5")
        assert breakdown.net_volume_l == Decimal("12.5")
        assert breakdown.total_weight_kg == Decimal("12.5") * density

    def test_direct_mode_quantity_three(self, bundled_catalog: Catalog) -> None:
        component = _component(
            quantity=3,
            volume=DirectVolume(volume_l=Decimal("12.5")),
            preset_id="pure-epoxy-low-volume",
        )
        breakdown = calculate_component(component, bundled_catalog)
        density = _density(bundled_catalog, "pure-epoxy-low-volume")
        assert breakdown.volume_per_component_l == Decimal("12.5")
        assert breakdown.net_volume_l == Decimal("37.5")
        assert breakdown.total_weight_kg == Decimal("37.5") * density


class TestMaterialRows:
    def test_rows_sum_to_total_weight_under_decimal(self, bundled_catalog: Catalog) -> None:
        component = _component(
            volume=DirectVolume(volume_l=Decimal("10")),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        )
        breakdown = calculate_component(component, bundled_catalog)
        rows_total = sum(
            (row.weight_kg for row in breakdown.materials),
            start=Decimal("0"),
        )
        assert rows_total == breakdown.total_weight_kg

    def test_material_name_comes_from_catalog(self, bundled_catalog: Catalog) -> None:
        component = _component(
            volume=DirectVolume(volume_l=Decimal("5")),
            preset_id="uhpc-mix",
        )
        breakdown = calculate_component(component, bundled_catalog)
        for row in breakdown.materials:
            material = bundled_catalog.material_by_id(row.material_id)
            assert material is not None
            assert row.material_name == material.name
            assert row.material_name

    def test_distributes_total_weight_by_proportion(self) -> None:
        catalog = _custom_catalog(
            materials=[
                Material(id="alpha", name="Alpha", category="binder"),
                Material(id="bravo", name="Bravo", category="aggregate"),
            ],
            presets=[
                MixPreset(
                    id="two-mat",
                    name="Two-material",
                    version="1.0.0",
                    density_kg_per_l=Decimal("1.0"),
                    materials=[
                        MaterialProportion(material_id="alpha", proportion=Decimal("0.4")),
                        MaterialProportion(material_id="bravo", proportion=Decimal("0.6")),
                    ],
                ),
            ],
        )
        component = _component(
            volume=DirectVolume(volume_l=Decimal("10")),
            preset_id="two-mat",
        )
        breakdown = calculate_component(component, catalog)
        weights = {row.material_id: row.weight_kg for row in breakdown.materials}
        assert weights == {"alpha": Decimal("4.0"), "bravo": Decimal("6.0")}


class TestOrderingPrecisionAndEdgeCases:
    def test_rows_sorted_case_insensitively_independent_of_preset_order(self) -> None:
        catalog = _custom_catalog(
            materials=[
                Material(id="quartz", name="Quartz sand", category="aggregate"),
                Material(id="aggregate-fines", name="aggregate fines", category="aggregate"),
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
        component = _component(
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="mix",
        )
        breakdown = calculate_component(component, catalog)
        names = [row.material_name for row in breakdown.materials]
        assert names == ["aggregate fines", "Hardener", "Quartz sand"]

    def test_does_not_quantise_repeating_decimals(self) -> None:
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
                        MaterialProportion(
                            material_id="alpha",
                            proportion=Decimal("0.3333"),
                        ),
                        MaterialProportion(
                            material_id="bravo",
                            proportion=Decimal("0.3333"),
                        ),
                        MaterialProportion(
                            material_id="charlie",
                            proportion=Decimal("0.3334"),
                        ),
                    ],
                ),
            ],
        )
        component = _component(
            volume=DirectVolume(volume_l=Decimal("1") / Decimal("7")),
            preset_id="thirds",
        )
        breakdown = calculate_component(component, catalog)
        for row in breakdown.materials:
            quantised = row.weight_kg.quantize(Decimal("0.01"))
            assert row.weight_kg != quantised

    def test_unknown_preset_id_raises(self, bundled_catalog: Catalog) -> None:
        component = _component(
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="phantom-mix",
        )
        with pytest.raises(UnknownPresetError, match="phantom-mix"):
            calculate_component(component, bundled_catalog)

    def test_pinned_preset_version_mismatch_does_not_raise(
        self,
        bundled_catalog: Catalog,
    ) -> None:
        component = _component(
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="epoxy-mix",
            preset_version="1.0.0",
        )
        breakdown = calculate_component(component, bundled_catalog)
        density = _density(bundled_catalog, "epoxy-mix")
        assert breakdown.density_kg_per_l == density
        assert breakdown.preset_id == "epoxy-mix"

    def test_includes_default_excluded_water(self, bundled_catalog: Catalog) -> None:
        component = _component(
            volume=DirectVolume(volume_l=Decimal("1")),
            preset_id="uhpc-mix",
        )
        breakdown = calculate_component(component, bundled_catalog)
        material_ids = {row.material_id for row in breakdown.materials}
        assert "water" in material_ids


class TestUserFlowExample:
    def test_router_gantry_machine(self, bundled_catalog: Catalog) -> None:
        bed = _component(
            component_id="bed",
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
            component_id="cross-slide",
            name="Cross slide",
            volume=AreaHeightVolume(
                area_mm2=Decimal("240000"),
                height_mm=Decimal("80"),
            ),
            preset_id="gantry-beam-dynamic-fill",
        )

        bed_breakdown = calculate_component(bed, bundled_catalog)
        cross_breakdown = calculate_component(cross_slide, bundled_catalog)

        assert bed_breakdown.net_volume_l == Decimal("38.4")
        assert cross_breakdown.net_volume_l == Decimal("19.2")

        for breakdown in (bed_breakdown, cross_breakdown):
            names = [row.material_name.casefold() for row in breakdown.materials]
            assert names == sorted(names)
