# Roadmap

Phase-gated implementation order. Each phase ships a working CLI; later
phases extend it without rewriting earlier work.

## Phase 0 — Scaffold ✅

- src-layout Python package, Typer CLI entry point
- OpenSpec workspace, pre-commit hooks, pytest harness
- Docs skeleton (charter, roadmap, stack)

## Phase 1 — Domain core

- Pydantic models: `MixPreset`, `Component`, `SupplierPackage`,
  `Machine`, `PurchaseLine`
- YAML catalog loader with validation at startup (fail-fast)
- Pure calculator: dimensions → volume → material weights per component
- Display-precision rules (FR-012 from prior spec): 1 decimal ≤ 10, 0
  above; prices 2 decimals; percentages 0 decimals
- Unit tests against known-good fixtures from the prior backend

## Phase 2 — Multi-component aggregation ✅

- Pure `aggregate_project(project, catalog) -> ProjectBreakdown` summing
  per-component breakdowns into project-wide volume, weight, and
  per-material totals with source attribution.

## Phase 3 — Purchase optimization

- Supplier-aware package selection per material
- Three strategies: cheapest, bulk-value, minimal-waste
- Waste, overage and cost reporting per line

## Phase 4 — Export

- Excel export of purchase list (xlsxwriter, optional dependency)
- Per-component mix sheets formatted for print

## Phase 5 — Interactive wizard

- Typer + Rich prompts mirroring the four-step flow:
  dimensions → calculate → machine → purchase
- Resumable sessions saved as JSON snapshots

## Future

- Importable Python API for downstream consumers (e.g. a future web app)
- Custom mix presets and supplier overrides via user-config directory
