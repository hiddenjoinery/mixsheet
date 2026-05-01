## 1. Wizard package skeleton

- [x] 1.1 Create `src/mixsheet/wizard/__init__.py` exporting `run_new` and `run_open` entry points.
- [x] 1.2 Create `src/mixsheet/wizard/paths.py` with `resolve_new_paths(name, shape, project_dir) -> ProjectPaths` and `resolve_open_paths(project_path) -> ProjectPaths` that return the project-file path plus the two workbook paths per the flat-vs-folder layout.
- [x] 1.3 Create `src/mixsheet/wizard/prompts.py` with a `prompt(name, console, *, kind, default, validate)` helper, the `?`-help dispatcher (`HELP_BLURBS: dict[str, str]`), and explicit prompt-name constants.
- [x] 1.4 Create `src/mixsheet/wizard/comparison.py` with `build_comparison_table(project, catalog) -> StrategyComparison` invoking `optimize_purchase` once per `Strategy` member.
- [x] 1.5 Create `src/mixsheet/wizard/new.py` and `src/mixsheet/wizard/open.py` skeletons that take an injected `Console`, `Catalog`, and project paths plus an optional `--no-compare` flag.

## 2. Volume and preset prompt flows

- [x] 2.1 Implement `prompt_volume(component_id, console) -> Volume` selecting between `dimensions`, `area_height`, and `direct` and parsing each numeric input as `Decimal`.
- [x] 2.2 Surface Pydantic `ValidationError` from the volume models as one-line "<field> must be > 0. (mixsheet help volume)" re-prompts that target only the offending field.
- [x] 2.3 Add the below-minimum (`< 0.01 L`) confirmation prompt; declining returns to volume mode selection, accepting proceeds with the entered values.
- [x] 2.4 Implement `prompt_preset(catalog, console) -> tuple[str, str]` rendering one row per preset (name, density, application/description) and returning `(preset_id, preset_version)` pinned to the catalog's current version.
- [x] 2.5 Implement `prompt_component(component_id, catalog, console) -> Component` composing the volume and preset prompts plus name and quantity inputs.

## 3. `mixsheet new` flow

- [x] 3.1 Implement project name + shape prompts in `wizard/new.py`, then capture the first component (always required so `Project.components` satisfies `min_length=1`), call `new_project`, and dispatch to the machine loop below for shape `machine`.
- [x] 3.2 Resolve the project-file path via `paths.resolve_new_paths` after the shape prompt, ensure the parent directory exists, and call `save_project` immediately after the first component is captured (the model's component constraint forces the first save to coincide with that prompt).
- [x] 3.3 For `machine` shape: loop on component prompts, appending each to `project.components` and calling `save_project` after every append; refuse "add another? n" until at least one component is saved.
- [x] 3.4 Implement the project-overage prompt (integer percent → `Decimal("0.10")` style) with `?`-help and `save_project` on commit.
- [x] 3.5 Implement the strategy comparison: render `build_comparison_table` results via Rich (mark ties as "same as <other>") unless `--no-compare` is set or the user declines the comparison prompt.
- [x] 3.6 Implement the strategy selection prompt; persist via `save_project` before optimisation.
- [x] 3.7 Run `optimize_purchase`, `render_purchase_list`, and `render_component_mixsheet` per component; render the resulting tables to the console for at-a-glance confirmation.
- [x] 3.8 Call `write_purchase_workbook` and `write_mixsheet_workbook` with the resolved workbook paths; catch `MissingExcelExtraError` and print the install hint without leaving partial files behind.

## 4. `mixsheet open` flow

- [x] 4.1 Implement `wizard/open.py` calling `load_project(path, catalog)` and printing one line per `CatalogVersionMismatch` with component id, preset id, pinned version, and catalog version.
- [x] 4.2 Implement the unknown-preset remediation: when `load_project` raises a project file referencing an absent preset, print available preset ids, offer per-component pick or quit, and only call `save_project` after the user confirms a replacement.
- [x] 4.3 Compute the resume target from project state (no components → component prompt; components but default strategy and no workbooks → strategy prompt; otherwise re-export).
- [x] 4.4 Implement the resume menu (`Continue / Add a component / Edit a component / Recalculate purchase list / Export / Quit`) with selections that delegate into the same prompt helpers used by `mixsheet new`.
- [x] 4.5 Handle `UnpurchasableMaterialError` from the optimiser: prompt for skip / add-to-excluded / quit; on add-to-excluded, mutate `project.purchase.excluded_materials`, save, and re-run the optimiser.
- [x] 4.6 Ensure quitting from any remediation prompt leaves the project file's bytes on disk unchanged compared to the load-time bytes (assert via tests).

## 5. CLI wiring

- [x] 5.1 In `src/mixsheet/cli.py`, register `mixsheet new` (Typer command) with options `--name/-n`, `--shape`, `--project-dir`, and `--no-compare`; preserve interactive prompts when options are absent.
- [x] 5.2 Register `mixsheet open <path>` with a single positional path argument and a `--no-compare` option.
- [x] 5.3 Remove the placeholder `calc` command; keep `version`.
- [x] 5.4 Construct one `Console` per command invocation and inject it into the wizard entry points; route `MissingExcelExtraError` (and any uncaught domain error) through Rich on stdout while letting structlog log to its JSON file.

## 6. Tests — prompt helpers

- [x] 6.1 Add `tests/wizard/__init__.py`.
- [x] 6.2 Test `prompt_volume` against each mode using `Console(file=StringIO(), force_terminal=False)` and a fed-input pattern; assert `Decimal` output values.
- [x] 6.3 Test the below-minimum confirmation: declining loops back, accepting proceeds.
- [x] 6.4 Test `?`-help on volume, overage, and strategy prompts; assert blurb is printed and the prompt re-asks without state mutation.
- [x] 6.5 Test `prompt_preset` echoes density and application text and pins `preset_version` to the catalog's current version.

## 7. Tests — `mixsheet new`

- [x] 7.1 Add an integration test driving `mixsheet new` end-to-end via `CliRunner` against the bundled catalog for a single-component flow; assert YAML file + both workbooks exist at the flat-layout paths.
- [x] 7.2 Add an integration test for the `machine` shape covering two components; assert folder layout, two-component YAML, and both workbooks inside the project folder.
- [x] 7.3 Test save-after-each-prompt by killing the runner mid-flow (send EOF after answering the project-name prompt); assert the file on disk loads via `load_project` and carries the answered name.
- [x] 7.4 Test the `--no-compare` flag suppresses the comparison table and lands on the strategy prompt directly.
- [x] 7.5 Test the strategy comparison invokes `optimize_purchase` once per `Strategy` member by patching the optimiser with a counting wrapper.
- [x] 7.6 Test tied strategies are marked with the "same as <other>" annotation by feeding a project where two strategies produce identical totals.
- [x] 7.7 Test missing `xlsxwriter`: monkeypatch the export module to raise `MissingExcelExtraError`; assert the install hint is printed, the YAML stays on disk, and the process exits non-zero.

## 8. Tests — `mixsheet open`

- [x] 8.1 Test the resume menu's "Continue" target is the next unanswered step for projects in three states (zero components, components-without-strategy, fully-answered).
- [x] 8.2 Test `CatalogVersionMismatch` lines are printed before the resume menu naming the component, preset, pinned and catalog versions.
- [x] 8.3 Test the unknown-preset remediation: load a project referencing a nonexistent preset, assert the available-ids line, pick a replacement, assert `save_project` runs once and the new preset is persisted.
- [x] 8.4 Test "Quit" from the unknown-preset remediation leaves the project file's bytes unchanged.
- [x] 8.5 Test `UnpurchasableMaterialError` remediation: simulate an unpurchasable material, pick "Add to excluded materials", assert `excluded_materials` includes the id and the optimiser is re-invoked successfully.
- [x] 8.6 Test "Quit" from the unpurchasable-material prompt leaves the project file's bytes unchanged.

## 9. Documentation

- [x] 9.1 Tick off Phase 6 in `docs/ROADMAP.md`.
- [x] 9.2 Reconcile `docs/user-flow.md` golden paths with the actual wizard output (default strategy text, exact resume-menu order, the flat-vs-folder path layout).
- [x] 9.3 Add a one-line `Added` entry to `CHANGELOG.md` under `[Unreleased]` ("Interactive wizard: `mixsheet new` and `mixsheet open` commands").
- [x] 9.4 Add a one-line `Removed` entry to `CHANGELOG.md` under `[Unreleased]` ("Placeholder `mixsheet calc` command").

## 10. Validation

- [x] 10.1 Run `uv run ruff check --fix` and `uv run ruff format` on the touched files.
- [x] 10.2 Run `uv run pyright` and resolve any type errors.
- [x] 10.3 Run `uv run pytest` and confirm wizard tests pass alongside the existing suite.
- [x] 10.4 Run a real `uv run mixsheet new` against the bundled catalog in a scratch directory; eyeball the prompts, verify both workbooks open in Excel.
- [x] 10.5 Run `openspec validate add-cli-wizard` and resolve any warnings.
