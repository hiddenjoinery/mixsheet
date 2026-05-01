"""Wizard test fixtures: bundled catalog plus a Console-on-StringIO factory."""

from __future__ import annotations

import sys
from collections.abc import Callable
from io import StringIO

import pytest
from rich.console import Console

from mixsheet.domain import Catalog, load_bundled_catalog


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    return load_bundled_catalog()


@pytest.fixture
def make_console(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], tuple[Console, StringIO]]:
    """Return a factory that builds a Console wired to a stdin string.

    The factory installs ``StringIO(stdin_text)`` as ``sys.stdin`` so
    ``console.input(...)`` reads from it. Console output is captured on
    the returned ``StringIO`` so assertions can read it back.
    """

    def factory(stdin_text: str) -> tuple[Console, StringIO]:
        monkeypatch.setattr(sys, "stdin", StringIO(stdin_text))
        out = StringIO()
        console = Console(file=out, force_terminal=False, no_color=True, width=120)
        return console, out

    return factory
