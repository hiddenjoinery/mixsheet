## Context

`PurchaseListView` already groups the optimizer's output by supplier
and pre-formats every cell at full precision. The next surface the
user actually touches is on disk: a workbook they open at the order
desk and another they pin to a clipboard at the workbench. Both are
`.xlsx` per the user-flow's preference; `xlsxwriter` is the canonical
Python writer for one-shot workbooks (no streaming, no formulas).

Per-component mix sheets follow the same display-rounding rules as
the purchase list (`mixsheet.domain.display`), but the source data is
a `ComponentBreakdown`, not a `PurchaseList`. To keep the writer dumb,
the renderer pattern repeats: a pure `mixsheet-rendering` capability
projects each `ComponentBreakdown` onto a `ComponentMixSheetView` with
raw `Decimal` plus formatted strings.

## Goals / Non-Goals

**Goals:**

- Two `.xlsx` workbooks per project, written by a pure-write surface
  that consumes frozen view models — no domain calls inside the
  writer.
- Order-desk-first layout for `purchase.xlsx`: an Overview tab plus
  one tab per supplier with the columns a user types into a webshop
  (`material`, `package`, `count`, `€ each`, `€ row`).
- Workbench-first layout for `mixsheets.xlsx`: one tab per component
  with header (project, component, preset, volume, density, total
  weight) and a single material table.
- xlsxwriter as an opt-in extra so the core CLI installs without it
  and surfaces a clear hint when the export command is invoked
  without the extra.
- Deterministic file output: identical input ⇒ byte-stable workbook
  modulo timestamps that xlsxwriter writes by default. We will pin
  metadata where xlsxwriter exposes a knob to keep tests workable.

**Non-Goals:**

- No CSV path. The "CSV is floor" decision in `docs/user-flow.md` is
  retracted in this change.
- No formulas, no conditional formatting, no charts, no images.
  Number formats are applied per cell to support raw `Decimal`
  values; that is the only formatting concern.
- No Rich/Typer wiring. The export functions take `pathlib.Path`
  inputs; the wizard capability glues things together later.
- No PDF, no print-layout tuning. Page setup is whatever xlsxwriter's
  defaults are.
- No localisation. `€` and SI units only.
- No `excel-export` knowledge of the optimizer or aggregator. The
  writer takes views and a project header, period.

## Decisions

### Decision: One workbook for purchase, one workbook for mix sheets

The two artifacts have different audiences and different lifecycles.
The purchase workbook lives at the order desk for the duration of
ordering; mix sheets live at the workbench during the pour. Bundling
them into one file forces the user to keep flipping past
not-relevant tabs.

**Why over the alternative**: rejected one combined `project.xlsx`
because the order-desk and workbench flows are physically different
sessions; rejected per-component mix-sheet workbooks because that
multiplies file count for machine projects without benefit (the user
opens one workbook and tabs between components).

### Decision: Renderer extension carries the per-material rolled-up view

`PurchaseListView` already fans out to per-supplier rows. Adding a
parallel `materials: list[PurchaseLineItemSummaryView]` with one
entry per parent `PurchaseLineItem` keeps the writer single-input
and gives the future Rich CLI the same rolled-up table for free.

**Why over the alternative**: rejected having the writer take both
`PurchaseList` and `PurchaseListView` because that re-couples the
writer to the optimizer model and duplicates the formatting
contract. Rejected reconstructing the rolled-up view from supplier
groups inside the writer because that pushes logic out of the
domain.

### Decision: New capability `mixsheet-rendering`, not an extension of `purchase-rendering`

Mix sheets render a `ComponentBreakdown`; purchase rendering renders
a `PurchaseList`. They share constants (display.py) but no source
type, no row shape, and no consumer. Bundling them into one
capability would create a name that reads "rendering" without
boundary.

**Why over the alternative**: rejected a single `display-rendering`
capability because the responsibilities don't compose. The two
renderers stay sibling capabilities under the same domain layer.

### Decision: `xlsxwriter` is an optional extra, imported lazily

The Mix Sheet is a CLI; many users may run only `mixsheet new` and
the wizard without ever exporting. Adding xlsxwriter to the core
dependency tree pulls C extensions onto every install. The lazy
import + clear error message keeps the install slim and the failure
mode obvious.

**Why over the alternative**: rejected a hard dependency because the
charter calls out "simplicity" as a design principle and pulling C
deps for a feature most flows touch occasionally violates that.

### Decision: Tab names use the human name, fall back to id, truncate to 31 chars

Excel limits sheet names to 31 characters and forbids `[ ] : * ? / \`.
The renderer's view models carry both id and name; the writer picks
the name (more readable at the order desk), falls back to id when the
name is empty, sanitises the forbidden characters to `_`, and
truncates to 31 chars with a deterministic `~N` suffix when two
truncated names would collide.

**Why over the alternative**: rejected using ids verbatim because
machine-style ids ("acme-cement") read worse on a tab than a name
("Acme Materials"). Rejected forbidding long names because the
catalog is user-extendable YAML and we cannot police it upstream.

### Decision: Per-material `suppliers` field is a sorted, joined string

`PurchaseLineItemSummaryView.suppliers` is a `str` like `"acme"` or
`"acme + beta"`. The renderer sorts the supplier ids alphabetically
and joins with `" + "`. The Overview tab writes this string straight
into a cell; the writer never decides supplier strings.

**Why over the alternative**: rejected emitting a list of supplier
ids because the writer would have to format them — that is display
logic and belongs in the renderer. Rejected ad-hoc separators
because Excel users skim columns; one consistent separator wins.

### Decision: Per-cell number formats over per-column

Excel cell formats apply per cell. The renderer already decides
per-cell whether a quantity is at or above the threshold, so the
writer mirrors that and applies `"0.0"` or `"0"` per cell. Prices
always use `"€ #,##0.00"`. Supplier strings are plain text.

**Why over the alternative**: rejected per-column formats because
the user-flow examples show 9.6 kg sitting next to 124 kg in the
same column with different precision. Per-column would either round
9.6 to 10 (loses meaning) or show 124.0 (visual noise).

### Decision: Writer signature takes paths and views, never opens files itself for reads

`write_purchase_workbook(view: PurchaseListView, project_header:
ProjectHeader, output_path: Path) -> None`

`write_mixsheet_workbook(views: list[ComponentMixSheetView],
project_header: ProjectHeader, output_path: Path) -> None`

The writer never reads files, never reaches into the catalog. The
caller (later: the wizard capability) owns the project I/O and
hands views in.

## Risks / Trade-offs

[Risk: xlsxwriter version drift produces byte-different workbooks
across CI runs even with identical inputs.] → Mitigation: tests open
the produced workbook with openpyxl (also a test-only dep) and
assert against parsed cell values, not raw bytes. We pin xlsxwriter
to a minor range in the optional-dependencies block.

[Risk: A user with 30+ suppliers per project produces an unwieldy
tab strip.] → Mitigation: not a real workload for the target
audience (DIY workshop, typical 1-5 suppliers). The 31-char tab name
limit does the rest. We document this in the export topic when help
content lands.

[Risk: The "drop CSV is floor" decision is a docs change visible in
diffs but easy to miss.] → Mitigation: the change touches the
Decisions table row plus the golden-path examples in
`docs/user-flow.md` in the same PR. The proposal's Impact section
calls it out so reviewers see it without diff-spelunking.

[Risk: Bringing xlsxwriter in lazily means import errors only show
up at command time, not install time.] → Mitigation: the export
command catches `ImportError` from the lazy import and prints
`Install with 'uv add mixsheet[export]' to enable Excel export.`
A unit test asserts that error message.

[Risk: A `ComponentMixSheetView` that mirrors `ComponentBreakdown`
risks being a near-1:1 wrapper.] → Mitigation: the view exists to
carry the formatted strings the writer writes. If a future change
strips formatting from breakdowns, the view stays the boundary —
the writer never reaches into raw breakdowns.
