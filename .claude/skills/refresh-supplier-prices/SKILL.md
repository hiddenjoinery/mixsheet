---
name: refresh-supplier-prices
description: Verify and refresh list prices and bundle-discount tiers in src/mixsheet/data/suppliers.yaml against the live supplier pages. Use whenever the user mentions checking, verifying, refreshing, or updating Mix Sheet prices, supplier prices, package prices, staffel discounts, bundle discounts, or the supplier catalog. Trigger on phrases like "check supplier prices", "refresh prices", "verify bundle discounts", "update mixsheet catalog", "are the prices still right", or "have the discounts changed".
license: MIT
compatibility: Requires WebFetch tool, the bundled `mixsheet.domain.load_bundled_catalog`, and (for --write mode) ruamel.yaml.
metadata:
  author: hidden-joinery
  version: "1.0"
---

# Refresh supplier prices

Walk every package in `src/mixsheet/data/suppliers.yaml`, fetch its
`product_url`, extract the listed price (incl. VAT) and any
`bundle_discount` tiers from the supplier page, and report a structured
diff against the YAML. Default mode is read-only — the skill prints a
diff and stops; the user reviews and applies manually. Apply mode
(`--write`) edits the YAML in place after explicit per-package
confirmation.

## When to run this

- The user asks whether catalog prices are still current.
- The user wants to refresh the catalog ahead of a real purchase.
- A supplier site has clearly changed (e.g. a redirect, a new staffel,
  a price bump) and the YAML needs reconciliation.
- A new package was added by hand and the user wants it sanity-checked
  against the live page.

If the user just wants to *see* a single supplier listing without
touching the catalog, that's a plain WebFetch call — not this skill.

## Inputs

The user may supply any of:

- `--package <id>` — restrict to one package id (e.g. `epoxy-resin-25kg`).
- `--supplier <id>` — restrict to one supplier (`moertelshop` or
  `rg-faserverbund`).
- `--write` — apply confirmed changes to the YAML in place. Default
  is dry-run.
- `--yaml <path>` — alternate suppliers.yaml path. Defaults to the
  bundled catalog at `src/mixsheet/data/suppliers.yaml`.

If no flags are given, the skill checks every package in the bundled
catalog in dry-run mode.

## Steps

### 1. Load the catalog

Always go through the parsed model rather than re-parsing YAML by
hand:

```python
from mixsheet.domain import load_bundled_catalog
catalog = load_bundled_catalog()
```

This guarantees you see the same shape the rest of the codebase sees,
including `BundleDiscount` rows. For `--yaml <path>` use
`load_catalog(presets_path, path)`.

Filter `catalog.packages` by the user's `--package` / `--supplier`
flags before doing any web work. Skip any package whose `product_url`
is `None` and report it as "no URL on file" so the user can backfill.

### 2. Fetch each product page

Call WebFetch once per unique `product_url` (Moertelshop's three
durigid grain sizes share one URL — fetch once, parse all three from
the result). Use a focused extraction prompt per supplier:

**Moertelshop prompt template:**

> "List every variant on this page with its weight (kg or L) and price
> incl. VAT (€). Output as a markdown table with columns: variant,
> weight_kg, price_eur. If a variant's price is hidden behind a
> selector and not shown on the page, write 'unknown' in the price
> column. Do not invent prices."

**RG Faserverbund prompt template:**

> "List every package size with its weight (kg or L), price incl. VAT
> (€), and the full staffel/bulk-discount table (each row: from N
> units, X% off). Output as two markdown tables. Show every tier
> verbatim — do not summarise."

Keep the prompts deterministic; do not ask the model to "judge" or
"interpret". The diff step is where judgment happens, on the user's
side.

### 3. Compute the diff

For each package in scope, compare:

- `price_incl_vat` (YAML) against the listed price for the matching
  variant on the page. Match by `weight_kg` — Moertelshop's variant
  selector reports weight prominently; RG's pages list packages by
  weight in their headers.
- `bundle_discounts` (YAML) — *only* for RG Faserverbund packages —
  against the staffel rows scraped from the page. Compare both
  `min_quantity` and `discount_pct` exactly. If the page shows a tier
  that is missing in YAML, flag it. If YAML has a tier that is missing
  on the page, flag it. Do not silently drop or merge tiers.

Anything we could not confirm — variant selector hid the price, page
returned a redirect, fetch failed — goes in a separate "unconfirmed"
list. Never guess; never carry over the YAML value as if it were
verified.

### 4. Render the report

Use Rich (or plain markdown if the channel doesn't render Rich) with
this exact structure:

```
## Mix Sheet — supplier price refresh

### Confirmed unchanged
{count} packages match online listings exactly.

### Changes proposed
| package_id        | field            | yaml      | online    | delta    |
|-------------------|------------------|-----------|-----------|----------|
| epoxy-resin-25kg  | price_incl_vat   | €341.21   | €340.98   | -€0.23   |
| hardener-gl2-20kg | price_incl_vat   | €404.97   | €404.87   | -€0.10   |
| epoxy-resin-25kg  | bundle_discounts | (3 tiers) | (4 tiers) | +1 tier  |

### Unconfirmed
- durigid-1-3-25kg: variant price hidden behind selector on
  https://www.moertelshop.com/buy-refractory-aggregate-cheaply_15
- pce-375-10l: HTTP 503 from supplier
```

For tier diffs, expand the row when the user asks (or include a
collapsed summary like `+1 tier` and a follow-up table that lists each
changed tier as one row).

Always include the "Unconfirmed" section even when empty (write
"(none)") so the user knows the skill considered it.

### 5. Stop here in dry-run mode

In dry-run, the skill ends after the report. Tell the user how to
apply: "Run me again with `--write` to apply these changes after
confirmation per package." Do not edit any file in dry-run mode.

### 6. Apply mode

When the user passes `--write`:

1. Iterate proposed changes one by one. For each, show the same row
   from the diff and ask `Apply? [y/N/quit]`. Treat anything other
   than `y` as decline.
2. Confirmed edits go through `ruamel.yaml.YAML(typ="rt")` so YAML
   comments and key order survive. Read the full file, mutate the
   targeted package node, write back. Do *not* round-trip the file
   through `yaml.safe_load` / `yaml.safe_dump` — that would erase the
   header comment and reformat every block.
3. After every applied change, re-run `load_bundled_catalog()` to
   confirm the file still parses. If it doesn't, restore the
   pre-change content and surface the validation error to the user.
4. If `ruamel.yaml` is not installed, abort apply mode and tell the
   user: "ruamel.yaml is not in the project deps. Add it under the
   relevant pyproject extra and rerun." Do not fall back to PyYAML —
   the catalog file's comments and ordering are part of the
   contract.

Never commit, never push, never open a PR. The user owns the diff
once it's on disk.

## Supplier-specific parsing notes

### Moertelshop (`https://www.moertelshop.com/...`)

- All prices on the page already include 19 % German VAT — no
  conversion needed.
- Pages list variants by weight (5 kg / 25 kg / 300 kg / 1000 kg).
  The 5 kg row is always visible; larger sizes are sometimes only
  selectable in a dropdown, with the price loaded over JS. WebFetch
  returns the static HTML, so those prices may show as "unknown".
  Don't fabricate them.
- Durigid: one product page covers `0-1`, `1-3`, and `3-6` mm. The
  variant selector keys off the grain size; price is identical across
  sizes today (€17.40 for 5 kg, €52.40 for 25 kg). Verify per
  YAML-package by mapping `material_id` (`durigid-0-1` etc.) to the
  grain-size variant on the page.
- No staffel discounts — `bundle_discounts` should always be empty
  for Moertelshop packages. If the page ever starts showing tiers,
  flag it.

### RG Faserverbund (`https://www.r-g.de/en/art/...`)

- Prices include 19 % VAT.
- Each package size has its own staffel table. The pattern is "Ab N
  Stück: X %" (German) or "From N units: X %" (English mirror at
  `/en/`). Use the English URL where available.
- Tiers must be strictly ascending on both `min_quantity` and
  `discount_pct` — that's a Pydantic invariant in the catalog
  (`SupplierPackage._bundle_discounts_strictly_increase`). If the
  page ever shows a flat-rate tier ("From 5: €19.95 each") instead of
  a percentage, surface it as a structural mismatch — the current
  schema can't represent flat-rate tiers, and the user must decide
  whether to extend the schema or model it as an equivalent
  percentage.

## Example invocations

**Default dry-run, full catalog:**

> User: "check supplier prices"
> Skill: fetches every URL, prints the diff table.

**Targeted check on one package:**

> User: "verify bundle discounts on epoxy-resin-25kg"
> Skill: fetches `https://www.r-g.de/en/art/100133`, prints the staffel
> diff for that one package.

**Apply confirmed changes:**

> User: "the diff looks right, apply it with --write"
> Skill: walks each row, prompts `Apply? [y/N/quit]`, edits via
> ruamel.yaml, re-validates by reloading the catalog.

## Open follow-ups (for a future code-side change)

- A small Python helper under `src/mixsheet/_devtools/` could wrap the
  WebFetch + parse + Rich-table flow into a `mixsheet refresh-prices`
  CLI subcommand. Worth doing once the skill has been used a few
  times and the parsing patterns stabilise — until then, agent-driven
  is fine.
- Add `ruamel.yaml` to a `[tool.uv.sources]` dev extra so apply mode
  works without a separate install step.
