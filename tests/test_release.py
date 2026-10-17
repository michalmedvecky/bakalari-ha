"""Kontroly shody verze a obsahu připravovaného vydání."""

import json
from pathlib import Path

import pytest

from scripts.release_notes import release_notes


@pytest.fixture
def project(tmp_path):
    component = tmp_path / "custom_components/bakalari"
    component.mkdir(parents=True)
    (component / "manifest.json").write_text(json.dumps({"version": "1.0.0"}))
    (tmp_path / "CHANGELOG.md").write_text(
        "# Přehled změn\n\n## Připravuje se\n\nNávrhy.\n\n"
        "## 1.0.0 — 2026-10-17\n\nPrvní vydání.\n\n### Funkce\n\n- Integrace.\n\n"
        "## 0.9.0\n\nStaré vydání.\n"
    )
    return tmp_path


def test_current_release_notes(project):
    result = release_notes(project, "v1.0.0")
    assert result.startswith("První vydání.")
    assert "### Funkce" in result
    assert "Staré vydání" not in result
    assert "Návrhy" not in result


@pytest.mark.parametrize("tag", ["v1.0.1", "1.0.0", "v1.0.0-test"])
def test_tag_must_match_manifest(project, tag):
    with pytest.raises(ValueError, match="manifestu"):
        release_notes(project, tag)


def test_changelog_section_required(project):
    (project / "CHANGELOG.md").write_text("# Přehled změn\n")
    with pytest.raises(ValueError, match="poznámky"):
        release_notes(project, "v1.0.0")


def test_repository_release_is_consistent():
    root = Path(__file__).resolve().parents[1]
    version = json.loads(
        (root / "custom_components/bakalari/manifest.json").read_text()
    )["version"]
    assert release_notes(root, f"v{version}")
