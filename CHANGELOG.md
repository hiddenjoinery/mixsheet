# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial project scaffold: src-layout Python package, Typer CLI entry point, OpenSpec workspace, pre-commit hooks, and pytest harness.
- User flow documentation (`docs/user-flow.md`): project model, volume input modes, single project-level overage, strategy comparison, resumable wizard, help and discoverability layers, catalog cleanup vs old implementation.
- Domain core (`mixsheet.domain`): Pydantic v2 models for catalog (`Material`, `MixPreset`, `Supplier`, `SupplierPackage`), project (`Project`, `Component`, discriminated `Volume` union, `PurchaseConfig`), `Strategy` enum, fail-fast YAML catalog loader (`yaml.safe_load`-based), project file load/save with catalog-version mismatch detection, default-excluded materials seed, bundled catalog (`mixsheet.data/presets.yaml`, `suppliers.yaml`) and display-precision constants.
- Calculator (`mixsheet.domain.calculator`): pure `calculate_component(component, catalog) -> ComponentBreakdown` with full-precision `Decimal` weights, alphabetically ordered material rows, denormalised `material_name`, and a typed `UnknownPresetError` for missing preset ids.
- Pure project aggregator: per-component, per-material, and project-level totals with source attribution.
- Purchase optimizer (`mixsheet.domain.optimizer`): pure `optimize_purchase(breakdown, catalog, *, strategy, overage_pct, excluded_materials) -> PurchaseList` with multi-package and cross-supplier allocations, three strategies (`cheapest`, `minimal_waste`, `bulk_value`), overage applied before package selection, supplier subtotals, deterministic tie-breaking, `UnpurchasableMaterialError` for missing packages, and `CatalogTooBroadError` as a defensive search-space guard.
- Excel export of purchase list and mix sheets via optional `export` extra (`mixsheet.export`): pure `write_purchase_workbook` and `write_mixsheet_workbook` writers, per-component mix-sheet renderer (`render_component_mixsheet`), per-material rolled-up `PurchaseListView.materials` for the Overview tab, lazy `xlsxwriter` import with focused install hint.
