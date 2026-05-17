"""Tests for hooks/mojiemoji_md_edit_warn.py.

The PostToolUse hook never blocks — it only writes a unified diff to
stderr when a documentation `*.md` would change under prestamp. Exit
code is always 0. These tests verify three properties:

  1. Match scope: only documentation paths trigger inspection.
  2. Silence: matching files with no Japanese, no drift, or
     fully-escaped content produce no output.
  3. Drift detection: a matching file that would change under
     prestamp emits a diff with the suggested transform.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "hooks" / "mojiemoji_md_edit_warn.py"


def _run(payload: dict, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env={"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        timeout=15,
    )


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / ".claude-plugin").mkdir()
    return tmp_path


def test_warn_hook_ignores_non_md_files(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    target = repo / "code.py"
    target.write_text("# 修正のメモ\nprint('ok')\n")
    result = _run(
        {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}, cwd=repo
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_warn_hook_ignores_unmatched_md_paths(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    # `notes/foo.md` is not in the documentation glob list (no docs/ prefix).
    notes = repo / "notes"
    notes.mkdir()
    target = notes / "scratch.md"
    target.write_text("修正と確認のメモ。\n")
    result = _run(
        {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}, cwd=repo
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_warn_hook_silent_for_english_only_readme(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    target = repo / "README.md"
    target.write_text("# Hello\n\nJust English here.\n")
    result = _run(
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}}, cwd=repo
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_warn_hook_silent_when_already_prestamped(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    target = repo / "README.md"
    # Run prestamp first so the file already contains <img> stamps — a
    # second run is idempotent.
    raw = "修正の確認をしました。\n"
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "skills/mojiemoji-github/scripts/prestamp.py")],
        input=raw, capture_output=True, text=True, timeout=10,
    )
    target.write_text(proc.stdout)
    result = _run(
        {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}, cwd=repo
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_warn_hook_emits_diff_for_documentation_drift(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    target = repo / "README.md"
    target.write_text("修正の確認をします。\n")
    result = _run(
        {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}, cwd=repo
    )
    assert result.returncode == 0
    assert "prestamp drift detected" in result.stderr
    assert "README.md" in result.stderr
    assert "<img" in result.stderr  # the proposed diff carries stamps


def test_warn_hook_silent_when_full_file_escaped(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    target = repo / "README.md"
    target.write_text(
        "<!-- mojiemoji:off -->\n"
        "修正の確認をします。\n"
        "<!-- mojiemoji:on -->\n"
    )
    result = _run(
        {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}, cwd=repo
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_warn_hook_matches_skill_md_paths(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    skill_dir = repo / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    target = skill_dir / "SKILL.md"
    target.write_text("修正の確認。\n")
    result = _run(
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}}, cwd=repo
    )
    assert result.returncode == 0
    assert "prestamp drift detected" in result.stderr
