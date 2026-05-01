"""Path resolution: slug, flat single, folder machine, open-existing."""

from __future__ import annotations

from pathlib import Path

from mixsheet.wizard.paths import (
    resolve_new_paths,
    resolve_open_paths,
    slugify,
)


def test_slugify_lowercases_and_dashes() -> None:
    assert slugify("Lathe Bed Riser") == "lathe-bed-riser"


def test_slugify_strips_punctuation_and_collapses_dashes() -> None:
    assert slugify("Router  Gantry!  v2") == "router-gantry-v2"


def test_slugify_falls_back_for_empty_input() -> None:
    assert slugify("   ") == "project"


def test_resolve_new_paths_single_uses_flat_layout(tmp_path: Path) -> None:
    paths = resolve_new_paths("Lathe bed riser", "single", tmp_path)
    assert paths.project_file == (tmp_path / "lathe-bed-riser.yaml").resolve()
    assert paths.purchase_xlsx == (tmp_path / "lathe-bed-riser.purchase.xlsx").resolve()
    assert paths.mixsheet_xlsx == (tmp_path / "lathe-bed-riser.mixsheets.xlsx").resolve()


def test_resolve_new_paths_machine_uses_folder_layout(tmp_path: Path) -> None:
    paths = resolve_new_paths("Router gantry", "machine", tmp_path)
    folder = (tmp_path / "router-gantry").resolve()
    assert paths.project_file == folder / "project.yaml"
    assert paths.purchase_xlsx == folder / "purchase.xlsx"
    assert paths.mixsheet_xlsx == folder / "mixsheets.xlsx"


def test_resolve_new_paths_default_dir() -> None:
    paths = resolve_new_paths("Demo", "single", None)
    assert paths.project_file.parent.name == "projects"


def test_resolve_open_paths_machine(tmp_path: Path) -> None:
    project_file = tmp_path / "router-gantry" / "project.yaml"
    project_file.parent.mkdir()
    project_file.write_text("schema_version: 1\n", encoding="utf-8")
    paths = resolve_open_paths(project_file)
    assert paths.purchase_xlsx == project_file.parent.resolve() / "purchase.xlsx"
    assert paths.mixsheet_xlsx == project_file.parent.resolve() / "mixsheets.xlsx"


def test_resolve_open_paths_single(tmp_path: Path) -> None:
    project_file = tmp_path / "lathe-bed-riser.yaml"
    project_file.write_text("schema_version: 1\n", encoding="utf-8")
    paths = resolve_open_paths(project_file)
    assert paths.purchase_xlsx == tmp_path.resolve() / "lathe-bed-riser.purchase.xlsx"
    assert paths.mixsheet_xlsx == tmp_path.resolve() / "lathe-bed-riser.mixsheets.xlsx"
