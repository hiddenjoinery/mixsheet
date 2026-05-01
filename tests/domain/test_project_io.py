"""Project file load/save, version mismatch detection, default-excluded seed."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from mixsheet.domain import (
    CatalogVersionMismatch,
    Component,
    DimensionsVolume,
    DirectVolume,
    Project,
    ProjectFileError,
    PurchaseConfig,
    load_bundled_catalog,
    load_project,
    new_project,
    save_project,
)

if TYPE_CHECKING:
    from pathlib import Path


NORMATIVE_PROJECT_YAML = dedent(
    """\
    schema_version: 1
    project:
      id: router-gantry-2026-05
      name: Router gantry
      shape: machine
      created_at: 2026-05-01T14:22:00Z
      updated_at: 2026-05-01T15:08:00Z

    components:
      - id: bed
        name: Machine bed
        quantity: 1
        volume:
          mode: dimensions
          length_mm: 800
          width_mm: 400
          height_mm: 120
        preset_id: epoxy-mix
        preset_version: "1.1.0"

      - id: cross-slide
        name: Cross slide
        quantity: 1
        volume:
          mode: area_height
          area_mm2: 240000
          height_mm: 80
        preset_id: gantry-beam-dynamic-fill
        preset_version: "1.0.0"

    purchase:
      overage_pct: 0.10
      strategy: cheapest
      excluded_materials: [water]
    """,
)


class TestProjectRoundTrip:
    def test_round_trips_the_normative_example(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        original_path = tmp_path / "project.yaml"
        original_path.write_text(NORMATIVE_PROJECT_YAML, encoding="utf-8")

        result = load_project(original_path, catalog)
        assert not result.mismatches

        saved_path = tmp_path / "project-saved.yaml"
        save_project(result.project, saved_path)
        saved_text = saved_path.read_text(encoding="utf-8")
        assert "volume_l: 38" not in saved_text
        assert "net_volume_l" not in saved_text

        reloaded = load_project(saved_path, catalog)
        assert reloaded.project.name == result.project.name
        assert reloaded.project.shape == result.project.shape
        assert len(reloaded.project.components) == 2
        assert reloaded.project.components[0].volume.volume_l == Decimal("38.4")
        assert reloaded.project.components[1].volume.volume_l == Decimal("19.2")
        assert reloaded.project.purchase.excluded_materials == ["water"]
        assert reloaded.project.purchase.overage_pct == Decimal("0.10")

    def test_updates_updated_at_on_save(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        path = tmp_path / "project.yaml"
        path.write_text(NORMATIVE_PROJECT_YAML, encoding="utf-8")
        result = load_project(path, catalog)
        before = result.project.updated_at

        out_path = tmp_path / "project-saved.yaml"
        wall_clock_before = datetime.now(UTC)
        refreshed = save_project(result.project, out_path)
        wall_clock_after = datetime.now(UTC)

        assert refreshed.updated_at != before
        assert wall_clock_before <= refreshed.updated_at <= wall_clock_after

    def test_rejects_a_payload_with_the_wrong_schema_version(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        bad = NORMATIVE_PROJECT_YAML.replace("schema_version: 1", "schema_version: 2")
        path = tmp_path / "bad.yaml"
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(ProjectFileError):
            load_project(path, catalog)


class TestVersionMismatchDetection:
    def test_returns_no_mismatches_for_an_aligned_project(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        path = tmp_path / "project.yaml"
        path.write_text(NORMATIVE_PROJECT_YAML, encoding="utf-8")
        result = load_project(path, catalog)
        assert result.mismatches == []

    def test_reports_a_mismatched_preset_version(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        bumped = NORMATIVE_PROJECT_YAML.replace(
            'preset_id: epoxy-mix\n    preset_version: "1.1.0"',
            'preset_id: epoxy-mix\n    preset_version: "1.0.0"',
        )
        assert "1.0.0" in bumped.split("epoxy-mix", 1)[1].split("\n", 2)[1]
        path = tmp_path / "project.yaml"
        path.write_text(bumped, encoding="utf-8")
        result = load_project(path, catalog)
        assert result.mismatches == [
            CatalogVersionMismatch(
                component_id="bed",
                preset_id="epoxy-mix",
                pinned_version="1.0.0",
                catalog_version="1.1.0",
            ),
        ]


class TestDefaultExcludedSeed:
    def test_seeds_water_on_a_new_project(self) -> None:
        catalog = load_bundled_catalog()
        components = [
            Component(
                id="bed",
                name="Bed",
                quantity=1,
                volume=DirectVolume(volume_l=Decimal("5")),
                preset_id="epoxy-mix",
                preset_version="1.1.0",
            ),
        ]
        project = new_project("Lathe bed", "single", components, catalog)
        assert "water" in project.purchase.excluded_materials

    def test_preserves_a_hand_edited_excluded_list(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        edited = NORMATIVE_PROJECT_YAML.replace(
            "excluded_materials: [water]",
            "excluded_materials: []",
        )
        path = tmp_path / "project.yaml"
        path.write_text(edited, encoding="utf-8")
        result = load_project(path, catalog)
        assert result.project.purchase.excluded_materials == []


class TestProjectFileErrors:
    def test_rejects_non_mapping_top_level(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        path = tmp_path / "p.yaml"
        path.write_text("- 1\n- 2\n", encoding="utf-8")
        with pytest.raises(ProjectFileError, match="must be a mapping"):
            load_project(path, catalog)

    def test_rejects_missing_schema_version(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        path = tmp_path / "p.yaml"
        path.write_text("project:\n  id: x\n", encoding="utf-8")
        with pytest.raises(ProjectFileError, match="schema_version"):
            load_project(path, catalog)

    def test_rejects_non_mapping_project_block(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        path = tmp_path / "p.yaml"
        path.write_text("schema_version: 1\nproject: not-a-mapping\n", encoding="utf-8")
        with pytest.raises(ProjectFileError, match="'project' must be a mapping"):
            load_project(path, catalog)

    def test_rejects_yaml_parse_error(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        path = tmp_path / "p.yaml"
        path.write_text("not: : valid\n  yaml: ::\n", encoding="utf-8")
        with pytest.raises(ProjectFileError, match="YAML parse error"):
            load_project(path, catalog)

    def test_unknown_preset_id_does_not_produce_mismatch(self, tmp_path: Path) -> None:
        catalog = load_bundled_catalog()
        modified = NORMATIVE_PROJECT_YAML.replace(
            "preset_id: epoxy-mix",
            "preset_id: ghost-preset",
        )
        path = tmp_path / "project.yaml"
        path.write_text(modified, encoding="utf-8")
        result = load_project(path, catalog)
        assert all(m.preset_id != "ghost-preset" for m in result.mismatches)


def test_save_uses_deterministic_sorted_keys(tmp_path: Path) -> None:
    components = [
        Component(
            id="bed",
            name="Bed",
            quantity=1,
            volume=DimensionsVolume(
                length_mm=Decimal("800"),
                width_mm=Decimal("400"),
                height_mm=Decimal("120"),
            ),
            preset_id="epoxy-mix",
            preset_version="1.1.0",
        ),
    ]
    project = Project(
        id="p1",
        name="P1",
        shape="single",
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, tzinfo=UTC),
        components=components,
        purchase=PurchaseConfig(),
    )
    path = tmp_path / "p.yaml"
    save_project(project, path)
    text = path.read_text(encoding="utf-8")
    assert "components:" in text
    assert "purchase:" in text
    assert "schema_version:" in text
