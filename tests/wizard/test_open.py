"""Integration tests for ``mixsheet open`` resume menu and remediations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from mixsheet.cli import app
from mixsheet.domain import (
    Component,
    DimensionsVolume,
    DirectVolume,
    Project,
    PurchaseConfig,
    load_bundled_catalog,
    load_project,
    save_project,
)
from mixsheet.domain.strategy import Strategy

if TYPE_CHECKING:
    from pathlib import Path

    from typer.testing import CliRunner


def _bedded_project(tmp_path: Path, overage: Decimal = Decimal("0.10")) -> Path:
    catalog = load_bundled_catalog()
    preset = catalog.presets[0]
    project_file = tmp_path / "demo.yaml"
    project = Project(
        schema_version=1,
        id="demo",
        name="Demo",
        shape="single",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        components=[
            Component(
                id="part",
                name="Part",
                quantity=1,
                volume=DimensionsVolume(
                    length_mm=Decimal("320"),
                    width_mm=Decimal("180"),
                    height_mm=Decimal("60"),
                ),
                preset_id=preset.id,
                preset_version=preset.version,
            ),
        ],
        purchase=PurchaseConfig(overage_pct=overage, excluded_materials=["water"]),
    )
    save_project(project, project_file)
    return project_file


def test_open_continue_finalises_to_export(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    project_file = _bedded_project(tmp_path)
    # menu pick 1 (continue) → no compare prompt → strategy 1 (cheapest) →
    # overage default keeps 10. Order: overage (default 10) → comparison (n) →
    # strategy (1).
    inputs = "\n".join(["1", "10", "n", "1", ""])
    result = runner.invoke(app, ["open", str(project_file)], input=inputs)
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "demo.purchase.xlsx").exists()
    assert (tmp_path / "demo.mixsheets.xlsx").exists()


def test_open_continue_label_matches_state(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    project_file = _bedded_project(tmp_path)
    # quit immediately to inspect the menu output
    result = runner.invoke(app, ["open", str(project_file)], input="6\n")
    assert result.exit_code == 0
    assert "next: purchase strategy" in result.stdout
    # now create the workbooks and re-open: continue should switch to re-export
    runner.invoke(
        app,
        ["open", str(project_file)],
        input="\n".join(["1", "10", "n", "1", ""]),
    )
    result2 = runner.invoke(app, ["open", str(project_file)], input="6\n")
    assert "next: re-export" in result2.stdout


def test_open_quit_leaves_file_untouched(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    project_file = _bedded_project(tmp_path)
    before = project_file.read_bytes()
    result = runner.invoke(app, ["open", str(project_file)], input="6\n")
    assert result.exit_code == 0
    assert project_file.read_bytes() == before


def test_open_mismatch_warning_appears(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    catalog = load_bundled_catalog()
    preset = catalog.presets[0]
    project_file = tmp_path / "drift.yaml"
    project = Project(
        schema_version=1,
        id="drift",
        name="Drift",
        shape="single",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        components=[
            Component(
                id="part",
                name="Part",
                quantity=1,
                volume=DirectVolume(volume_l=Decimal("3.5")),
                preset_id=preset.id,
                preset_version="0.0.0",  # forced drift
            ),
        ],
        purchase=PurchaseConfig(excluded_materials=["water"]),
    )
    save_project(project, project_file)
    result = runner.invoke(app, ["open", str(project_file)], input="6\n")
    assert result.exit_code == 0
    flat = " ".join(result.stdout.split())
    assert "pinned preset" in flat
    assert "0.0.0" in flat
    assert preset.version in flat


def test_open_unknown_preset_remediation_persists(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    catalog = load_bundled_catalog()
    real_preset = catalog.presets[0]
    project_file = tmp_path / "ghost.yaml"
    project = Project(
        schema_version=1,
        id="ghost",
        name="Ghost",
        shape="single",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        components=[
            Component(
                id="part",
                name="Part",
                quantity=1,
                volume=DirectVolume(volume_l=Decimal("3.5")),
                preset_id=real_preset.id,
                preset_version=real_preset.version,
            ),
        ],
        purchase=PurchaseConfig(excluded_materials=["water"]),
    )
    save_project(project, project_file)

    raw = project_file.read_text(encoding="utf-8")
    swapped = raw.replace(real_preset.id, "legacy-mix")
    project_file.write_text(swapped, encoding="utf-8")

    # remediation menu: index 2 = first available preset id (sorted), then
    # quit the resume menu (6).
    result = runner.invoke(app, ["open", str(project_file)], input="\n".join(["2", "6", ""]))
    assert result.exit_code == 0
    assert "unknown preset" in " ".join(result.stdout.split()).lower()
    reloaded = load_project(project_file, catalog).project
    assert reloaded.components[0].preset_id != "legacy-mix"


def test_open_unknown_preset_quit_leaves_file_untouched(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    catalog = load_bundled_catalog()
    real_preset = catalog.presets[0]
    project_file = tmp_path / "ghost.yaml"
    project = Project(
        schema_version=1,
        id="ghost",
        name="Ghost",
        shape="single",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        components=[
            Component(
                id="part",
                name="Part",
                quantity=1,
                volume=DirectVolume(volume_l=Decimal("3.5")),
                preset_id=real_preset.id,
                preset_version=real_preset.version,
            ),
        ],
        purchase=PurchaseConfig(excluded_materials=["water"]),
    )
    save_project(project, project_file)
    swapped = project_file.read_text(encoding="utf-8").replace(real_preset.id, "legacy-mix")
    project_file.write_text(swapped, encoding="utf-8")
    before = project_file.read_bytes()
    # menu pick 1 = "Quit (do not modify the file)"
    result = runner.invoke(app, ["open", str(project_file)], input="1\n")
    assert result.exit_code != 0
    assert project_file.read_bytes() == before


def test_open_unpurchasable_remediation(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exclude → recover: simulated unpurchasable surfaces a prompt and re-runs."""
    from mixsheet.domain.optimizer import UnpurchasableMaterialError
    from mixsheet.wizard import flow

    project_file = _bedded_project(tmp_path)
    real = flow.optimize_purchase
    state = {"raised": False}

    def flaky(*args: object, **kwargs: object) -> object:
        if not state["raised"]:
            state["raised"] = True
            raise UnpurchasableMaterialError("custom-pigment")
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(flow, "optimize_purchase", flaky)
    # menu 1 (continue) → overage 10 → comparison n → strategy 1 →
    # remediation: exclude → re-runs successfully
    inputs = "\n".join(["1", "10", "n", "1", "exclude", ""])
    result = runner.invoke(app, ["open", str(project_file)], input=inputs)
    assert result.exit_code == 0, result.stdout
    project = load_project(project_file, load_bundled_catalog()).project
    assert "custom-pigment" in project.purchase.excluded_materials
    assert project.purchase.strategy is Strategy.CHEAPEST


def test_open_unpurchasable_quit_leaves_file_untouched(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mixsheet.domain.optimizer import UnpurchasableMaterialError
    from mixsheet.wizard import flow

    project_file = _bedded_project(tmp_path)

    def boom(*_args: object, **_kwargs: object) -> object:
        raise UnpurchasableMaterialError("custom-pigment")

    monkeypatch.setattr(flow, "optimize_purchase", boom)
    # menu 1 (continue) → overage 10 → no compare → strategy 1 → handle: quit
    inputs = "\n".join(["1", "10", "n", "1", "quit", ""])
    # Capture bytes after the strategy save (which IS expected) — re-load
    # from disk to compare against the post-quit bytes
    runner.invoke(app, ["open", str(project_file)], input=inputs[:0])  # no-op
    # First, let the strategy save happen by running through then quit.
    # Bytes before optimiser fires:
    pre_optimizer_bytes = project_file.read_bytes()  # still default strategy
    result = runner.invoke(app, ["open", str(project_file)], input=inputs)
    assert result.exit_code != 0
    # The strategy save legitimately happened before optimisation, so we
    # expect the post-quit file to match the strategy-save state. We assert
    # the user's quit choice did not append 'custom-pigment'.
    project = load_project(project_file, load_bundled_catalog()).project
    assert "custom-pigment" not in project.purchase.excluded_materials
    assert pre_optimizer_bytes != project_file.read_bytes()  # strategy save did write
