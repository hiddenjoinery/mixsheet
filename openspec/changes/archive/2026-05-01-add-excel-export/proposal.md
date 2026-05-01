## Why

Phase 4 produced a frozen `PurchaseListView` ready for display, but the
project still has no on-disk artifact. The user-flow promises two
deliverables — a per-component mix sheet for the workbench and a
project-wide purchase list for the order desk — and `xlsx` is the
preferred format on both surfaces. Without an exporter, every result
the user worked through dies inside the wizard. This change closes
that gap and earns Phase 5 of the roadmap.

## What Changes

- Add a new capability `excel-export` that writes two `.xlsx`
  workbooks per project: `purchase.xlsx` (Overview tab + alphabetical
  sheet-per-supplier) and `mixsheets.xlsx` (sheet-per-component).
- Extend the `purchase-rendering` capability with a per-material
  rolled-up view (`PurchaseListView.materials`) so the Overview tab
  can answer "what does the project need across all suppliers?"
  without the writer reaching back into the optimizer's
  `PurchaseList`. Existing fields are unchanged; this is an additive
  spec delta.
- Add a new capability `mixsheet-rendering`: pure
  `render_component_mixsheet(component_breakdown) ->
  ComponentMixSheetView` mirroring the renderer pattern with raw
  `Decimal` plus display-rounded strings, so the mix-sheet writer
  consumes one frozen view per component and applies no formatting
  itself.
- Drop the "CSV is floor; xlsx preferred" decision from
  `docs/user-flow.md` and rewrite the export decision row to make
  xlsx the single export path. The `bed.mix.csv` /
  `cross-slide.mix.csv` / `purchase.csv` examples in the same file
  flip to `mixsheets.xlsx` and `purchase.xlsx`.
- Mark `xlsxwriter` as an **optional** dependency under
  `[project.optional-dependencies] export`. The CLI imports it lazily
  inside the export command and surfaces a focused install hint when
  the extra is missing — the rest of the package stays installable
  without it.

Non-goals:

- No CLI wiring beyond the export command itself. The wizard
  capability is not in scope; the export command takes a project file
  + catalog and writes the workbooks.
- No PDF, no print-layout tuning, no conditional formatting, no
  Excel formulas. Output is data + minimal sheet structure.
- No re-shape of `PurchaseList`, `ProjectBreakdown`,
  `ComponentBreakdown`, or any catalog/project model.
- No localisation. Currency stays `€`; units stay kg / L.
- No cross-supplier marker on per-supplier sheets. The Overview's
  `Suppliers` column is the single place that signals splits.

## Capabilities

### New Capabilities

- `excel-export`: pure-write surface that consumes a
  `PurchaseListView` plus a list of `ComponentMixSheetView`s and
  produces two `.xlsx` workbooks at caller-supplied paths. Tab names
  derive from supplier/component name with id fallback and 31-char
  truncation. xlsxwriter is the only third-party dependency and is
  imported lazily.
- `mixsheet-rendering`: pure
  `render_component_mixsheet(component_breakdown) ->
  ComponentMixSheetView`. Frozen view carries header data (project,
  component, preset, volume, density, total weight) and material rows
  (raw `Decimal` + display strings) using the constants in
  `mixsheet.domain.display`.

### Modified Capabilities

- `purchase-rendering`: add an additive requirement that
  `PurchaseListView` carries a `materials` list — one entry per input
  `PurchaseLineItem` — with raw + formatted `required_kg`,
  `required_with_overage_kg`, `purchased_kg`, `waste_kg`,
  `cost_incl_vat`, plus a deterministic `suppliers` field
  (alphabetical supplier ids joined with `" + "`) for cross-supplier
  attribution.

## Impact

- New module `src/mixsheet/domain/mixsheet_renderer.py` with
  `render_component_mixsheet` and the `ComponentMixSheetView` family.
- Extended `src/mixsheet/domain/renderer.py` adding the per-material
  summary view; `mixsheet.domain.__init__` re-exports the new
  surface.
- New package `src/mixsheet/export/` with `excel.py`
  (writes both workbooks) and `__init__.py` exposing
  `write_purchase_workbook` and `write_mixsheet_workbook`.
- New tests under `tests/domain/test_mixsheet_renderer.py`,
  expanded `tests/domain/test_renderer.py` for the materials view,
  and `tests/export/test_excel.py` covering tab names, sheet
  structure, cell-format expectations, and the missing-extra error.
- `pyproject.toml`: add `xlsxwriter` under
  `[project.optional-dependencies] export`. No core dependency
  growth.
- `docs/user-flow.md`: drop the CSV-floor decision; flip the
  golden-path examples to `.xlsx` filenames; update the Decisions
  table row for export.
- `docs/ROADMAP.md`: tick off the Phase 5 Excel-export milestone.
