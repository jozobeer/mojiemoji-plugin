"""Tests for the installable Codex package copy."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "plugins" / "mojiemoji-plugin"
PACKAGE_SKILLS = PACKAGE_ROOT / "skills"
SOURCE_ONLY_SKILLS = ("bump-catalog", "mojiemoji-propose")


def test_codex_package_excludes_source_only_skills() -> None:
    for skill in SOURCE_ONLY_SKILLS:
        assert (REPO_ROOT / "skills" / skill / "SKILL.md").is_file()
        assert not (PACKAGE_SKILLS / skill).exists()


def test_codex_manifest_is_package_local_and_versioned_with_claude() -> None:
    root_manifest = REPO_ROOT / ".codex-plugin" / "plugin.json"
    package_manifest = PACKAGE_ROOT / ".codex-plugin" / "plugin.json"
    claude_manifest = REPO_ROOT / ".claude-plugin" / "plugin.json"

    assert not root_manifest.exists()
    assert json.loads(package_manifest.read_text(encoding="utf-8"))["version"] == json.loads(
        claude_manifest.read_text(encoding="utf-8")
    )["version"]


def test_codex_marketplace_targets_filtered_package() -> None:
    marketplace = json.loads(
        (REPO_ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    assert marketplace["plugins"][0]["source"]["path"] == "./plugins/mojiemoji-plugin"


def test_packaged_instructions_do_not_require_harness_root_variables() -> None:
    for skill_doc in PACKAGE_SKILLS.rglob("*.md"):
        instructions = skill_doc.read_text(encoding="utf-8")
        assert "CLAUDE_PLUGIN_ROOT" not in instructions
        assert "PLUGIN_ROOT" not in instructions


def test_packaged_prestamp_runs_from_an_unrelated_directory(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(PACKAGE_SKILLS / "mojiemoji-github" / "scripts" / "prestamp.py"),
        ],
        cwd=tmp_path,
        input="修正します。\n",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert 'alt="修正"' in proc.stdout


def test_packaged_config_runs_from_an_unrelated_directory(tmp_path: Path) -> None:
    script = PACKAGE_SKILLS / "mojiemoji-config" / "scripts" / "mojiemoji_config.py"
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "config")}

    for args in (("set", "minimal"), ("get",), ("unset",)):
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        if args == ("get",):
            assert "intensity=minimal" in proc.stdout


def test_codex_package_sync_check_matches_filtered_payload() -> None:
    proc = subprocess.run(
        [str(REPO_ROOT / "scripts" / "sync-codex-plugin-package.sh"), "--check"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
