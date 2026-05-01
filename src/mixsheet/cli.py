"""Typer-based CLI entry point for The Mix Sheet.

Wires up subcommands and exposes ``app`` as the ``mixsheet`` console script.
Domain logic lives in dedicated modules; this file stays a thin shell.
"""

from __future__ import annotations

import typer
from rich.console import Console

from mixsheet import __version__

app = typer.Typer(
    name="mixsheet",
    help="Know what you need before you pour.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def version() -> None:
    """Print the installed Mix Sheet version."""
    console.print(f"mixsheet {__version__}")


@app.command()
def calc() -> None:
    """Run the interactive calculator wizard.

    Placeholder — the wizard implementation lands in a later phase.
    """
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
