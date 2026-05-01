"""Material catalog models and fail-fast YAML loader.

The catalog is the single source of truth for materials, mix presets,
suppliers, and supplier packages. Models are strict and frozen so
parsed values cannot drift in memory; the loader aggregates every
problem into one error so a malformed catalog refuses to load instead
of producing wrong results downstream.
"""

from __future__ import annotations

import re
from decimal import Decimal
from importlib.resources import files
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from mixsheet.domain._yaml import safe_load_decimal

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

CATALOG_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PROPORTION_SUM_TOLERANCE = Decimal("0.0001")
PROPORTION_SUM_TARGET = Decimal("1.0")


class CatalogError(ValueError):
    """Raised when a catalog file fails fast-validation.

    The message lists every problem found in a single load pass, so a
    user fixing a hand-edited YAML can address them all at once.
    """

    def __init__(self, problems: list[str]) -> None:
        """Build the error from a list of human-readable problem strings."""
        self.problems = list(problems)
        joined = "\n  - ".join(self.problems)
        super().__init__(f"Catalog validation failed:\n  - {joined}")


class Material(BaseModel):
    """A purchasable raw material referenced by mix presets and packages."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    default_excluded: bool = False


class MaterialProportion(BaseModel):
    """A single material's mass fraction within a mix preset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    material_id: str = Field(min_length=1)
    proportion: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))


class MixPreset(BaseModel):
    """A named mix recipe: density and per-material mass fractions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    density_kg_per_l: Decimal = Field(gt=Decimal("0"))
    description: str | None = None
    application: str | None = None
    materials: list[MaterialProportion] = Field(min_length=1)

    @model_validator(mode="after")
    def _proportions_sum_to_one(self) -> MixPreset:
        total = sum((row.proportion for row in self.materials), start=Decimal("0"))
        if abs(total - PROPORTION_SUM_TARGET) > PROPORTION_SUM_TOLERANCE:
            msg = (
                f"preset {self.id!r} proportions sum to {total} "
                f"(expected 1.0 ± {PROPORTION_SUM_TOLERANCE})"
            )
            raise ValueError(msg)
        return self


class Supplier(BaseModel):
    """A vendor offering one or more :class:`SupplierPackage` SKUs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class SupplierPackage(BaseModel):
    """A purchasable SKU: weight and gross price for a single material."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)
    supplier_id: str = Field(min_length=1)
    weight_kg: Decimal = Field(gt=Decimal("0"))
    price_incl_vat: Decimal = Field(ge=Decimal("0"))

    @property
    def price_per_kg(self) -> Decimal:
        """Return the gross unit price (€/kg) derived from price ÷ weight."""
        return self.price_incl_vat / self.weight_kg


class Catalog(BaseModel):
    """A fully validated catalog: materials, presets, suppliers, packages.

    Cross-reference checks (no duplicate ids, every reference resolves)
    run in :func:`load_catalog`, not as a model validator, so that the
    aggregated :class:`CatalogError` is not swallowed by Pydantic's
    ``ValidationError`` wrapping.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalog_version: str
    materials: list[Material]
    presets: list[MixPreset]
    suppliers: list[Supplier]
    packages: list[SupplierPackage]

    def material_by_id(self, material_id: str) -> Material | None:
        """Return the material with the given id, or ``None`` if unknown."""
        return next((m for m in self.materials if m.id == material_id), None)

    def preset_by_id(self, preset_id: str) -> MixPreset | None:
        """Return the preset with the given id, or ``None`` if unknown."""
        return next((p for p in self.presets if p.id == preset_id), None)


def _duplicate_id_problems(kind: str, items: Iterable[Any]) -> list[str]:
    seen: dict[str, int] = {}
    for item in items:
        seen[item.id] = seen.get(item.id, 0) + 1
    return [f"duplicate {kind} id {item_id!r}" for item_id, count in seen.items() if count > 1]


def _cross_reference_problems(catalog: Catalog) -> list[str]:
    problems: list[str] = []
    problems.extend(_duplicate_id_problems("material", catalog.materials))
    problems.extend(_duplicate_id_problems("preset", catalog.presets))
    problems.extend(_duplicate_id_problems("supplier", catalog.suppliers))
    problems.extend(_duplicate_id_problems("package", catalog.packages))

    material_ids = {m.id for m in catalog.materials}
    supplier_ids = {s.id for s in catalog.suppliers}

    problems.extend(
        f"preset {preset.id!r} references unknown material {row.material_id!r}"
        for preset in catalog.presets
        for row in preset.materials
        if row.material_id not in material_ids
    )
    for package in catalog.packages:
        if package.material_id not in material_ids:
            problems.append(
                f"package {package.id!r} references unknown material {package.material_id!r}",
            )
        if package.supplier_id not in supplier_ids:
            problems.append(
                f"package {package.id!r} references unknown supplier {package.supplier_id!r}",
            )
    return problems


def _validate_catalog_version_string(value: object, source: str) -> str:
    if not isinstance(value, str):
        msg = f"{source}: catalog_version must be a string in YYYY-MM-DD form"
        raise CatalogError([msg])
    if not CATALOG_VERSION_PATTERN.fullmatch(value):
        msg = f"{source}: catalog_version {value!r} is not in YYYY-MM-DD form"
        raise CatalogError([msg])
    return value


def _read_yaml_mapping(text: str, source: str) -> dict[str, Any]:
    try:
        data = safe_load_decimal(text)
    except yaml.YAMLError as exc:
        msg = f"{source}: YAML parse error: {exc}"
        raise CatalogError([msg]) from exc
    if not isinstance(data, dict):
        type_name = type(data).__name__
        msg = f"{source}: top-level YAML must be a mapping, got {type_name}"
        raise CatalogError([msg])
    return data


def _expect_list(data: dict[str, Any], key: str, source: str) -> list[Any]:
    raw = data.get(key, [])
    if not isinstance(raw, list):
        msg = f"{source}: {key!r} must be a list, got {type(raw).__name__}"
        raise CatalogError([msg])
    return raw


def _require_catalog_version(data: dict[str, Any], source: str) -> str:
    if "catalog_version" not in data:
        msg = f"{source}: missing required field 'catalog_version'"
        raise CatalogError([msg])
    return _validate_catalog_version_string(data["catalog_version"], source)


def _format_pydantic_errors(exc: ValidationError) -> list[str]:
    problems: list[str] = []
    for err in exc.errors():
        location = ".".join(str(part) for part in err["loc"]) or "<root>"
        problems.append(f"{location}: {err['msg']}")
    return problems


def load_catalog(presets_path: Path, suppliers_path: Path) -> Catalog:
    """Load and validate a presets + suppliers catalog from two YAML files.

    Both files MUST declare a matching ``catalog_version``. The loader
    raises :class:`CatalogError` once with every problem aggregated.
    """
    presets_text = presets_path.read_text(encoding="utf-8")
    suppliers_text = suppliers_path.read_text(encoding="utf-8")
    return _build_catalog(
        presets_text,
        suppliers_text,
        presets_source=str(presets_path),
        suppliers_source=str(suppliers_path),
    )


def load_bundled_catalog() -> Catalog:
    """Load the catalog shipped inside the ``mixsheet.data`` package."""
    data_root = files("mixsheet.data")
    presets_text = (data_root / "presets.yaml").read_text(encoding="utf-8")
    suppliers_text = (data_root / "suppliers.yaml").read_text(encoding="utf-8")
    return _build_catalog(
        presets_text,
        suppliers_text,
        presets_source="mixsheet.data/presets.yaml",
        suppliers_source="mixsheet.data/suppliers.yaml",
    )


def _build_catalog(
    presets_text: str,
    suppliers_text: str,
    *,
    presets_source: str,
    suppliers_source: str,
) -> Catalog:
    presets_data = _read_yaml_mapping(presets_text, presets_source)
    suppliers_data = _read_yaml_mapping(suppliers_text, suppliers_source)

    presets_version = _require_catalog_version(presets_data, presets_source)
    suppliers_version = _require_catalog_version(suppliers_data, suppliers_source)
    if presets_version != suppliers_version:
        msg = (
            f"catalog_version mismatch: presets={presets_version!r}, "
            f"suppliers={suppliers_version!r}"
        )
        raise CatalogError([msg])

    materials_raw = _expect_list(presets_data, "materials", presets_source)
    presets_raw = _expect_list(presets_data, "presets", presets_source)
    suppliers_raw = _expect_list(suppliers_data, "suppliers", suppliers_source)
    packages_raw = _expect_list(suppliers_data, "packages", suppliers_source)

    try:
        catalog = Catalog.model_validate(
            {
                "catalog_version": presets_version,
                "materials": materials_raw,
                "presets": presets_raw,
                "suppliers": suppliers_raw,
                "packages": packages_raw,
            },
        )
    except ValidationError as exc:
        raise CatalogError(_format_pydantic_errors(exc)) from exc

    cross_problems = _cross_reference_problems(catalog)
    if cross_problems:
        raise CatalogError(cross_problems)
    return catalog
