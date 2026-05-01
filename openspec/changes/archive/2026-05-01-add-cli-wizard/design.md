## Context

The pure domain pipeline is complete and well-specified. What is
missing is the conversational shell that turns "user with a part to
pour" into "files on disk". The user-flow (`docs/user-flow.md`) is
already detailed enough to read as a draft script — golden paths,
edge cases, even the precise `?` help blurbs. This change is
plumbing: pick a prompt library, agree on save points, decide where
files land, and accept that the wizard owns no business logic.

Existing surfaces the wizard composes:

- `mixsheet.domain` — `load_project`, `save_project`, `new_project`,
  `Project`, `Component`, `Volume` union, `PurchaseConfig`,
  `Strategy`, `ProjectLoadResult` (carries `mismatches`),
  `Catalog`, `load_bundled_catalog`.
- `mixsheet.domain.calculator` — `calculate_component`.
- `mixsheet.domain.aggregator` — `aggregate_project`.
- `mixsheet.domain.optimizer` — `optimize_purchase`,
  `UnpurchasableMaterialError`, `CatalogTooBroadError`.
- `mixsheet.domain.renderer` — `render_purchase_list`.
- `mixsheet.domain.mixsheet_renderer` — `render_component_mixsheet`.
- `mixsheet.export` — `write_purchase_workbook`,
  `write_mixsheet_workbook`, `MissingExcelExtraError`,
  `ProjectHeader`.

CLI-side dependencies (Typer, Rich) are already declared and used
for the placeholder commands, so no dependency growth.

## Goals / Non-Goals

**Goals:**

- A working `mixsheet new` and `mixsheet open` that follow
  `docs/user-flow.md` end-to-end on the bundled catalog without
  reaching for outside data.
- Save-after-each-prompt: project state on disk leads, in-memory
  state follows. No partial sessions are lost to a Ctrl-C.
- A clean boundary: the wizard module imports the domain and
  export packages and never speaks YAML, runs no math, and writes
  no formatted strings of its own.
- Testable: the prompt loop is driven by `typer.testing.CliRunner`
  feeding stdin. Every requirement in the spec corresponds to at
  least one test.
- The wizard module structure is small enough that a future
  topic-help proposal slots in without rewrite.

**Non-Goals:**

- No new domain capability. Project file format, component model,
  optimiser strategies, render rules, and export layout are frozen
  by their existing specs.
- No new CLI surface beyond `new`, `open`, and the existing
  `version`. `mixsheet help <topic>`, `mixsheet doctor`,
  `mixsheet validate`, and `mixsheet calc` are out of scope. (The
  placeholder `calc` is removed because keeping it would surface
  in `--help` and confuse users.)
- No global state or per-user config directory. `~/.mixsheet/`
  does not exist.
- No catalog hot-reload. The wizard loads the bundled catalog once
  on startup; restarting picks up YAML edits.
- No background work, no watchers, no concurrency. The wizard
  blocks on user input by design.
- No localisation. Prompts, blurbs, and error text are English.
  Chat with the user is Dutch (per project convention) but only
  for code/PR/spec authoring; runtime CLI output stays English.

## Decisions

### Decision: Two commands, not one with subcommands

`mixsheet new` and `mixsheet open <path>` are top-level Typer
commands. We rejected `mixsheet project new` / `mixsheet project
open` because the user-flow examples show the short form, the CLI
has only one noun (the project), and Typer's grouping noise
without a real domain split adds typing for no payoff.

**Why over the alternative**: A nested group (`mixsheet project
...`) is the right pattern for CLIs that manage many noun types
(`mixsheet project ...`, `mixsheet catalog ...`, `mixsheet
preset ...`). The Mix Sheet has one noun. Rejected `mixsheet`
without subcommands (a single command that branches on
`--new` / `--open`) because Typer's `--help` is much friendlier
when commands are commands.

### Decision: Save through the existing `save_project`, no batched writes

The wizard writes the full project on every mutating prompt. We
rejected an in-memory diff buffer that flushes at "save points"
because the existing `save_project` is fast (a few hundred bytes
of YAML), the file is small, and any complexity we add to batch
writes is complexity that creates resume-correctness bugs. The
file always reflects the latest answered prompt.

**Why over the alternative**: Performance is not a concern at this
scale (single-user, tens of components, kilobytes of YAML).
Resume correctness IS a concern — every batched write is a window
where a Ctrl-C loses answered state.

### Decision: Path layout — flat for `single`, folder for `machine`

`single` projects produce three sibling files
(`<slug>.yaml`, `<slug>.purchase.xlsx`,
`<slug>.mixsheets.xlsx`). `machine` projects live in a folder
(`<slug>/project.yaml`, `<slug>/purchase.xlsx`,
`<slug>/mixsheets.xlsx`). The user-flow's golden paths show this
layout; the wizard codifies it.

**Why over the alternative**: Rejected always-folder because
single-component projects (the common DIY case) end up with one
folder per pour, cluttering the projects dir. Rejected always-flat
because machine projects produce multiple mix sheets per project
and a folder is the natural grouping. We accept the inconsistency
because it matches user mental model.

### Decision: `--project-dir` is a `mixsheet new` flag, not a global option

The location of project files is a creation-time decision; once
created, `mixsheet open <path>` already takes the path. We rejected
a global `--project-dir` option because it would have to apply to
`mixsheet open`, which already has a path argument, and a path
argument plus a directory option is two ways to say the same
thing.

**Why over the alternative**: Rejected reading project-dir from an
env var (`MIXSHEET_PROJECT_DIR`) because the user-flow's
"no global state in `~/`" decision applies; the env var would
become a hidden default that users forget they set.

### Decision: Strategy comparison runs the full optimiser per strategy

The comparison table calls `optimize_purchase` once per
`Strategy` member with the same project. With three strategies
and a typical project of a few materials, the runtime is
sub-second; we accept it for correctness. We rejected estimating
the table from a single run plus a heuristic because "tied
strategies" and "minimal_waste shines on small pours" lose
meaning if the numbers are not the real ones.

**Why over the alternative**: Rejected memoising on `(project,
catalog)` across `mixsheet new` runs because the wizard is a
single-process tool; the cache would never hit a second time
within a session.

### Decision: `?` help blurbs live next to the wizard, keyed by prompt

Each prompt registers its `?` blurb as a string constant in
`mixsheet/wizard/prompts.py` keyed by a stable prompt name. The
dispatcher echoes the blurb when the user types `?` and re-runs
the prompt. We rejected loading blurbs from `docs/help/<topic>.md`
because that wires this proposal to a topic-help system that does
not exist yet.

**Why over the alternative**: Rejected hard-coding blurbs inline
with each prompt because grepping for "where is the volume
help text" should land on one obvious file. The constants module
makes future migration to a topic-help registry mechanical: each
constant becomes a topic file.

### Decision: Resume menu is computed from project state, not stored

The "Continue where I left off" entry computes its target from
the loaded project on each open. We rejected storing a
`wizard_state.next_step` field because (a) it adds project-file
schema, (b) a hand-edited project file would lie about its
state, and (c) the project's own data already answers the
question (no components → next step is component prompt; no
strategy → next step is strategy; both → re-export).

**Why over the alternative**: Computing the resume target
means the wizard works correctly on hand-edited files and on
files written by older wizard versions. A stored cursor would
need migration logic.

### Decision: Wizard catches optimiser errors, never the calculator's

`UnpurchasableMaterialError` and `CatalogTooBroadError` are
recoverable: the wizard offers excluded-materials handling or
narrowing the catalog. The calculator's `UnknownPresetError` is
not recoverable in-flow — it can only happen if a project file
references a preset id absent from the catalog, which the load
path already handles via the resume-menu unknown-preset
remediation. The wizard does not wrap calculator calls in
try/except; if a calculator error fires inside the wizard it is
a bug.

**Why over the alternative**: Rejected blanket
`except Exception` because it hides bugs. The wizard catches the
two named recoverable optimiser errors and lets everything else
propagate (with structlog logging at the root of the command).

### Decision: Output is Rich on stdout; structlog stays JSON to a file

The wizard's printable surface is Rich (tables, prompts,
markup). Structlog continues to emit JSON to the
`./projects/.logs/` rotating file (or the configured project-dir
equivalent). Stderr stays mostly silent — Rich's print routes to
stdout, and we route warnings/errors to stderr only when the
wizard cannot continue.

**Why over the alternative**: Rejected mixing structlog and Rich
on the same stream because users would see JSON intermingled with
prompts. Rejected disabling structlog inside the wizard because
operational logs (catalog load failures, file IO errors) still
matter and the JSON file is the right home.

### Decision: One Rich `Console` per command run, injected for tests

`mixsheet/cli.py` constructs a `rich.console.Console` and passes
it into the wizard entry points. Tests construct a `Console(file=...)`
pointed at a `StringIO` so assertions can read the rendered
output. We rejected reading from `cli.console` (a module-level
singleton) because tests would need monkeypatching and the
behaviour would depend on import order.

**Why over the alternative**: Rejected `capsys`/`capfd` because
Rich's terminal detection produces different output when stdout
is not a tty; an explicit injected console is the only way to
make the rendered string deterministic.

## Risks / Trade-offs

[Risk: Rich's interactive prompts (`Prompt.ask`) read from real
stdin, which makes Typer's `CliRunner.invoke(input=...)` flaky on
some platforms.] → Mitigation: the wizard's prompt layer is a thin
function `ask(prompt_name, console, input_stream, **kw)` that
reads via `console.input()` (Rich's stdin-aware reader); tests
construct the console with an explicit `file` and feed input via
`runner.invoke(..., input="...\n...\n")`. A smoke test asserts
this on Windows + macOS + Linux CI.

[Risk: Save-after-each-prompt produces N writes per session and
generates noisy filesystem timestamps.] → Mitigation: not a real
problem for the target audience; the file is small and the user
expects writes. Tests assert the count is at least N (matching
the spec) but not exactly N to leave room for refactoring.

[Risk: The strategy comparison runs the optimiser three times,
which on pathological catalogs (many packages, many materials)
could be slow enough to feel laggy.] → Mitigation: the bundled
catalog is small (< 100 packages) and the user-flow targets DIY
workshops. We add a single `Console.status("Comparing
strategies...")` spinner so the user sees activity. We do not
parallelise; threading inside a Typer command would complicate
testing without buying real performance.

[Risk: A user hand-edits the YAML between prompts and the
wizard's next save clobbers the edit.] → Mitigation: this is a
behavioural risk inherent to "save-after-each-prompt". We
document it in the export topic when help content lands. The
wizard does not detect external edits; it owns the file while
running. The "open between sessions, hand-edit between sessions"
flow remains supported.

[Risk: Removing `mixsheet calc` is a behaviour change — anyone
scripting against the placeholder breaks.] → Mitigation: the
placeholder explicitly raises Exit(0) with no real work; no
plausible script depends on it. We note the removal in
CHANGELOG under `Removed`.

[Risk: Typer's `add_completion=False` means users get no shell
completion. With two commands and one positional path that's
fine; if we add more commands we should re-enable it.] →
Mitigation: not blocking for this change; revisit when the
topic-help and `doctor` commands land.

[Risk: The export step writing inside `./projects/<slug>/`
silently overwrites prior workbooks on every re-export.] →
Mitigation: this is the documented behaviour ("Recalculate
purchase list" in the resume menu). We do not introduce
versioned filenames; the project-file YAML is the historical
record.
