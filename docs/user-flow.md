# User flow — The Mix Sheet

How a user gets from "I need to pour something" to a printed mix sheet
and a purchase list. Drives the OpenSpec capability proposals; not an
implementation plan.

## Audience and assumptions

A DIY builder or hobby machinist sitting at a laptop, terminal open, with
a part to cast (machine base, tooling plate, frame). They know
dimensions or volume; they pick a mix preset; they want to know what to
buy and what it will cost. Network access is optional — catalogs ship
with the package.

## Core concept: the project

Every calculation lives in a **project file** on disk. A project is the
unit of work and the unit of resumption.

A project is one of two shapes:

| Shape | When | Example |
|-------|------|---------|
| **Single-component** | One part, one pour | "Lathe bed riser, 1 piece" |
| **Machine** | Multiple parts under one name | "Router gantry: bed + cross slide + Z column" |

Both shapes use the same file format. A single-component project is
simply a machine project with one component. The wizard renders them
differently, the data does not differ.

Projects are stored as YAML by default (human-readable, hand-editable),
JSON optionally (for tooling). Either can be exported to CSV for use
away from the terminal — at the workbench or the order desk.

### Project file (YAML, normative example)

```yaml
schema_version: 1
project:
  id: router-gantry-2026-05
  name: Router gantry
  shape: machine            # or: single
  created_at: 2026-05-01T14:22:00Z
  updated_at: 2026-05-01T15:08:00Z

components:
  - id: bed
    name: Machine bed
    quantity: 1
    volume:
      mode: dimensions       # dimensions | area_height | direct
      length_mm: 800
      width_mm: 400
      height_mm: 120
      # derived: volume_l: 38.4
    preset_id: epoxy-mix
    preset_version: 1.1.0       # pinned at save time

  - id: cross-slide
    name: Cross slide
    quantity: 1
    volume:
      mode: area_height
      area_mm2: 240000
      height_mm: 80
      # derived: volume_l: 19.2
    preset_id: gantry-beam-dynamic-fill
    preset_version: 1.0.0

purchase:
  overage_pct: 0.10             # 10% extra applied project-wide
  strategy: cheapest            # cheapest | bulk_value | minimal_waste
  excluded_materials: [water]   # user-supplied, do not order
```

The `derived:` comment lines are not stored — they are recomputed each
time the project is loaded. The file holds inputs only; outputs come
from calculation.

## Overage — single project-level setting

One overage percentage applies to the whole project. It covers the
combined uncertainty: mixing losses, supplier rounding, dropped bags,
margin for a re-pour. The user does not have to model each loss
separately — one number, one place to tune it.

| Setting | Scope | Effect |
|---------|-------|--------|
| `purchase.overage_pct` | Project-wide | Increases purchase demand beyond the mix-sheet requirement. The mix sheet shows what you **need to pour**; the purchase list buys for `required × (1 + overage_pct)`. |

Order of operations:

```
component.volume × density × proportion
  → material.required_kg per component   (mix sheet shows this)

Σ required_kg across all components
  × (1 + purchase.overage_pct)
  → project.purchase_demand_kg            (optimizer sees this)
```

Default: 10%. Set to 0% for a precise calculation; raise it for risky
pours or when restocking anyway.

## Volume input modes

A component can supply its volume in three ways:

1. **Direct volume** — user knows litres or mm³ already. Example:
   "12.5 L" or "12,500,000 mm³". Internal store: litres (`Decimal`).
2. **Area × height** — for parts shaped from a 2D footprint extruded
   vertically. Example: "240,000 mm² area × 80 mm height".
3. **Length × width × height** — straight rectangular prisms.
   Example: "800 × 400 × 120 mm".

The wizard asks the user which mode and validates inputs:

- All dimensions > 0
- Computed volume ≥ 0.01 L (smaller pours are not the target use case;
  warn but allow override)
- `quantity ≥ 1`

## Golden path — single-component project

```
$ mixsheet new

? Project name: Lathe bed riser
? Project shape: › Single component
                   Machine (multiple components)

— Project saved as ./projects/lathe-bed-riser.yaml —

? Component name: riser
? How do you know the volume?
  › Dimensions (length × width × height)
    Area × height
    Direct (litres or mm³)

? Length (mm): 320
? Width (mm):  180
? Height (mm): 60

  Volume per component: 3.46 L
  Quantity:             1
  Net volume:           3.46 L

? Mix preset:
  › Epoxy granite (1.91 kg/L) — Machine bases, bed castings
    Lightweight gantry fill (0.88 kg/L) — Gantry beams, low mass
    Ultra-High Performance Concrete (2.78 kg/L) — Load-bearing parts
    Pure epoxy (1.09 kg/L) — Thin pours, < 0.5 L

— Mix sheet computed —

  Riser — Epoxy granite — 1 piece — 3.46 L → 6.30 kg

  Material              Required
  Aeropor light agg.    0.50 kg
  Durigid 0-1 mm        1.74 kg
  Durigid 1-3 mm        1.87 kg
  Durigid 3-6 mm        1.37 kg
  Epoxy resin           0.62 kg
  Hardener GL2          0.19 kg
                        ─────────
                        6.30 kg

? Project overage (% extra applied to purchase): 10
? Strategy comparison: ‹y/N› y

— Comparing strategies on this purchase —

  Strategy        Total cost   Total waste   Lines
  cheapest        € 158.40     21.4 kg       6
  bulk_value      € 412.20     65.1 kg       6   (-/+ better unit price)
  minimal_waste   € 174.80      4.2 kg       6

? Choose strategy:
  › cheapest
    bulk_value
    minimal_waste

— Purchase list (cheapest) —

  Material         Required    Buy            Waste     Cost
  Aeropor          0.55 kg     1× 21 kg bag   20.45 kg  € 84.10
  Durigid 0-1      1.91 kg     1× 5 kg bag    3.09 kg   € 17.40
  Durigid 1-3      2.06 kg     1× 5 kg bag    2.94 kg   € 17.40
  Durigid 3-6      1.51 kg     1× 5 kg bag    3.49 kg   € 17.40
  Epoxy resin      0.68 kg     1× 2.5 kg can  1.82 kg   € 43.11
  Hardener GL2     0.20 kg     1× 0.75 kg     0.55 kg   € 24.38
                                                        ─────────
                                              31.4 kg   € 203.79

— Project saved —

  Mix sheet:     ./projects/lathe-bed-riser.mixsheets.xlsx
  Purchase list: ./projects/lathe-bed-riser.purchase.xlsx
  Project file:  ./projects/lathe-bed-riser.yaml
```

## Golden path — machine project

The flow is the same but loops on components until the user signals
"done":

```
$ mixsheet new
? Project shape: Machine
? Project name: Router gantry

— add component 1 —
  ... (name, volume, preset as above) ...
? Add another component? ‹Y/n› y

— add component 2 —
  ... ...
? Add another component? ‹Y/n› n

— Aggregated totals —

  Component       Preset            Volume    Required kg
  Machine bed     Epoxy granite     38.4 L     73.3 kg
  Cross slide     Gantry fill       19.2 L     16.9 kg
                                    ────────   ─────────
                                    57.6 L     90.2 kg

  Material aggregate (across all presets):
    Aeropor          11.1 kg
    Durigid 0-1      20.3 kg
    Durigid 1-3      26.3 kg
    ...

? Project overage:    10
? Strategy:           cheapest
? Show comparison?    y
... (same comparison + purchase list as single-component, but combined) ...

— Project saved —
  Mix sheets:    ./projects/router-gantry/mixsheets.xlsx
  Purchase list: ./projects/router-gantry/purchase.xlsx
  Project file:  ./projects/router-gantry/project.yaml
```

For machines: one folder per project. One mix sheet per component, one
combined purchase list for the project.

## Resuming and editing

The project file is the single source of truth. The wizard never holds
exclusive state — every prompt's answer is written to disk before the
next prompt.

```
$ mixsheet open ./projects/router-gantry/project.yaml

— Loaded: Router gantry (machine, 2 components) —

? What now?
  › Continue where I left off (next: purchase strategy)
    Add a component
    Edit a component
    Recalculate purchase list
    Export
    Quit
```

Editing a component re-prompts only that component's fields,
pre-filling existing values. Recalculating purchase list re-runs the
optimizer with current settings.

A user can also hand-edit the YAML and run `mixsheet open` again — the
loader validates and reports issues.

## Strategy comparison

The user always sees the impact of strategy choice. The comparison
table is shown by default before the purchase list step (skippable
with `--no-compare`).

| Strategy | Picks per material |
|----------|-------------------|
| `cheapest` | Combination with lowest total cost (waste as tiebreaker) |
| `bulk_value` | Combination with lowest €/kg (cost as tiebreaker) |
| `minimal_waste` | Combination with least leftover (cost as tiebreaker) |

The comparison reveals tradeoffs: `bulk_value` often costs more upfront
but leaves you with stock for the next project; `minimal_waste` shines
on small pours where a 25 kg bag would be 90% waste.

## Edge cases

### Empty or below-minimum volume

```
? Length (mm): 50
? Width (mm):  20
? Height (mm): 5

  Computed volume: 0.005 L

  ! Below minimum useful volume (0.01 L). Are you sure?
? Continue anyway? ‹y/N›
```

If yes, calculation proceeds. If no, return to volume input.

### Mix preset removed from catalog

The user opens an old project that references `preset_id: legacy-mix`
no longer in the catalog.

```
$ mixsheet open ./old-project.yaml

  ! Component "bed" references unknown preset "legacy-mix".
    Available presets: epoxy-mix, gantry-beam-dynamic-fill, uhpc-mix,
    pure-epoxy-low-volume

? Pick a replacement preset, or quit:
  › Quit (do not modify the file)
    epoxy-mix
    ...
```

The file is not modified until the user chooses. Quit leaves the
project file untouched.

### Material has no purchasable package

A material is in a preset but no supplier in the catalog sells it
(e.g., user-supplied additive). The optimizer surfaces this:

```
  ! No package available for material "custom-pigment".
    Add the material to your purchase list manually, or add it to
    `excluded_materials` in the project file.

? How to handle?
  › Skip this material (omit from purchase list)
    Add to excluded_materials and remember the choice
    Quit
```

Excluded materials are listed at the bottom of the mix sheet so the
user remembers to source them separately.

### Strategy ties

Two strategies might produce the same outcome (small project, single
package per material). The comparison table marks them:

```
  Strategy        Total cost   Total waste
  cheapest        € 158.40     21.4 kg     ◀ same as minimal_waste
  bulk_value      € 412.20     65.1 kg
  minimal_waste   € 158.40     21.4 kg     ◀ same as cheapest
```

## What this flow does NOT do

Out of scope for the user flow (and therefore for the CLI):

- No login, no accounts, no cloud sync
- No supplier pricing API — catalog is static, refreshed by editing YAML
- No order placement — purchase list is a document, not a transaction
- No stock tracking ("I already have 3 kg of cement")
- No structural calculation — densities and proportions only
- No web UI — the wizard is the only interface

Future phases may add an importable Python API so a separate web
product could consume the same domain library, but this is not part
of the CLI flow.

## Decisions

| Topic | Decision |
|-------|----------|
| Project storage | `./projects/` relative to the current working directory. `--project-dir` flag overrides. No global state in `~/`. |
| Export format | `.xlsx` is the only export path. Install with `uv add mixsheet[export]` to enable the writer. |
| Logging | Structlog JSON to a rotating log file under `./projects/.logs/` (or the configured project-dir). Only warnings and errors surface on stderr; the Rich wizard owns stdout. |
| Preset version pinning | A project pins both `preset_id` **and** `preset_version` at save time. Reopening a project with a newer catalog version warns and offers to recalculate against the new preset or keep the pinned values. |

## Catalog cleanup vs old implementation

The YAML catalogs (`presets.yaml`, `suppliers.yaml`) port over from the
old backend largely as-is. Six cleanups apply when migrating:

| Change | Reason |
|--------|--------|
| Drop `material_name` from preset materials list | Redundant — looked up from `materials:` by `material_id`. |
| Drop `vat_rate` from suppliers | Stored but never used in old code. Re-introduce only when net/gross display is required. |
| Drop `description` from packages | Inconsistently set; the display label is always derivable as `"{material} {weight} kg"`. |
| Mark `water` as default-excluded | Modeled as a fake €0.01/L supplier in the old data. Water is user-supplied; the optimizer should skip it unless explicitly listed. |
| Add file-level `catalog_version` (date string) | Lets a project's pinned preset version be cross-checked against the catalog the user is currently running. |
| Rename model field `density` → `density_kg_per_l` | Matches the YAML key and removes the unit-less ambiguity. |

These are catalog-data changes, not behavioural. Materials, presets,
suppliers, packages and prices stay identical.

## Help and discoverability

The CLI is the only interface — it must teach itself. Help is layered:

### Command-line help (`--help`)

Standard Typer-generated help on every command:

```
$ mixsheet --help
$ mixsheet new --help
$ mixsheet open --help
```

Each command shows its purpose, arguments, options, and one usage
example.

### Topic help (`mixsheet help <topic>`)

Long-form explanations the user reaches for *while* deciding, not while
typing flags. Topics map onto sections of this document:

```
$ mixsheet help overage      # When to raise/lower it, with examples
$ mixsheet help volume       # Three input modes explained
$ mixsheet help strategies   # Cheapest vs bulk vs minimal-waste
$ mixsheet help presets      # What's in the catalog, how to add custom
$ mixsheet help projects     # File format, resuming, hand-editing
$ mixsheet help export       # CSV vs xlsx, what each artifact contains
$ mixsheet help              # Index of all topics
```

Topic content lives next to this document under `docs/help/<topic>.md`
and is bundled with the package. Each topic reads like a printed
reference card: half a page, examples, no marketing.

### Inline help during the wizard

Every prompt accepts `?` as input to show context-specific help without
losing wizard state:

```
? Project overage (% extra applied to purchase): ?

  Project overage covers mixing losses, supplier rounding, dropped bags
  and re-pour margin in one number. Default 10%.

    0%   — precise calculation, you accept zero margin
    5%   — clean pour, well-defined geometry
   10%   — typical workshop use (default)
   20%+  — restocking anyway, or a risky pour

  See: mixsheet help overage

? Project overage (% extra applied to purchase): _
```

Validation errors include a one-line "see also" pointer:

```
  ! Length must be > 0. (mixsheet help volume)
```

### Documentation pointer

The CLI surfaces the project's documentation URL on first run and on
`mixsheet --version`, but does not require network access for any
help. All help is local.
