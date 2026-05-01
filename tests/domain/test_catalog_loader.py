"""Catalog file shape and fail-fast loader."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mixsheet.domain import CatalogError, load_bundled_catalog, load_catalog

if TYPE_CHECKING:
    from pathlib import Path


_VALID_PRESETS = """\
catalog_version: "2026-05-01"
materials:
  - id: cement
    name: Cement
    category: binder
  - id: water
    name: Water
    category: liquid
    default_excluded: true
presets:
  - id: m
    name: Mix
    version: "1.0.0"
    density_kg_per_l: 2.0
    materials:
      - material_id: cement
        proportion: 0.95
      - material_id: water
        proportion: 0.05
"""

_VALID_SUPPLIERS = """\
catalog_version: "2026-05-01"
suppliers:
  - id: s1
    name: Supplier One
packages:
  - id: cement-25kg
    material_id: cement
    supplier_id: s1
    weight_kg: 25.0
    price_incl_vat: 50.00
"""


def _write_pair(tmp_path: Path, presets: str, suppliers: str) -> tuple[Path, Path]:
    p = tmp_path / "presets.yaml"
    s = tmp_path / "suppliers.yaml"
    p.write_text(presets, encoding="utf-8")
    s.write_text(suppliers, encoding="utf-8")
    return p, s


class TestCatalogVersion:
    def test_loads_a_catalog_with_a_valid_version(self, tmp_path: Path) -> None:
        p, s = _write_pair(tmp_path, _VALID_PRESETS, _VALID_SUPPLIERS)
        catalog = load_catalog(p, s)
        assert catalog.catalog_version == "2026-05-01"

    def test_rejects_a_catalog_without_a_version(self, tmp_path: Path) -> None:
        bad_presets = _VALID_PRESETS.replace('catalog_version: "2026-05-01"\n', "")
        p, s = _write_pair(tmp_path, bad_presets, _VALID_SUPPLIERS)
        with pytest.raises(CatalogError, match="catalog_version"):
            load_catalog(p, s)

    def test_rejects_a_malformed_catalog_version(self, tmp_path: Path) -> None:
        bad_presets = _VALID_PRESETS.replace(
            'catalog_version: "2026-05-01"',
            'catalog_version: "May 2026"',
        )
        p, s = _write_pair(tmp_path, bad_presets, _VALID_SUPPLIERS)
        with pytest.raises(CatalogError, match="YYYY-MM-DD"):
            load_catalog(p, s)


class TestFailFastLoader:
    def test_loads_a_clean_catalog_without_raising(self) -> None:
        catalog = load_bundled_catalog()
        assert len(catalog.materials) > 0
        assert len(catalog.presets) > 0

    def test_reports_an_unknown_material_in_a_preset(self, tmp_path: Path) -> None:
        bad = _VALID_PRESETS.replace("material_id: cement", "material_id: phantom", 1)
        p, s = _write_pair(tmp_path, bad, _VALID_SUPPLIERS)
        with pytest.raises(CatalogError) as exc_info:
            load_catalog(p, s)
        assert "phantom" in str(exc_info.value)
        assert "'m'" in str(exc_info.value)

    def test_reports_a_package_with_unknown_material(self, tmp_path: Path) -> None:
        bad_suppliers = _VALID_SUPPLIERS.replace(
            "material_id: cement",
            "material_id: phantom",
        )
        p, s = _write_pair(tmp_path, _VALID_PRESETS, bad_suppliers)
        with pytest.raises(CatalogError, match="phantom"):
            load_catalog(p, s)

    def test_reports_a_package_with_unknown_supplier(self, tmp_path: Path) -> None:
        bad_suppliers = _VALID_SUPPLIERS.replace("supplier_id: s1", "supplier_id: ghost")
        p, s = _write_pair(tmp_path, _VALID_PRESETS, bad_suppliers)
        with pytest.raises(CatalogError, match="ghost"):
            load_catalog(p, s)

    def test_reports_duplicate_material_ids(self, tmp_path: Path) -> None:
        bad = _VALID_PRESETS.replace(
            "  - id: cement\n    name: Cement\n    category: binder\n",
            "  - id: cement\n    name: Cement\n    category: binder\n"
            "  - id: cement\n    name: Cement Two\n    category: binder\n",
            1,
        )
        p, s = _write_pair(tmp_path, bad, _VALID_SUPPLIERS)
        with pytest.raises(CatalogError, match="duplicate material id 'cement'"):
            load_catalog(p, s)

    def test_refuses_unsafe_yaml_tags(self, tmp_path: Path) -> None:
        evil = (
            'catalog_version: "2026-05-01"\n'
            "materials:\n"
            "  - !!python/object:os.system [echo pwned]\n"
        )
        p, s = _write_pair(tmp_path, evil, _VALID_SUPPLIERS)
        with pytest.raises(CatalogError):
            load_catalog(p, s)

    def test_reports_mismatched_versions_between_files(self, tmp_path: Path) -> None:
        bad_suppliers = _VALID_SUPPLIERS.replace("2026-05-01", "2026-06-01")
        p, s = _write_pair(tmp_path, _VALID_PRESETS, bad_suppliers)
        with pytest.raises(CatalogError, match="catalog_version mismatch"):
            load_catalog(p, s)

    def test_rejects_non_string_catalog_version(self, tmp_path: Path) -> None:
        bad = _VALID_PRESETS.replace('catalog_version: "2026-05-01"', "catalog_version: 20260501")
        p, s = _write_pair(tmp_path, bad, _VALID_SUPPLIERS)
        with pytest.raises(CatalogError, match="must be a string"):
            load_catalog(p, s)

    def test_rejects_non_mapping_top_level(self, tmp_path: Path) -> None:
        p, s = _write_pair(tmp_path, "- 1\n- 2\n", _VALID_SUPPLIERS)
        with pytest.raises(CatalogError, match="must be a mapping"):
            load_catalog(p, s)

    def test_rejects_non_list_section(self, tmp_path: Path) -> None:
        bad = 'catalog_version: "2026-05-01"\nmaterials: not-a-list\npresets: []\n'
        p, s = _write_pair(tmp_path, bad, _VALID_SUPPLIERS)
        with pytest.raises(CatalogError, match="must be a list"):
            load_catalog(p, s)

    def test_unknown_lookups_return_none(self) -> None:
        catalog = load_bundled_catalog()
        assert catalog.material_by_id("phantom") is None
        assert catalog.preset_by_id("phantom") is None

    def test_proportion_sum_violation_surfaces(self, tmp_path: Path) -> None:
        bad = _VALID_PRESETS.replace("proportion: 0.95", "proportion: 0.50")
        p, s = _write_pair(tmp_path, bad, _VALID_SUPPLIERS)
        with pytest.raises(CatalogError, match="proportions sum"):
            load_catalog(p, s)
