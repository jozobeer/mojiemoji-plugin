"""Gate behavior for decorated PR bodies on leaking repos (issue #138).

The PR-body policy gate has two distinct jobs:

- **Passive skip** — an *undecorated* Japanese PR body on a leaking /
  undetectable repo is allowed through without forcing decoration, so
  the body stays clean of HTML that would bleed into commit history.
- **Active block** — a *decorated* PR body on a *confirmed-leaking* repo
  is rejected (exit 2), because those stamps would land in the
  squash/merge commit message. UNKNOWN repos are NOT blocked (we don't
  reject on a guess) — they fall through to normal stamp validation.

These tests also cover the target-repo resolution (`-R owner/repo`, MCP
`owner`/`repo`) and the per-path FORCE escape hatch.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from conftest import stamp_img

JP_PARAGRAPH = "これは日本語のPR本文で、ちゃんとした装飾済みのスタンプが含まれています。"


def _seed_policy(xdg_cache_home: Path, *, owner: str, repo: str, squash: str, merge: str) -> None:
    path = xdg_cache_home / "mojiemoji" / "repo-policy" / f"{owner}--{repo}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "squash_merge_commit_message": squash,
                "merge_commit_message": merge,
                "allow_squash_merge": True,
                "allow_merge_commit": True,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        encoding="utf-8",
    )


class TestDecoratedLeakBlock:
    """Decorated PR body on a confirmed-leaking repo is blocked."""

    def test_bash_decorated_pr_body_blocks_on_leaking_repo(self, run_hook, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        _seed_policy(tmp_path, owner="o", repo="r", squash="PR_BODY", merge="PR_TITLE")
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh pr create -R o/r --title "x" --body "{body}"'},
            }
        )
        assert result.returncode == 2, result.stderr
        assert "#138" in result.stderr

    def test_force_prefix_bypasses_leak_block(self, run_hook, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        _seed_policy(tmp_path, owner="o", repo="r", squash="PR_BODY", merge="PR_TITLE")
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f'MOJIEMOJI_FORCE_PR_BODY=1 gh pr create -R o/r --body "{body}"',
                },
            }
        )
        assert result.returncode == 0, result.stderr

    def test_decorated_pr_body_allowed_on_safe_repo(self, run_hook, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        _seed_policy(tmp_path, owner="o", repo="r", squash="BLANK", merge="PR_TITLE")
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh pr create -R o/r --body "{body}"'},
            }
        )
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize(
        "flag",
        ["-R o/r", "--repo o/r", "--repo=o/r", "-R github.com/o/r"],
    )
    def test_repo_flag_forms_resolve_target(self, run_hook, tmp_path, monkeypatch, flag):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        _seed_policy(tmp_path, owner="o", repo="r", squash="PR_BODY", merge="PR_TITLE")
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh pr create {flag} --body "{body}"'},
            }
        )
        assert result.returncode == 2, result.stderr

    def test_undecorated_pr_body_skipped_on_leaking_repo(self, run_hook, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        _seed_policy(tmp_path, owner="o", repo="r", squash="PR_BODY", merge="PR_TITLE")
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'gh pr create -R o/r --body "これは日本語の本文です。"'},
            }
        )
        assert result.returncode == 0, result.stderr


class TestMcpTargetRepo:
    """MCP create_pull_request resolves owner/repo from tool_input."""

    def test_mcp_decorated_pr_body_blocks_on_leaking_repo(self, run_hook, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        _seed_policy(tmp_path, owner="o", repo="r", squash="PR_BODY", merge="PR_TITLE")
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {
                "tool_name": "mcp__github__github_create_pull_request",
                "tool_input": {"owner": "o", "repo": "r", "body": body},
            }
        )
        assert result.returncode == 2, result.stderr
        assert "#138" in result.stderr

    def test_mcp_force_marker_in_body_bypasses_leak_block(self, run_hook, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        _seed_policy(tmp_path, owner="o", repo="r", squash="PR_BODY", merge="PR_TITLE")
        body = f"MOJIEMOJI_FORCE_PR_BODY=1\n{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {
                "tool_name": "mcp__github__github_create_pull_request",
                "tool_input": {"owner": "o", "repo": "r", "body": body},
            }
        )
        assert result.returncode == 0, result.stderr
