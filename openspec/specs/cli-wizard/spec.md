# cli-wizard Specification

## Purpose
TBD - created by archiving change add-cli-wizard. Update Purpose after archive.
## Requirements
### Requirement: CLI command surface

The system SHALL expose two Typer commands as the wizard's entry
points: `mixsheet new` (start a new project) and `mixsheet open <path>`
(resume an existing project file). Both commands MUST run the
interactive Rich-driven wizard, MUST exit with status `0` on success,
and MUST exit with a non-zero status when the user aborts before any
project is saved. The placeholder `mixsheet calc` command MUST be
removed; `mixsheet version` MUST remain unchanged.

#### Scenario: `mixsheet --help` lists the new and open commands

- **WHEN** the user runs `mixsheet --help`
- **THEN** the help output names `new`, `open`, and `version` and does
  not name `calc`

#### Scenario: `mixsheet new` exits zero after a completed run

- **WHEN** the user completes a single-component flow end-to-end
- **THEN** the process exits with status `0` and a project file plus
  the two workbooks exist at the documented paths

#### Scenario: User aborts before saving

- **WHEN** the user sends `Ctrl-C` at the very first prompt of
  `mixsheet new`
- **THEN** the process exits with non-zero status and no project file
  is written

### Requirement: Project shape and identity prompts

`mixsheet new` SHALL ask for the project name (non-empty, trimmed) and
the project shape (`single` or `machine`) before any component prompt.
The wizard MUST construct the project via the existing `new_project`
constructor (which seeds default-excluded materials) and write it
through `save_project` as soon as the first component is captured —
the existing `Project` model requires at least one component, so the
initial save coincides with the first component's completion. The
project file path MUST resolve to `<project-dir>/<slug>.yaml` for
shape `single` and `<project-dir>/<slug>/project.yaml` for shape
`machine`, where `<project-dir>` defaults to `./projects/` and
`<slug>` is the project's id.

#### Scenario: New single-component project lands at a flat path

- **WHEN** the user names the project `Lathe bed riser`, picks
  `single`, and completes the first component prompt
- **THEN** a YAML file is written at
  `./projects/lathe-bed-riser.yaml` carrying that component before
  the next prompt fires

#### Scenario: New machine project lands in a per-project folder

- **WHEN** the user names the project `Router gantry`, picks
  `machine`, and completes the first component prompt
- **THEN** the per-project folder `./projects/router-gantry/` is
  created and `project.yaml` carrying that component is written
  inside it before the next prompt fires

#### Scenario: `--project-dir` overrides the default location

- **WHEN** the user runs `mixsheet new --project-dir ./out`
- **THEN** the project file is created under `./out/` and not under
  `./projects/`

### Requirement: Volume input modes with validation

The wizard SHALL ask each component how its volume is supplied
(`dimensions`, `area_height`, or `direct`) and prompt for the matching
fields. Numeric inputs MUST be parsed as `Decimal`. Inputs that fail
the existing model validation MUST be re-prompted with a one-line
error and a `(mixsheet help volume)` see-also pointer. A computed
volume below `Decimal("0.01")` litres MUST trigger a confirmation
prompt; declining returns to volume input, accepting proceeds.

#### Scenario: Rectangular dimensions compute and persist

- **WHEN** the user picks `dimensions` and enters `length=320`,
  `width=180`, `height=60`
- **THEN** the wizard reports `Volume per component: 0.0 L`
  (display-rounded) with a raw value matching the existing
  `DimensionsVolume.volume_l` calculation, and the component is
  written to disk before the next prompt

#### Scenario: Below-minimum volume asks for confirmation

- **WHEN** the user enters dimensions producing `0.005` L
- **THEN** the wizard prints a warning naming the threshold and asks
  `Continue anyway? [y/N]`; declining re-opens the volume prompt

#### Scenario: Non-positive dimension is rejected with a hint

- **WHEN** the user enters `length=0`
- **THEN** the wizard prints `Length must be > 0. (mixsheet help
  volume)` and re-prompts for length only

### Requirement: Preset selection and pinning

The wizard SHALL present the catalog's mix presets as a selectable
list per component, showing each preset's name, density, and
application label. The user's pick MUST persist as both `preset_id`
and `preset_version` (pinning to the catalog version at save time)
through the standard `Component` model and `save_project` write.

#### Scenario: Preset list shows density and application

- **WHEN** the wizard reaches the preset prompt for a component
- **THEN** every preset in the bundled catalog appears with its
  `density_kg_per_l` and `application` (or `description`) text on
  one line per preset

#### Scenario: Picked preset is pinned by version

- **WHEN** the user picks a preset whose catalog `version` is
  `"1.1.0"`
- **THEN** the saved component records `preset_version: "1.1.0"`

### Requirement: Machine-shape component loop

For projects of `shape: machine` the wizard SHALL repeat the
volume + preset prompts per component, asking after each component
whether to add another. Each completed component MUST be appended to
the project file via `save_project` before the "add another?" prompt.
The user MUST be able to terminate the loop only after at least one
component has been saved.

#### Scenario: Two components saved in order

- **WHEN** the user completes two components and answers `n` to "add
  another?"
- **THEN** the project file's `components` list contains both
  components in the order they were entered

#### Scenario: Cannot finish the loop with zero components

- **WHEN** the user attempts to answer `n` to "add another?" before
  finishing the first component
- **THEN** the wizard refuses and continues with the current
  component's prompts

### Requirement: Project-level purchase configuration

The wizard SHALL ask for the project-level overage (percent integer,
default `10`) once per session and offer the strategy comparison
prompt. When the user accepts the comparison, the wizard MUST render
a table that calls `optimize_purchase` once per `Strategy` member and
shows total cost, total waste, and line count per strategy with tie
markers when two rows match. Skipping the comparison (`--no-compare`
flag or declining the comparison prompt) MUST proceed to strategy
selection directly. The chosen strategy MUST be written to
`purchase.strategy` via `save_project` before optimisation.

#### Scenario: Comparison runs every strategy once

- **WHEN** the user accepts the comparison prompt
- **THEN** `optimize_purchase` is invoked exactly once per `Strategy`
  enum member and the table shows one row per strategy

#### Scenario: Tied strategies are marked

- **WHEN** two strategies produce identical total cost and total
  waste
- **THEN** the table marks both rows with a "same as <other>"
  annotation referencing the matching strategy

#### Scenario: `--no-compare` skips the comparison entirely

- **WHEN** the user runs `mixsheet new --no-compare`
- **THEN** no comparison table is shown and the wizard goes straight
  to the strategy selection prompt

### Requirement: Optimisation, rendering, and Excel export

After the user picks a strategy the wizard SHALL run the existing
`optimize_purchase`, `render_purchase_list`, and
`render_component_mixsheet` functions, then call
`write_purchase_workbook` and `write_mixsheet_workbook` to produce
`purchase.xlsx` and `mixsheets.xlsx`. The output paths MUST be
sibling to the project file for shape `single` and inside the
project folder for shape `machine`. When the optional `export` extra
is missing, the wizard MUST catch the writer's
`MissingExcelExtraError` and print the install hint without losing
the saved project file.

#### Scenario: Single-component layout writes flat sibling files

- **WHEN** the project file is `./projects/lathe-bed-riser.yaml`
- **THEN** the wizard writes
  `./projects/lathe-bed-riser.purchase.xlsx` and
  `./projects/lathe-bed-riser.mixsheets.xlsx`

#### Scenario: Machine layout writes inside the project folder

- **WHEN** the project file is `./projects/router-gantry/project.yaml`
- **THEN** the wizard writes
  `./projects/router-gantry/purchase.xlsx` and
  `./projects/router-gantry/mixsheets.xlsx`

#### Scenario: Missing export extra surfaces the install hint

- **WHEN** the export step runs in an environment without
  `xlsxwriter` installed
- **THEN** the wizard prints a message containing
  `"uv add mixsheet[export]"` and exits with non-zero status while
  the saved project file remains untouched on disk

### Requirement: `mixsheet open` resume menu

`mixsheet open <path>` SHALL load the project file via the existing
`load_project`, surface any catalog version mismatches the loader
returns, and present a resume menu offering at least: continue at
the next unanswered step, add a component, edit a component,
recalculate the purchase list, export, and quit. The "continue"
entry MUST point to the earliest step the project file does not yet
satisfy (next component for an incomplete component list, strategy
selection when components are present but no strategy is fixed,
otherwise re-export). Quitting MUST NOT modify the file.

#### Scenario: Mismatch warning before the resume menu

- **WHEN** the loaded project pins a `preset_version` that differs
  from the catalog
- **THEN** the wizard prints one mismatch line per affected
  component before showing the resume menu, naming component id,
  preset id, pinned version, and catalog version

#### Scenario: Continue jumps to the next unanswered step

- **WHEN** the project has two saved components and a default
  strategy but no exported workbooks
- **THEN** the resume menu's "Continue" entry is labelled with the
  next step (`Continue where I left off (next: purchase strategy)`
  or equivalent) and selecting it lands on that prompt

#### Scenario: Quit leaves the file untouched

- **WHEN** the user picks "Quit" from the resume menu
- **THEN** the project file's bytes on disk are unchanged compared
  to the load-time bytes

### Requirement: Save-after-each-prompt invariant

Every prompt that mutates project state SHALL persist the change via
`save_project` before the wizard advances to the next prompt. The
wizard MUST NOT hold project mutations exclusively in memory. After
saving, `updated_at` MUST reflect the just-completed write (delegated
to the existing `save_project` contract).

#### Scenario: Crash after a prompt preserves answered fields

- **WHEN** the user answers the project-name prompt and the process
  is killed before the next prompt fires
- **THEN** `mixsheet open` on the resulting file loads a project
  carrying the answered name with no further state lost

#### Scenario: Save count matches mutating prompts

- **WHEN** the user completes a single-component flow with `N`
  mutating prompts
- **THEN** `save_project` is invoked at least `N` times during the
  run

### Requirement: Inline `?` help on every prompt

The wizard SHALL accept `?` as a special input on every prompt and,
when received, print a prompt-specific blurb of at most ten lines
without advancing the wizard or modifying the project file. The
blurb MUST end with a one-line `See: mixsheet help <topic>` pointer
even when the topic-help system is not yet implemented.

#### Scenario: Asking `?` on the overage prompt prints the blurb

- **WHEN** the user types `?` at the project-overage prompt
- **THEN** the wizard prints the overage blurb (ending with
  `See: mixsheet help overage`) and re-shows the same prompt

#### Scenario: `?` does not change the file

- **WHEN** the user types `?` on any prompt
- **THEN** the project file's bytes on disk are identical before and
  after

### Requirement: Edge case handling for unpurchasable materials

The wizard SHALL handle `UnpurchasableMaterialError` from the
optimiser by surfacing a focused prompt offering: skip the material
(omit from purchase list), add it to `purchase.excluded_materials`
and re-run, or quit. Choosing "add to excluded" MUST persist the
change via `save_project` and re-run the optimiser.

#### Scenario: Add-to-excluded persists and recovers

- **WHEN** the user picks "Add to excluded materials" for material
  `custom-pigment`
- **THEN** `purchase.excluded_materials` on disk includes
  `custom-pigment` and the optimiser is re-invoked, succeeding when
  no other unpurchasable materials remain

#### Scenario: Quit leaves the project file untouched

- **WHEN** the user picks "Quit" from the unpurchasable-material
  prompt
- **THEN** the project file's bytes on disk are unchanged compared
  to the bytes immediately before the optimiser ran

### Requirement: Edge case handling for unknown presets on load

The wizard SHALL handle a project whose component references a
preset id absent from the catalog by printing one line per affected
component listing the unknown id and the available ids, then
offering to pick a replacement preset per component or quit. The
wizard MUST NOT modify the project file until the user confirms a
replacement; quitting MUST leave the file untouched.

#### Scenario: Unknown preset reports the available ids

- **WHEN** a component references `preset_id: legacy-mix` not in the
  catalog
- **THEN** the wizard prints a line naming the unknown id and a line
  listing every catalog preset id

#### Scenario: Quitting on unknown preset does not mutate the file

- **WHEN** the user picks "Quit (do not modify the file)"
- **THEN** the project file's bytes on disk are unchanged
