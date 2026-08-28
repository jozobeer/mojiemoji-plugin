"""Tests for `scripts/audit-harness-skills.sh` repo-scope contracts (#144).

The script derives its repo root from its own location, so each test
copies it into a synthetic repo under tmp_path with a canonical
skills/mojiemoji-github/SKILL.md and a single checked-in adapter, then
runs it with MOJIEMOJI_AUDIT_SCOPE=repo and an empty HOME. This covers
the two contract shapes reviewers flagged as previously invisible:
backtick-delimited recommendation values (contracts 3-4) and the
schema-version marker comparison (contract 6).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit-harness-skills.sh"

CANONICAL_MARKER = "<!-- mojiemoji-schema-version: 2.2.0 -->"

CLEAN_ADAPTER = f"""---
name: mojiemoji-github
---

{CANONICAL_MARKER}

# mojiemoji-github (Codex)

Run `uvx mojiemoji` before posting.

Use the canonical `/emoji/<encoded-text>` endpoint with `font`, `color`,
`animation`, `background`, `outline`, and `outline_width`.

Recommended colors: `a855f7`, `22c55e`. Animations: `bane`, `bure`.
"""


def _synthetic_repo(tmp_path: Path, adapter_text: str) -> Path:
    """Copy the audit script into a minimal fake repo with one adapter."""
    repo = tmp_path / "repo"
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy(AUDIT_SCRIPT, scripts_dir / "audit-harness-skills.sh")
    canonical = repo / "skills" / "mojiemoji-github" / "SKILL.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text(f"# host\n\n{CANONICAL_MARKER}\n", encoding="utf-8")
    adapter = repo / "harnesses" / "codex" / "mojiemoji-github" / "SKILL.md"
    adapter.parent.mkdir(parents=True)
    adapter.write_text(adapter_text, encoding="utf-8")
    return repo


def _run_audit(tmp_path: Path, adapter_text: str) -> subprocess.CompletedProcess[str]:
    repo = _synthetic_repo(tmp_path, adapter_text)
    empty_home = tmp_path / "home"
    empty_home.mkdir()
    env = {**os.environ, "MOJIEMOJI_AUDIT_SCOPE": "repo", "HOME": str(empty_home)}
    return subprocess.run(
        ["bash", str(repo / "scripts" / "audit-harness-skills.sh")],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


class TestRepoScopeContracts:
    def test_clean_adapter_passes(self, tmp_path):
        result = _run_audit(tmp_path, CLEAN_ADAPTER)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_prohibition_wording_is_not_a_recommendation(self, tmp_path):
        prohibition = CLEAN_ADAPTER + "\nNever use `spring`; use `poyoon` instead.\n"
        result = _run_audit(tmp_path, prohibition)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_backticked_forbidden_color_fails(self, tmp_path):
        result = _run_audit(tmp_path, CLEAN_ADAPTER.replace("`a855f7`", "`dc2626`"))
        assert result.returncode == 1
        assert "dc2626" in result.stdout

    def test_backticked_bad_animation_fails(self, tmp_path):
        result = _run_audit(tmp_path, CLEAN_ADAPTER.replace("`bane`", "`spring`"))
        assert result.returncode == 1
        assert "spring" in result.stdout

    def test_missing_uvx_mojiemoji_reference_fails(self, tmp_path):
        no_invocation = CLEAN_ADAPTER.replace("Run `uvx mojiemoji` before posting.", "")
        result = _run_audit(tmp_path, no_invocation)
        assert result.returncode == 1
        assert "uvx mojiemoji" in result.stdout

    def test_stale_schema_marker_fails(self, tmp_path):
        stale = CLEAN_ADAPTER.replace("2.2.0", "1.0.0")
        result = _run_audit(tmp_path, stale)
        assert result.returncode == 1
        assert "Schema version drift" in result.stdout

    def test_missing_schema_marker_fails(self, tmp_path):
        unmarked = CLEAN_ADAPTER.replace(f"{CANONICAL_MARKER}\n\n", "")
        result = _run_audit(tmp_path, unmarked)
        assert result.returncode == 1
        assert "Missing mojiemoji-schema-version marker" in result.stdout
