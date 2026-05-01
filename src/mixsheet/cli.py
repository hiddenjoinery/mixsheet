"""Typer-based CLI entry point for The Mix Sheet.

Wires up subcommands and exposes ``app`` as the ``mixsheet`` console
script. Domain logic lives in ``mixsheet.domain``; the interactive
wizard lives in ``mixsheet.wizard``. This file stays a thin shell.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - needed at runtime for Typer annotations
from typing import Annotated

import typer
from rich.console import Console

from mixsheet import __version__
from mixsheet.domain.catalog import load_bundled_catalog
from mixsheet.wizard import run_new, run_open

app = typer.Typer(
    name="mixsheet",
    help="Know what you need before you pour.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Print the installed Mix Sheet version."""
    Console().print(f"mixsheet {__version__}")


@app.command(name="new")
def new_command(
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Project name (skips the name prompt)."),
    ] = None,
    shape: Annotated[
        str | None,
        typer.Option("--shape", help="Project shape: 'single' or 'machine'."),
    ] = None,
    project_dir: Annotated[
        Path | None,
        typer.Option(
            "--project-dir",
            help="Override the default ./projects/ output directory.",
        ),
    ] = None,
    no_compare: Annotated[
        bool,
        typer.Option(
            "--no-compare",
            help="Skip the strategy comparison table.",
        ),
    ] = False,
) -> None:
    """Start a new project with the interactive wizard."""
    console = Console()
    catalog = load_bundled_catalog()
    exit_code = run_new(
        console,
        catalog,
        name=name,
        shape=shape,
        project_dir=project_dir,
        no_compare=no_compare,
    )
    raise typer.Exit(code=exit_code)


@app.command(name="open")
def open_command(
    project_path: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            help="Path to an existing project YAML file.",
        ),
    ],
    no_compare: Annotated[
        bool,
        typer.Option(
            "--no-compare",
            help="Skip the strategy comparison table.",
        ),
    ] = False,
) -> None:
    """Resume an existing project via the interactive wizard."""
    console = Console()
    catalog = load_bundled_catalog()
    exit_code = run_open(
        console,
        catalog,
        project_path=project_path,
        no_compare=no_compare,
    )
    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
