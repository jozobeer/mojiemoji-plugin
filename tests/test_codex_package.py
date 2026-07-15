"""Tests for the installable Codex package copy."""

from __future__ import annotations

from fnmatch import fnmatchcase
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "plugins" / "mojiemoji-plugin"
PACKAGE_SKILLS = PACKAGE_ROOT / "skills"
SOURCE_ONLY_SKILLS = ("bump-catalog", "mojiemoji-propose")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )


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


def test_config_skill_allows_quoted_and_unquoted_script_paths() -> None:
    skill = (REPO_ROOT / "skills" / "mojiemoji-config" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    frontmatter = yaml.safe_load(skill.split("---", 2)[1])
    allowed_tools = frontmatter["allowed-tools"]
    commands = (
        "Bash(python3 /tmp/mojiemoji-config/scripts/mojiemoji_config.py get)",
        'Bash(python3 "/tmp/mojiemoji-config/scripts/mojiemoji_config.py" get)',
    )

    for command in commands:
        assert any(fnmatchcase(command, pattern) for pattern in allowed_tools), command


@pytest.mark.parametrize(
    "changed_path",
    [
        ".agents/plugins/marketplace.json",
        "plugins/mojiemoji-plugin/.codex-plugin/plugin.json",
    ],
)
@pytest.mark.parametrize(("head_version", "expected_returncode"), [("1.0.0", 1), ("1.0.1", 0)])
def test_version_bump_guard_covers_codex_package_paths(
    tmp_path: Path,
    changed_path: str,
    head_version: str,
    expected_returncode: int,
) -> None:
    manifest = tmp_path / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"version": "1.0.0"}) + "\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "initial")
    base_sha = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    changed = tmp_path / changed_path
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("{}\n", encoding="utf-8")
    manifest.write_text(json.dumps({"version": head_version}) + "\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "package change")
    head_sha = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    proc = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "check-version-bump.sh")],
        cwd=tmp_path,
        env={**os.environ, "BASE_SHA": base_sha, "HEAD_SHA": head_sha},
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert proc.returncode == expected_returncode, proc.stdout + proc.stderr


def test_codex_package_sync_check_matches_filtered_payload() -> None:
    cache_dir = PACKAGE_SKILLS / "mojiemoji-github" / "scripts" / "__pycache__"
    cache_file = cache_dir / "codex_package_sync_test.pyc"
    cache_dir.mkdir(exist_ok=True)
    cache_file.write_bytes(b"runtime cache")

    try:
        proc = subprocess.run(
            [str(REPO_ROOT / "scripts" / "sync-codex-plugin-package.sh"), "--check"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        cache_file.unlink(missing_ok=True)
        try:
            cache_dir.rmdir()
        except OSError:
            pass
