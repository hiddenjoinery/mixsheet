## 1. Renderer extension — per-material summary

- [x] 1.1 Add frozen `PurchaseLineItemSummaryView` model in `src/mixsheet/domain/renderer.py` with `material_id`, `material_name`, raw + formatted `required_kg`, `required_with_overage_kg`, `purchased_kg`, `waste_kg`, `cost_incl_vat`, and a `suppliers: str` field.
- [x] 1.2 Add a `materials: list[PurchaseLineItemSummaryView]` field to `PurchaseListView` (preserve existing fields untouched).
- [x] 1.3 Implement a private `_summary_view(line_item)` that echoes the parent `PurchaseLineItem`'s raw values, applies the existing `_format_quantity` / `_format_price` helpers, and joins the deduplicated supplier ids alphabetically with `" + "`.
- [x] 1.4 Populate `PurchaseListView.materials` inside `render_purchase_list`, in input `line_items` order; verify the empty-list case returns `[]`.
- [x] 1.5 Re-export `PurchaseLineItemSummaryView` from `src/mixsheet/domain/__init__.py`.

## 2. Renderer tests for the materials summary

- [x] 2.1 Add `TestMaterialsSummary` to `tests/domain/test_renderer.py` covering: length matches input, single-supplier `suppliers == "acme"`, cross-supplier `suppliers == "acme + bcs"` (sorted, joined).
- [x] 2.2 Add tests for raw-vs-formatted parity on the summary view (`Decimal("9.6")` → `"9.6"`, `Decimal("36")` cost → `"€ 36.00"`).
- [x] 2.3 Add a test that confirms `materials == []` for an empty input.
- [x] 2.4 Confirm existing renderer tests still pass unchanged.

## 3. Mix-sheet renderer module

- [x] 3.1 Create `src/mixsheet/domain/mixsheet_renderer.py` with module docstring and lazy imports following the renderer.py pattern.
- [x] 3.2 Add a frozen `MixSheetMaterialRow` model (`material_id`, `material_name`, raw + formatted `weight_per_component_kg`, `weight_kg`).
- [x] 3.3 Add a frozen `ComponentMixSheetView` model with `component_id`, `component_name`, `preset_id`, `preset_name`, raw + formatted `density_kg_per_l` (two-decimal display), `quantity` (int), raw + formatted `volume_per_component_l`, `net_volume_l`, `weight_per_component_kg`, `total_weight_kg`, and `materials: list[MixSheetMaterialRow]`.
- [x] 3.4 Add a private `_format_density(value)` that quantises to two decimals half-up.
- [x] 3.5 Implement `render_component_mixsheet(component_breakdown) -> ComponentMixSheetView` that echoes raw fields, applies `_format_quantity` per cell, and walks `component_breakdown.materials` in order to build `MixSheetMaterialRow`s.
- [x] 3.6 Re-export `render_component_mixsheet`, `ComponentMixSheetView`, and `MixSheetMaterialRow` from `src/mixsheet/domain/__init__.py`.

## 4. Mix-sheet renderer tests

- [x] 4.1 Create `tests/domain/test_mixsheet_renderer.py`.
- [x] 4.2 Test the frozen-result, single-component path (header echoed, materials populated).
- [x] 4.3 Test material-order preservation and per-row raw + display values.
- [x] 4.4 Test threshold behaviour on volume and weight cells (9.6 → `"9.6"`, 124 → `"124"`).
- [x] 4.5 Test density formats to two decimals (`Decimal("1.91")` → `"1.91"`, `Decimal("2")` → `"2.00"`).
- [x] 4.6 Test that the total weight is echoed unmodified at full precision and its display follows the threshold rule.
- [x] 4.7 Test reproducibility (two calls with equal input return equal views) and input non-mutation.

## 5. Excel writer module skeleton

- [x] 5.1 Create `src/mixsheet/export/__init__.py` re-exporting `write_purchase_workbook` and `write_mixsheet_workbook`.
- [x] 5.2 Create `src/mixsheet/export/excel.py` with module docstring describing the no-domain-calls boundary and lazy `xlsxwriter` import.
- [x] 5.3 Define a frozen `ProjectHeader` Pydantic model carrying the run-config strings the writers stamp on each workbook (project name, generation date, strategy, overage display).
- [x] 5.4 Add a `MissingExcelExtraError(ImportError)` whose message names `"uv add mixsheet[export]"`.
- [x] 5.5 Add private helpers: `_safe_tab_name(name, fallback_id, used: set[str]) -> str` (sanitise forbidden chars, truncate to 31, deterministic `~N` suffix on collision); `_quantity_format(value)` returning `"0.0"` or `"0"`; constant `PRICE_FORMAT = "€ #,##0.00"`.

## 6. Excel writer — purchase workbook

- [x] 6.1 Implement `write_purchase_workbook(view, project_header, output_path)` with a lazy `xlsxwriter` import that raises `MissingExcelExtraError` on `ImportError`.
- [x] 6.2 Write the `Overview` sheet: header block (project name, strategy, overage, generation date), per-material table (one row per `view.materials` entry with columns material, required, purchased, waste, suppliers, cost), per-supplier table (one row per `view.suppliers` entry with supplier_id, item_count, subtotal), grand totals.
- [x] 6.3 Write one supplier sheet per `view.suppliers` entry in alphabetical order with header row, material/package/count/€-each/€-row columns sourced from the supplier group's `line_items`, and a subtotal row.
- [x] 6.4 Apply per-cell number formats: `_quantity_format(raw)` for quantity cells, `PRICE_FORMAT` for price cells; supplier-id and material-name cells stay text.
- [x] 6.5 Write the raw `Decimal` (cast to `float` only at xlsxwriter boundary, never to formatted strings) so spreadsheets store native numbers.
- [x] 6.6 Handle the empty-view case: emit an Overview sheet with totals = 0 and no supplier sheets.

## 7. Excel writer — mix-sheet workbook

- [x] 7.1 Implement `write_mixsheet_workbook(views, project_header, output_path)` with the same lazy-import + missing-extra contract.
- [x] 7.2 For each view, create a sheet named after `_safe_tab_name(view.component_name, view.component_id, used)` containing the header block (project, component, preset name + version, density, quantity, volume per component, net volume, weight per component, total weight) and the materials table.
- [x] 7.3 Apply per-cell number formats consistent with the purchase writer; density uses a `"0.00"` format (two decimals).
- [x] 7.4 Handle the empty list (no views) by raising `ValueError("write_mixsheet_workbook requires at least one component view")`.

## 8. Excel writer tests

- [x] 8.1 Add `tests/export/__init__.py` and `tests/export/test_excel.py`.
- [x] 8.2 Test `_safe_tab_name`: long-name truncation to 31 chars, forbidden-char sanitisation, deterministic `~N` collision suffix.
- [x] 8.3 Test `write_purchase_workbook` writes a file at the requested path; reopen with `openpyxl` and assert sheet names (`Overview` first, then suppliers alphabetical), row counts, and selected cell values + number formats.
- [x] 8.4 Test the cross-supplier path: Overview's `Suppliers` cell reads `"acme + beta"`; per-supplier sheets carry only their slice with no marker.
- [x] 8.5 Test the empty-view path produces a workbook with one Overview sheet and zero supplier sheets.
- [x] 8.6 Test `write_mixsheet_workbook` writes one sheet per component in input order with correct header block and material rows.
- [x] 8.7 Test the missing-extra path: monkeypatch `sys.modules["xlsxwriter"]` to `None` (or use `importlib` machinery) and assert `MissingExcelExtraError` with the install hint message.
- [x] 8.8 Test reproducibility: two consecutive writes produce workbooks whose parsed-cell content is identical.

## 9. Optional dependency wiring

- [x] 9.1 Add `[project.optional-dependencies] export = ["xlsxwriter>=3.2,<4"]` to `pyproject.toml`.
- [x] 9.2 Add `openpyxl` as a dev/test dependency for assertion-by-parse in the writer tests.
- [x] 9.3 Run `uv lock` and confirm the lockfile is updated cleanly.
- [x] 9.4 Verify `uv sync --no-extra export` followed by `uv run python -c "import mixsheet.export"` succeeds (lazy imports, no top-level xlsxwriter import).

## 10. Documentation

- [x] 10.1 Update `docs/user-flow.md`: in the Decisions table, replace the "Export format" row with a one-line decision pinning `.xlsx` as the only export path; remove the "CSV is floor" wording.
- [x] 10.2 Update the golden-path examples in `docs/user-flow.md` so the trailing "Project saved" blocks list `mixsheets.xlsx` and `purchase.xlsx` instead of `bed.mix.csv` / `cross-slide.mix.csv` / `purchase.csv`.
- [x] 10.3 Tick off the Phase 5 Excel-export milestone in `docs/ROADMAP.md`.
- [x] 10.4 Add a one-line entry to the appropriate CHANGELOG section under `[Unreleased]` (Added: Excel export of purchase list and mix sheets via optional `export` extra).

## 11. Validation

- [x] 11.1 Run `uv run ruff check --fix` and `uv run ruff format` on the touched files.
- [x] 11.2 Run `uv run pyright` and resolve any type errors (including the lazy-import boundary).
- [x] 11.3 Run `uv run pytest` and confirm all renderer, mix-sheet renderer, and Excel writer tests pass alongside the existing suite.
- [x] 11.4 Run `openspec validate add-excel-export` and resolve any warnings.
