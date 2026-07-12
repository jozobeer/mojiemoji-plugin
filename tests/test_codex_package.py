"""Tests for the installable Codex package copy."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_SKILLS = REPO_ROOT / "plugins" / "mojiemoji-plugin" / "skills"


def test_codex_package_excludes_claude_only_propose_skill() -> None:
    assert (REPO_ROOT / "skills" / "mojiemoji-propose" / "SKILL.md").is_file()
    assert not (PACKAGE_SKILLS / "mojiemoji-propose").exists()


def test_codex_package_sync_check_matches_filtered_payload() -> None:
    proc = subprocess.run(
        [str(REPO_ROOT / "scripts" / "sync-codex-plugin-package.sh"), "--check"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
