"""Regression tests for bump-catalog's generated package allowlist."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"
BUMP_CATALOG = SCRIPTS / "bump_catalog.py"


def test_bump_catalog_allows_all_synced_package_skill_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = runpy.run_path(str(BUMP_CATALOG))
    package_dir = tmp_path / "plugins" / "mojiemoji-plugin"
    (package_dir / ".codex-plugin").mkdir(parents=True)
    (package_dir / "skills").mkdir()

    intended = set(module["package_mutation_paths"](package_dir, tmp_path))

    assert module["intended_path"](
        "plugins/mojiemoji-plugin/skills/mojiemoji-config/SKILL.md",
        intended,
    )
    assert not module["intended_path"]("skills/unrelated/SKILL.md", intended)
