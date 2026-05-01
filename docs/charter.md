# Charter — The Mix Sheet

## Purpose

The Mix Sheet calculates material requirements for concrete and UHPC
mixes, optimizes supplier package selection, surfaces waste and overage,
and produces actionable artifacts (mix sheets for the workbench, purchase
lists for the order desk).

**Tagline:** "Know what you need before you pour."

## Audience

DIY builders, hobby machinists and small workshops who pour concrete or
UHPC components — typically machine bases, tooling plates, and frames —
and need to translate "fill this volume" into "buy this much from these
suppliers" without spreadsheet gymnastics.

## Scope

**In scope**

- Single-component calculations (dimensions or direct volume → material weights)
- Multi-component aggregation under a named "machine" project
- Purchase-list optimization across supplier package sizes
- Three optimization strategies: cheapest, bulk-value, minimal-waste
- Export to disk: per-component mix sheets and combined purchase lists
- Built-in catalogs of mix presets and supplier packages, user-extendable
  via YAML

**Out of scope**

- HTTP service / web frontend (a separate web product may consume the
  same domain library later)
- Stock management, order placement, payments
- Real-time supplier price feeds — package prices are static catalog data
- Pour scheduling, curing models, structural engineering calculations

## Design principles

1. **Data first** — mix presets and supplier packages are declarative
   YAML, validated at startup. Code is the calculator, not the catalog.
2. **CLI as contract** — every result the user sees on screen is a
   structured value that can also be exported to file. No hidden state.
3. **Calculate honestly** — show waste, overage and rounding explicitly.
   The user always sees what they pay for and what they throw away.
4. **Simplicity** — one Python package, one CLI command, no plugin
   system. Add complexity only when a real workflow demands it.
5. **Discovery before implementation** — non-trivial features go through
   an OpenSpec proposal before code lands.
6. **Documentation closes the loop** — CHANGELOG, README, and roadmap
   updates ship in the same change as the code.

## Voice

User-facing copy follows the **Corbin** voice — anonymous, instrumental,
no marketing flair. Refer to the `hj-corbin` skill.
