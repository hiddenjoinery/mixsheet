## Why

Phases 1-5 produced a complete pure-domain pipeline: catalog loader,
calculator, project aggregator, purchase optimizer, both renderers,
the project YAML loader/saver, and the Excel writer. Every piece is
callable in isolation; nothing wires them together. The Typer entry
point still has only `version` and a `calc` placeholder. A user who
installs `mixsheet` today cannot do the one thing the product
promises — get from a part description to a purchase list. This
change closes that gap and earns Phase 6 of the roadmap by delivering
the interactive wizard documented in `docs/user-flow.md`.

## What Changes

- Add a new capability `cli-wizard`: two Typer commands —
  `mixsheet new` and `mixsheet open <path>` — backed by a Rich-based
  prompt loop that mirrors the user-flow golden paths for both the
  single-component and machine project shapes. The wizard composes
  existing capabilities: dimensions/area/direct volume input → preset
  pick → calculator → aggregator (machine) → strategy comparison →
  optimizer → renderers → Excel export.
- Establish the **save-after-each-prompt** invariant: every answer is
  written through `save_project` before the next prompt fires, so the
  user can `Ctrl-C` and resume via `mixsheet open` without state loss.
- Add a `mixsheet open` resume menu (`Continue where I left off / Add
  a component / Edit a component / Recalculate purchase list / Export
  / Quit`) driven by which sections of the project file are populated
  and which catalog mismatches the loader reported.
- Wire the strategy comparison table (default on, `--no-compare` to
  skip) and the export step that produces `mixsheets.xlsx` and
  `purchase.xlsx` next to the project file (single-component) or in
  a per-project folder (machine).
- Replace the placeholder `calc` command in `src/mixsheet/cli.py`
  with the `new` and `open` commands. `version` stays.
- Add inline `?` help on every prompt: typing `?` returns the
  prompt-specific blurb without losing wizard state. The blurbs are
  short, in-flow, and reference the future topic-help system but do
  not require it.
- Handle the documented edge cases: below-minimum volume override,
  unknown preset on load, material with no purchasable package, and
  pinned preset-version drift.
- Update `docs/ROADMAP.md` to tick off Phase 6 and reconcile the
  golden-path text in `docs/user-flow.md` with the actual wizard
  behaviour where it diverges.

Non-goals:

- No `mixsheet help <topic>` long-form topic help system. Inline
  `?` blurbs are in scope; the topic registry under `docs/help/` is a
  follow-up proposal.
- No JSON project format. YAML only. The user-flow's "JSON
  optionally" note is deferred until a tooling consumer asks for it.
- No catalog cleanups (drop `material_name`, `vat_rate`,
  `description`; default-exclude `water`; rename `density` →
  `density_kg_per_l`; add `catalog_version`). The data work listed in
  `docs/user-flow.md` § "Catalog cleanup vs old implementation"
  belongs in a separate, focused proposal.
- No custom presets / supplier overrides via a user-config directory.
- No new project-file fields, no schema-version bump, no changes to
  `load_project`, `save_project`, `Project`, `Component`, or any
  other domain model. The wizard consumes existing surfaces and
  reports their warnings; spec-level model behaviour is unchanged.
- No structured logging redesign. Structlog already routes to JSON;
  the wizard owns stdout via Rich and surfaces only warnings + errors
  on stderr.
- No new export targets. `mixsheets.xlsx` + `purchase.xlsx` only;
  CSV/PDF stays out.
- No global state under `~/`. Project files are resolved relative to
  the current working directory, with an explicit `--project-dir`
  flag overriding for `mixsheet new`.

## Capabilities

### New Capabilities

- `cli-wizard`: Typer commands `mixsheet new` and
  `mixsheet open <path>` plus the Rich-driven prompt loop that
  composes the existing `domain-models` (project I/O, volume modes,
  validation), `calculator`, `project-aggregation`,
  `purchase-optimization`, `purchase-rendering`,
  `mixsheet-rendering`, and `excel-export` capabilities. The
  capability covers the prompt shapes, validation feedback, the
  strategy-comparison view, the resume menu, the
  save-after-each-prompt invariant, the inline `?` help blurbs, and
  the documented edge-case handling.

### Modified Capabilities

_None._ All existing capabilities remain unchanged at the spec level;
the wizard consumes their public surfaces.

## Impact

- New module `src/mixsheet/wizard/` with `new.py`, `open.py`,
  `prompts.py` (Rich helpers + `?`-help dispatcher),
  `comparison.py` (strategy-comparison table), `paths.py` (resolves
  project-file paths and per-shape output layouts), and
  `__init__.py`.
- `src/mixsheet/cli.py`: drop `calc`, register `new` and `open`
  commands; keep `version`.
- New tests under `tests/wizard/` driving prompts via Typer's
  `CliRunner` against an in-memory Rich console plus an integration
  test that runs `mixsheet new` end-to-end against the bundled
  catalog and asserts the project file + workbook artefacts on disk.
- `pyproject.toml`: no new core dependencies (Typer, Rich, pyyaml,
  Pydantic, structlog already present). The wizard imports
  `mixsheet.export` lazily so the `export` extra remains optional —
  if missing at the export step, the wizard surfaces the same
  install hint as the writer (`uv add mixsheet[export]`).
- `docs/ROADMAP.md`: tick off Phase 6.
- `docs/user-flow.md`: minor reconciliation only (default strategy,
  paths, exact resume-menu ordering).
- `CHANGELOG.md`: one `Added` bullet for the wizard.
