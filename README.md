# The Mix Sheet

**Know what you need before you pour.**

![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

Open-source material calculator for concrete and UHPC mixes. Calculates
material requirements, optimizes packaging, minimizes waste and provides
cost insight — all from the terminal.

A product of [Hidden Joinery](https://github.com/hiddenjoinery).

## Quick start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.14+
- [pre-commit](https://pre-commit.com/) (`uv tool install pre-commit`)

### Setup

```bash
uv sync --locked
pre-commit install
```

### Run the CLI

```bash
uv run mixsheet --help
```

## Usage

The Mix Sheet is an interactive terminal wizard. Three commands cover
the full flow:

| Command | Purpose |
|---------|---------|
| `uv run mixsheet new` | Start a new project (single component or machine) |
| `uv run mixsheet open <project.yaml>` | Resume or edit an existing project |
| `uv run mixsheet version` | Print the installed version |

### Wizard flow

`mixsheet new` walks through four steps and writes a YAML project file
plus an `.xlsx` mix sheet and purchase list under `./projects/`:

1. **Component dimensions** — pick volume mode (length × width × height,
   area × height, or direct litres) and enter the geometry.
2. **Material breakdown** — pick a mix preset (epoxy granite, UHPC,
   gantry fill, pure epoxy). The wizard computes required kg per material.
3. **Machine builder** — for multi-component projects, loop step 1–2
   per component until you signal "done". Single-component projects
   skip the loop.
4. **Purchase list** — set project overage (default 10%), compare
   strategies (`cheapest`, `bulk_value`, `minimal_waste`), and write
   the optimized purchase list to disk.

### Common options

```bash
uv run mixsheet new --name "Lathe bed riser" --shape single
uv run mixsheet new --shape machine --no-compare
uv run mixsheet new --project-dir ./my-builds/
uv run mixsheet open ./projects/router-gantry/project.yaml
```

The full user journey, including edge cases (preset removed from
catalog, sub-minimum volumes, strategy ties), lives in
[`docs/user-flow.md`](docs/user-flow.md).

## Project layout

```
mixsheet/
├── .claude/             # Claude Code commands and skills (incl. openspec-*)
├── config/              # Runtime configuration (yaml)
├── docs/                # Charter, roadmap, stack
├── openspec/            # Capability specs and proposed changes
├── scripts/             # Operational helpers
├── src/mixsheet/        # Python package (CLI entry point)
└── tests/               # Pytest suite
```

## Documentation

- [`docs/charter.md`](docs/charter.md) — purpose, scope, design principles
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — implementation phases
- [`docs/STACK.md`](docs/STACK.md) — tech-stack inventory

## License

[MIT](LICENSE)
