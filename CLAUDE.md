# CLAUDE.md — The Mix Sheet (CLI)

Root instructions for the `mixsheet` repo. Open-source material calculator
for concrete and UHPC mixes, distributed as a Python CLI. Calculates
material requirements, optimizes packaging, minimizes waste and provides
cost insight.

## Documentation

Start in [`docs/README.md`](docs/README.md) — index over:

- [`charter.md`](docs/charter.md) — purpose, scope, design principles
- [`ROADMAP.md`](docs/ROADMAP.md) — phase-gated implementation order
- [`STACK.md`](docs/STACK.md) — tech-stack inventory

`pyproject.toml` and `uv.lock` are authoritative for installed versions;
`STACK.md` summarises but is not authoritative.

## Scope

Mix Sheet is a **CLI tool**. It is not an HTTP service and ships no
frontend. The user experience is an interactive terminal wizard
(Typer + Rich) that mirrors the four-step calculator flow:

1. Component dimensions → volume
2. Material breakdown per component
3. Machine builder (multi-component aggregation)
4. Purchase list (supplier-aware package optimization)

Output artifacts (mix sheets, purchase lists) are written to disk for
offline use on the workbench.

## Tech stack

- **Python** 3.14+, `src/` layout (single package)
- **Package manager** uv; never pip
- **CLI** Typer + Rich for prompts, tables, and progress
- **Validation** Pydantic v2 (`model_config = ConfigDict(strict=True)`)
- **Linting / formatting** ruff with `S`, `D`, `ANN`, `PT`, `PL` rule sets
- **Type checking** pyright (basic)
- **Testing** pytest + pytest-cov
- **Logging** structlog JSON, never `print()` (use Rich for user-facing UI)

## Terminology

Use these terms consistently in CLI output and docs:

| Concept | Term | Not this |
|---------|------|----------|
| Material formula | Mix / mix preset | Recipe, formula, composition |
| Amounts needed | Required | Needed, necessary, demand |
| What you buy | Purchase / order | Shopping list, cart |
| Leftover material | Waste | Excess, surplus, remainder |
| Extra for safety | Overage | Buffer, safety margin, contingency |
| Supplier sizes | Packages | Bags, containers, units |
| Running the calc | Calculate | Compute, process, run |
| The result | Purchase list | Order summary, shopping list |

Product name: "The Mix Sheet" or "Mix Sheet" — never "the mix sheet" or
"MixSheet".

## Specification workflow

This repo uses **OpenSpec** for capability specs and changes. See
[`openspec/config.yaml`](openspec/config.yaml) for repo-specific rules.

- Capability specs live in [`openspec/specs/`](openspec/specs/) and use
  SHALL/MUST contracts with at least one testable scenario per requirement.
- Proposed changes live in [`openspec/changes/<slug>/`](openspec/changes/);
  archived changes move to `openspec/changes/archive/`.
- Skills `openspec-propose`, `openspec-apply-change`,
  `openspec-archive-change`, and `openspec-explore` are available under
  `.claude/skills/`.
