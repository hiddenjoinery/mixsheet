# Tech stack

Snapshot of the runtime and tooling. `pyproject.toml` and `uv.lock` are
authoritative for installed versions.

## Language and runtime

- **Python** 3.14+
- **Layout** `src/` single-package
- **Package manager** uv

## Runtime dependencies

| Library | Role |
|---------|------|
| pydantic v2 | Data models, strict validation |
| pydantic-settings | Environment / `.env` configuration |
| typer | CLI command tree |
| rich | Terminal UI: prompts, tables, progress |
| structlog | Structured JSON logging to stderr |
| pyyaml | Catalog files (mix presets, supplier packages) |

## Development tooling

| Tool | Role |
|------|------|
| ruff | Linting and formatting (strict ruleset incl. `S`, `D`, `ANN`, `PT`, `PL`) |
| pyright | Type checking (basic mode) |
| pytest | Test runner |
| pytest-cov | Coverage reporting |
| pre-commit | Git hook runner |
| gitleaks | Secret detection |
| actionlint | GitHub Actions linting |

## Conventions

- Type hints required on public functions
- Google-style docstrings
- f-strings, never `.format()`
- `pathlib`, never `os.path`
- One exception type per `except` clause
- No nested `if` — use early returns or extract functions
- Logging via structlog; never `print()` (use Rich for user-facing UI)
