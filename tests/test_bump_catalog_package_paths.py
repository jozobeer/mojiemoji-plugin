"""Regression tests for bump-catalog's generated package allowlist."""

from __future__ import annotations

import runpy
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"
BUMP_CATALOG = SCRIPTS / "bump_catalog.py"
SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync-codex-plugin-package.sh"


def test_bump_catalog_allows_all_synced_package_skill_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = runpy.run_path(str(BUMP_CATALOG))
    package_dir = tmp_path / "plugins" / "mojiemoji-plugin"
    (package_dir / ".codex-plugin").mkdir(parents=True)
    (package_dir / "skills").mkdir()
    (package_dir / "packages" / "mojiemoji-core" / "src").mkdir(parents=True)

    intended = set(
        module["package_mutation_paths"](package_dir, tmp_path, SYNC_SCRIPT)
    )

    assert module["intended_path"](
        "plugins/mojiemoji-plugin/skills/mojiemoji-config/SKILL.md",
        intended,
    )
    # The payload vendors the core too; leaving it off the allowlist made
    # the dirty-tree guard refuse every catalog PR the sync touched.
    assert module["intended_path"](
        "plugins/mojiemoji-plugin/packages/mojiemoji-core/src/mojiemoji/data/"
        "prestamp-catalog.yml",
        intended,
    )
    assert not module["intended_path"]("skills/unrelated/SKILL.md", intended)


def test_package_allowlist_tracks_the_sync_scripts_payload_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every path the sync script declares must be allowlisted."""
    monkeypatch.syspath_prepend(str(SCRIPTS))
    module = runpy.run_path(str(BUMP_CATALOG))
    declared = subprocess.run(
        [str(SYNC_SCRIPT), "--payload-paths"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    package_dir = tmp_path / "plugins" / "mojiemoji-plugin"
    for rel in declared:
        (package_dir / rel).mkdir(parents=True)

    intended = set(
        module["package_mutation_paths"](package_dir, tmp_path, SYNC_SCRIPT)
    )

    assert intended == {f"plugins/mojiemoji-plugin/{rel}" for rel in declared}
