"""Public domain model surface for The Mix Sheet.

Importing from ``mixsheet.domain`` is the supported way to reach the
catalog, project, strategy, and display-precision types. Submodules
remain importable but are considered internal.
"""

from __future__ import annotations

from mixsheet.domain.catalog import (
    Catalog,
    CatalogError,
    Material,
    MaterialProportion,
    MixPreset,
    Supplier,
    SupplierPackage,
    load_bundled_catalog,
    load_catalog,
)
from mixsheet.domain.display import (
    PERCENT_DECIMALS,
    PRICE_DECIMALS,
    QUANTITY_DECIMALS_HIGH,
    QUANTITY_DECIMALS_LOW,
    QUANTITY_THRESHOLD,
)
from mixsheet.domain.project import (
    AreaHeightVolume,
    CatalogVersionMismatch,
    Component,
    DimensionsVolume,
    DirectVolume,
    Project,
    ProjectFileError,
    ProjectLoadResult,
    PurchaseConfig,
    Volume,
    load_project,
    new_project,
    save_project,
)
from mixsheet.domain.strategy import Strategy

__all__ = [
    "PERCENT_DECIMALS",
    "PRICE_DECIMALS",
    "QUANTITY_DECIMALS_HIGH",
    "QUANTITY_DECIMALS_LOW",
    "QUANTITY_THRESHOLD",
    "AreaHeightVolume",
    "Catalog",
    "CatalogError",
    "CatalogVersionMismatch",
    "Component",
    "DimensionsVolume",
    "DirectVolume",
    "Material",
    "MaterialProportion",
    "MixPreset",
    "Project",
    "ProjectFileError",
    "ProjectLoadResult",
    "PurchaseConfig",
    "Strategy",
    "Supplier",
    "SupplierPackage",
    "Volume",
    "load_bundled_catalog",
    "load_catalog",
    "load_project",
    "new_project",
    "save_project",
]
