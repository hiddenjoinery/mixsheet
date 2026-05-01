"""Smoke tests proving the CLI loads."""

from __future__ import annotations

from typer.testing import CliRunner

from mixsheet.cli import app


def test_version_command_returns_zero(runner: CliRunner) -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "mixsheet" in result.stdout
