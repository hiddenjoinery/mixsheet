"""Catalog model unit tests (Material, MixPreset, Supplier, SupplierPackage)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from mixsheet.domain import (
    BundleDiscount,
    Material,
    MaterialProportion,
    MixPreset,
    Supplier,
    SupplierPackage,
)


class TestMaterial:
    def test_loads_a_material_with_default_excluded_set(self) -> None:
        material = Material(
            id="water",
            name="Water",
            category="liquid",
            default_excluded=True,
        )
        assert material.default_excluded is True

    def test_default_excluded_defaults_to_false(self) -> None:
        material = Material(id="cement", name="Cement", category="binder")
        assert material.default_excluded is False

    def test_rejects_an_empty_material_id(self) -> None:
        with pytest.raises(ValidationError):
            Material(id="", name="Water", category="liquid")


class TestMaterialProportion:
    def test_accepts_a_fractional_proportion(self) -> None:
        row = MaterialProportion(material_id="cement", proportion=Decimal("0.3698"))
        assert row.proportion == Decimal("0.3698")

    def test_rejects_a_proportion_of_zero(self) -> None:
        with pytest.raises(ValidationError, match="greater than 0"):
            MaterialProportion(material_id="cement", proportion=Decimal("0"))

    def test_rejects_a_proportion_above_one(self) -> None:
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            MaterialProportion(material_id="cement", proportion=Decimal("1.0001"))


class TestMixPreset:
    def _row(self, material_id: str, proportion: str) -> MaterialProportion:
        return MaterialProportion(material_id=material_id, proportion=Decimal(proportion))

    def test_loads_a_preset_with_summing_proportions(self) -> None:
        preset = MixPreset(
            id="four-mat",
            name="Four-mat",
            version="1.0.0",
            density_kg_per_l=Decimal("1.91"),
            materials=[
                self._row("a", "0.0792"),
                self._row("b", "0.2772"),
                self._row("c", "0.5436"),
                self._row("d", "0.1000"),
            ],
        )
        assert isinstance(preset.density_kg_per_l, Decimal)
        assert preset.density_kg_per_l == Decimal("1.91")

    def test_rejects_proportions_that_do_not_sum_to_one(self) -> None:
        with pytest.raises(ValidationError, match=r"0\.99"):
            MixPreset(
                id="under-sum",
                name="Under-sum",
                version="1.0.0",
                density_kg_per_l=Decimal("1.0"),
                materials=[self._row("a", "0.99")],
            )


class TestSupplierAndPackage:
    def test_supplier_loads_without_vat_rate(self) -> None:
        supplier = Supplier(id="moertelshop", name="Moertelshop")
        assert supplier.id == "moertelshop"

    def test_supplier_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            Supplier.model_validate({"id": "x", "name": "X", "vat_rate": Decimal("0.19")})

    def test_loads_a_package_and_exposes_derived_price_per_kg(self) -> None:
        package = SupplierPackage(
            id="aeropor-21kg",
            material_id="aeropor",
            supplier_id="moertelshop",
            weight_kg=Decimal("21.0"),
            price_incl_vat=Decimal("84.10"),
        )
        expected = Decimal("84.10") / Decimal("21.0")
        assert package.price_per_kg == expected

    def test_rejects_a_zero_weight_package(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPackage(
                id="zero",
                material_id="x",
                supplier_id="y",
                weight_kg=Decimal("0"),
                price_incl_vat=Decimal("1.0"),
            )

    def test_rejects_a_negative_price(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPackage(
                id="neg",
                material_id="x",
                supplier_id="y",
                weight_kg=Decimal("1.0"),
                price_incl_vat=Decimal("-0.01"),
            )

    def test_loads_a_package_with_a_product_url_and_bundle_discounts(self) -> None:
        package = SupplierPackage(
            id="epoxy-resin-25kg",
            material_id="epoxy-resin",
            supplier_id="rg-faserverbund",
            weight_kg=Decimal("25.0"),
            price_incl_vat=Decimal("340.98"),
            product_url="https://www.r-g.de/en/art/100133",  # type: ignore[arg-type]
            bundle_discounts=[
                BundleDiscount(min_quantity=2, discount_pct=Decimal("0.05")),
                BundleDiscount(min_quantity=4, discount_pct=Decimal("0.15")),
            ],
        )
        assert str(package.product_url) == "https://www.r-g.de/en/art/100133"
        assert len(package.bundle_discounts) == 2

    def test_rejects_a_malformed_product_url(self) -> None:
        with pytest.raises(ValidationError):
            SupplierPackage.model_validate(
                {
                    "id": "p",
                    "material_id": "x",
                    "supplier_id": "y",
                    "weight_kg": Decimal("1.0"),
                    "price_incl_vat": Decimal("1.0"),
                    "product_url": "not-a-url",
                },
            )

    def test_rejects_bundle_tiers_with_descending_min_quantity(self) -> None:
        with pytest.raises(ValidationError, match="strictly ascending"):
            SupplierPackage(
                id="p",
                material_id="x",
                supplier_id="y",
                weight_kg=Decimal("1.0"),
                price_incl_vat=Decimal("1.0"),
                bundle_discounts=[
                    BundleDiscount(min_quantity=4, discount_pct=Decimal("0.05")),
                    BundleDiscount(min_quantity=2, discount_pct=Decimal("0.10")),
                ],
            )

    def test_rejects_bundle_tiers_with_non_increasing_discount(self) -> None:
        with pytest.raises(ValidationError, match="strictly ascending"):
            SupplierPackage(
                id="p",
                material_id="x",
                supplier_id="y",
                weight_kg=Decimal("1.0"),
                price_incl_vat=Decimal("1.0"),
                bundle_discounts=[
                    BundleDiscount(min_quantity=2, discount_pct=Decimal("0.10")),
                    BundleDiscount(min_quantity=4, discount_pct=Decimal("0.10")),
                ],
            )


class TestBundleDiscount:
    def test_rejects_a_min_quantity_below_two(self) -> None:
        with pytest.raises(ValidationError, match="greater than or equal to 2"):
            BundleDiscount(min_quantity=1, discount_pct=Decimal("0.05"))

    def test_rejects_a_discount_pct_at_or_above_one(self) -> None:
        with pytest.raises(ValidationError, match="less than 1"):
            BundleDiscount(min_quantity=2, discount_pct=Decimal("1.0"))

    def test_rejects_a_zero_discount_pct(self) -> None:
        with pytest.raises(ValidationError, match="greater than 0"):
            BundleDiscount(min_quantity=2, discount_pct=Decimal("0"))
