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
