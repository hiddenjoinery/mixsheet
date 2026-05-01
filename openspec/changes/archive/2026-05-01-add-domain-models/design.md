## Context

`docs/user-flow.md` is the source of truth for the project file shape
(`schema_version: 1`, components with three volume input modes,
project-level `purchase.overage_pct`, pinned `preset_version`,
`excluded_materials`) and the catalog shape (file-level
`catalog_version`, `default_excluded` materials,
`density_kg_per_l` on presets, suppliers without `vat_rate`, packages
without `description`).

This change locks that shape into typed models and a fail-fast loader
so every later capability can rely on the data being valid the moment
it is in memory.

## Goals / Non-Goals

**Goals:**

- Single source of truth for project and catalog data via Pydantic v2.
- Decimal-only arithmetic across the stack; no float drift, no int
  grams.
- Fail-fast catalog validation at process start: malformed catalog
  refuses to load instead of producing wrong results downstream.
- Round-trippable project YAML: load → save → reload yields identical
  inputs, with derived fields recomputed.
- A small `display` constants module so wizard, exports, and tests pull
  precision rules from one place.

**Non-Goals:**

- Volume → material weights (calculator).
- Purchase optimization, package selection, waste calculation.
- Machine-level aggregation logic beyond the `shape: machine` flag.
- Typer commands, Rich rendering, prompt flow, project resume UX.
- Export formats (CSV, xlsx).

## Decisions

### D1 — Pydantic v2 strict, frozen value objects

Use `ConfigDict(strict=True, frozen=True)` on every catalog model
(`Material`, `MaterialProportion`, `MixPreset`, `Supplier`,
`SupplierPackage`). Project models (`Project`, `Component`, `Volume`,
`PurchaseConfig`) are strict but mutable — the wizard mutates them
between prompts.

Alternative considered: `dataclasses` with manual validators. Rejected:
loses field coercion, JSON Schema export (useful for the future web
consumer), and discriminated unions for `Volume.mode`.

### D2 — `Volume` is a discriminated union by `mode`

`Volume` is a tagged union over three variants:

- `DimensionsVolume` (`length_mm`, `width_mm`, `height_mm`)
- `AreaHeightVolume` (`area_mm2`, `height_mm`)
- `DirectVolume` (`volume_l`)

A `volume_l: Decimal` computed field on each variant exposes the same
contract; the `Component` model never branches on mode after parsing.
Pydantic's `Field(discriminator="mode")` handles parsing.

Alternative considered: one flat `Volume` model with optional fields
per mode. Rejected: validators become a maze of "if mode == X then Y
must be set"; type-checkers cannot help.

### D3 — Volume derivation belongs in the model, weight derivation does not

`Volume.volume_l` is pure geometry: `length × width × height` in mm³ →
litres. It needs no preset, no density. Putting it on the model means
`Component` always exposes `volume_l` regardless of input mode, and
keeps `add-calculator` focused on `volume_l × density × proportion →
kg`.

Alternative considered: keep all derivation in the calculator package.
Rejected: every consumer (export, wizard echo, machine totals) would
need to recompute the same arithmetic.

### D4 — Catalog file shape with explicit `catalog_version`

Catalog YAML gains a top-level `catalog_version: "YYYY-MM-DD"` string.
The loader rejects catalogs without it. Projects pin
`preset_version` per component (already present in the user-flow
example). On reopen, the loader compares pinned versions to the
catalog and surfaces a structured `CatalogVersionMismatch` warning;
the wizard decides what to do with it (out of scope here).

Alternative considered: hash the catalog file. Rejected: hashes change
on whitespace edits and give no human-readable diff.

### D5 — Default-excluded materials are catalog-driven

`Material` gains `default_excluded: bool = False`. The bundled catalog
sets `water.default_excluded = true`. New `Project` instances seed
`purchase.excluded_materials` from the catalog's default-excluded set
when created. Hand-edited project files keep whatever the user wrote.

**Forward-looking contract** (consumed by future capabilities, not
enforced here):

- `add-purchase-optimizer` MUST skip every material id in
  `purchase.excluded_materials` — no package selection, no cost, no
  waste, no overage line. The purchase list footer notes the count of
  skipped materials so the omission is visible.
- `add-export` (mix sheet) MUST still show excluded materials as
  required kg per component (you need them to pour) and SHOULD list
  them at the bottom of the sheet as "source separately".

This capability provides only the data and the seed. Behaviour lives
with the consuming capabilities.

Alternative considered: hardcode `"water"` in the wizard. Rejected:
violates charter principle 1 (data first) and would not extend to
future user-supplied additives.

### D6 — Catalog shape

The bundled YAML ships in the cleaned shape from `docs/user-flow.md`:
no `material_name` inside `preset.materials[*]`, no `vat_rate` on
`Supplier`, no `description` on `SupplierPackage`, a top-level
`catalog_version` (date string), `density_kg_per_l` on every preset,
and `default_excluded: true` on `water`. Strict-mode validation
rejects any field outside the documented schema; no compatibility
shims are introduced.

### D7 — Display precision as constants, not formatters

`mixsheet.domain.display` exports plain constants:
`QUANTITY_DECIMALS_LOW = 1`, `QUANTITY_DECIMALS_HIGH = 0`,
`QUANTITY_THRESHOLD = Decimal("10")`, `PRICE_DECIMALS = 2`,
`PERCENT_DECIMALS = 0`. No `format_quantity()` helper here — that
ships with the wizard, where Rich rendering needs are concrete.

### D8 — Filesystem layout

```
src/mixsheet/
  domain/
    __init__.py
    catalog.py        # Material, MixPreset, Supplier, SupplierPackage, loader
    project.py        # Project, Component, Volume variants, PurchaseConfig, loader
    strategy.py       # Strategy enum
    display.py        # precision constants
  data/
    presets.yaml
    suppliers.yaml
```

YAML files ship inside the package via `importlib.resources` so the
installed wheel finds them without filesystem hunting.

## Risks / Trade-offs

- **Discriminated union complexity** → mitigated by exhaustive
  scenario coverage for each `Volume` variant (see specs).
- **Catalog drift between bundled YAML and user-supplied YAML** →
  mitigated by versioning every catalog file with `catalog_version` and
  surfacing mismatch on project reopen. User-supplied catalog override
  is out of scope here; it lands with `add-interactive-wizard` or a
  dedicated `add-user-catalog-override` change.
- **Decimal precision on `volume_l` from dimensions** → all arithmetic
  in `Decimal`, no `float`; rounding deferred to display layer.
- **Frozen catalog models complicate hot-reload** → acceptable: catalog
  is read once at startup; hot-reload is out of charter.
- **`pyyaml` security (arbitrary tag execution)** → mitigated by using
  `yaml.safe_load` exclusively.

## Migration Plan

Not applicable — this is the first capability spec for the new CLI.
