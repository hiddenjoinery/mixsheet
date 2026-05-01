"""Shared pytest fixtures for the mixsheet test suite."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """Return a Typer ``CliRunner`` for invoking the CLI in tests."""
    return CliRunner()
