"""Public domain model surface for The Mix Sheet.

Importing from ``mixsheet.domain`` is the supported way to reach the
catalog, project, calculator, aggregator, optimizer, renderer, strategy,
and display-precision types. Submodules remain importable but are
considered internal.
"""

from __future__ import annotations

from mixsheet.domain.aggregator import (
    AggregatedMaterial,
    AggregatedMaterialSource,
    ProjectBreakdown,
    aggregate_project,
)
from mixsheet.domain.calculator import (
    ComponentBreakdown,
    MaterialBreakdownRow,
    UnknownPresetError,
    calculate_component,
)
from mixsheet.domain.catalog import (
    BundleDiscount,
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
from mixsheet.domain.mixsheet_renderer import (
    ComponentMixSheetView,
    MixSheetMaterialRow,
    render_component_mixsheet,
)
from mixsheet.domain.optimizer import (
    CatalogTooBroadError,
    PurchaseAllocation,
    PurchaseLineItem,
    PurchaseList,
    SupplierSubtotal,
    UnpurchasableMaterialError,
    optimize_purchase,
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
from mixsheet.domain.renderer import (
    PurchaseAllocationView,
    PurchaseLineItemSummaryView,
    PurchaseLineItemView,
    PurchaseListView,
    SupplierGroupView,
    render_purchase_list,
)
from mixsheet.domain.strategy import Strategy

__all__ = [
    "PERCENT_DECIMALS",
    "PRICE_DECIMALS",
    "QUANTITY_DECIMALS_HIGH",
    "QUANTITY_DECIMALS_LOW",
    "QUANTITY_THRESHOLD",
    "AggregatedMaterial",
    "AggregatedMaterialSource",
    "AreaHeightVolume",
    "BundleDiscount",
    "Catalog",
    "CatalogError",
    "CatalogTooBroadError",
    "CatalogVersionMismatch",
    "Component",
    "ComponentBreakdown",
    "ComponentMixSheetView",
    "DimensionsVolume",
    "DirectVolume",
    "Material",
    "MaterialBreakdownRow",
    "MaterialProportion",
    "MixPreset",
    "MixSheetMaterialRow",
    "Project",
    "ProjectBreakdown",
    "ProjectFileError",
    "ProjectLoadResult",
    "PurchaseAllocation",
    "PurchaseAllocationView",
    "PurchaseConfig",
    "PurchaseLineItem",
    "PurchaseLineItemSummaryView",
    "PurchaseLineItemView",
    "PurchaseList",
    "PurchaseListView",
    "Strategy",
    "Supplier",
    "SupplierGroupView",
    "SupplierPackage",
    "SupplierSubtotal",
    "UnknownPresetError",
    "UnpurchasableMaterialError",
    "Volume",
    "aggregate_project",
    "calculate_component",
    "load_bundled_catalog",
    "load_catalog",
    "load_project",
    "new_project",
    "optimize_purchase",
    "render_component_mixsheet",
    "render_purchase_list",
    "save_project",
]
