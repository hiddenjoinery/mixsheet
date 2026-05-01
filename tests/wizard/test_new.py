"""Integration tests for ``mixsheet new`` end-to-end via CliRunner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from mixsheet.cli import app
from mixsheet.domain import load_bundled_catalog, load_project

if TYPE_CHECKING:
    from pathlib import Path

    from typer.testing import CliRunner

SINGLE_INPUT = "\n".join(
    [
        "Test Riser",
        "single",
        "riser",
        "1",
        "dimensions",
        "320",
        "180",
        "60",
        "1",
        "10",
        "n",
        "1",
        "",
    ],
)
"""Single-component golden path: name+shape+component+overage+no-compare+strategy."""


MACHINE_INPUT = "\n".join(
    [
        "Router gantry",
        "machine",
        "Bed",
        "1",
        "dimensions",
        "800",
        "400",
        "120",
        "1",
        "y",
        "Slide",
        "1",
        "area_height",
        "240000",
        "80",
        "1",
        "n",
        "10",
        "n",
        "1",
        "",
    ],
)
"""Two-component machine project with no-compare and cheapest strategy."""


def test_new_single_writes_flat_layout(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["new", "--project-dir", str(tmp_path)],
        input=SINGLE_INPUT,
    )
    assert result.exit_code == 0, result.stdout
    project_file = tmp_path / "test-riser.yaml"
    assert project_file.exists()
    assert (tmp_path / "test-riser.purchase.xlsx").exists()
    assert (tmp_path / "test-riser.mixsheets.xlsx").exists()
    project = load_project(project_file, load_bundled_catalog()).project
    assert project.name == "Test Riser"
    assert project.shape == "single"
    assert len(project.components) == 1


def test_new_machine_writes_folder_layout(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["new", "--project-dir", str(tmp_path)],
        input=MACHINE_INPUT,
    )
    assert result.exit_code == 0, result.stdout
    folder = tmp_path / "router-gantry"
    assert (folder / "project.yaml").exists()
    assert (folder / "purchase.xlsx").exists()
    assert (folder / "mixsheets.xlsx").exists()
    project = load_project(folder / "project.yaml", load_bundled_catalog()).project
    assert project.shape == "machine"
    assert len(project.components) == 2


def test_new_save_after_each_prompt_persists_first_component(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """Killing input after the first component lands a loadable file on disk."""
    partial_input = "\n".join(
        [
            "Half Run",
            "single",
            "part",
            "1",
            "dimensions",
            "100",
            "100",
            "100",
            "1",
            "",  # EOF after preset pick — overage prompt fails
        ],
    )
    runner.invoke(
        app,
        ["new", "--project-dir", str(tmp_path)],
        input=partial_input,
    )
    project_file = tmp_path / "half-run.yaml"
    assert project_file.exists()
    project = load_project(project_file, load_bundled_catalog()).project
    assert project.name == "Half Run"
    assert len(project.components) == 1


def test_new_no_compare_flag_skips_comparison_table(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """With --no-compare we drop the comparison? prompt; one fewer input line."""
    flat_input = "\n".join(
        [
            "Quick Run",
            "single",
            "part",
            "1",
            "dimensions",
            "320",
            "180",
            "60",
            "1",
            "10",
            "1",  # strategy directly, no comparison? prompt
            "",
        ],
    )
    result = runner.invoke(
        app,
        ["new", "--project-dir", str(tmp_path), "--no-compare"],
        input=flat_input,
    )
    assert result.exit_code == 0, result.stdout
    assert "Strategy comparison?" not in result.stdout


def test_new_uses_cli_options_to_skip_name_and_shape_prompts(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    flat_input = "\n".join(
        [
            "part",
            "1",
            "dimensions",
            "320",
            "180",
            "60",
            "1",
            "10",
            "1",
            "",
        ],
    )
    result = runner.invoke(
        app,
        [
            "new",
            "--name",
            "Auto Named",
            "--shape",
            "single",
            "--project-dir",
            str(tmp_path),
            "--no-compare",
        ],
        input=flat_input,
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "auto-named.yaml").exists()


def test_new_missing_export_extra_prints_install_hint(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When xlsxwriter is absent the export step prints the install command."""
    from mixsheet.export.excel import MissingExcelExtraError
    from mixsheet.wizard import flow

    def boom(*_args: object, **_kwargs: object) -> None:
        raise MissingExcelExtraError

    monkeypatch.setattr(flow, "write_purchase_workbook", boom)
    result = runner.invoke(
        app,
        ["new", "--project-dir", str(tmp_path), "--no-compare"],
        input="\n".join(
            [
                "Hint",
                "single",
                "part",
                "1",
                "dimensions",
                "320",
                "180",
                "60",
                "1",
                "10",
                "1",
                "",
            ],
        ),
    )
    assert result.exit_code != 0
    flat_stdout = " ".join(result.stdout.split())
    assert "uv add mixsheet[export]" in flat_stdout
    assert (tmp_path / "hint.yaml").exists()


def test_new_mixsheets_yaml_excludes_water_by_default(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app,
        ["new", "--project-dir", str(tmp_path), "--no-compare"],
        input=SINGLE_INPUT.replace("n\n1\n", "1\n"),  # no comparison prompt
    )
    assert result.exit_code == 0, result.stdout
    raw = yaml.safe_load((tmp_path / "test-riser.yaml").read_text(encoding="utf-8"))
    assert "water" in raw["purchase"]["excluded_materials"]
