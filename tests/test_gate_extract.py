"""Pre-validator extract / routing tests for the gate.

Covers what reaches the validator pipeline:
- tool-name filtering (`Bash` vs MCP routing patterns)
- `gh edit` subcommand inclusion in the inspect set
- Japanese-language detection (English-only bodies bypass)
- body-file / script-file / `--input` payload inspection
- `hooks/hooks.json` matcher coverage (production routing boundary)

`MOJIEMOJI_HOOK_DISABLED` bypass markers live in `test_gate_bypass.py`;
LGTM `![]()` image extraction lives in `test_gate_url_presence.py`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest

from conftest import HOOK, stamp_url

JP_BODY = "これは日本語の本文です。"


class TestToolFiltering:
    """The gate should exit 0 for any tool we don't care about."""

    def test_unrelated_tool_is_allowed(self, run_hook):
        result = run_hook({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
        assert result.returncode == 0

    def test_empty_command_is_allowed(self, run_hook):
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": ""}})
        assert result.returncode == 0

    def test_non_posting_gh_is_allowed(self, run_hook):
        # `gh pr view` is a read-only operation, not in GH_HIGH_RE.
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr view 123 --comments # {JP_BODY}'}}
        )
        assert result.returncode == 0

    def test_missing_fields_is_allowed(self, run_hook):
        # `{}` parses fine but lacks `tool_name` — fail-open on missing fields.
        result = run_hook({})
        assert result.returncode == 0

    def test_unparseable_stdin_is_allowed(self, tmp_path):
        # The hook should never crash a tool call on its own bug.
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=b"not json at all {{{",
            capture_output=True,
            cwd=str(tmp_path),
            timeout=10,
        )
        assert result.returncode == 0


class TestGhEditVariants:
    """`edit` subcommands accept body inputs (`--body`, `--notes`, etc.)
    and must trip the gate just like `create` / `comment` / `review`."""

    def test_gh_issue_edit_with_japanese_body_is_blocked(self, run_hook):
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh issue edit 123 --body "{JP_BODY}"'}}
        )
        assert result.returncode == 2

    def test_gh_pr_edit_with_japanese_body_is_blocked(self, run_hook):
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr edit 123 --body "{JP_BODY}"'}}
        )
        assert result.returncode == 2

    def test_gh_release_edit_with_japanese_notes_is_blocked(self, run_hook):
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh release edit v1.0.0 --notes "{JP_BODY}"'}}
        )
        assert result.returncode == 2


class TestLanguageFiltering:
    """English-only bodies bypass the gate."""

    def test_english_body_is_allowed(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'gh pr create --title "x" --body "English only PR body"'},
            }
        )
        assert result.returncode == 0


class TestFileInspection:
    """File-routed bodies are inspected just like inline ones."""

    def test_body_file_with_bad_url_blocks(self, run_hook, tmp_path):
        bad_url = stamp_url().replace("font=gothic-bold&", "")
        (tmp_path / "body.md").write_text(f'{JP_BODY} <img src="{bad_url}">')
        cmd = "gh pr create --title x --body-file body.md"
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, cwd=tmp_path)
        assert result.returncode == 2

    def test_gh_api_input_with_bad_url_blocks(self, run_hook, tmp_path):
        bad_url = stamp_url().replace("font=gothic-bold&", "")
        payload = {"body": f'{JP_BODY} <img src="{bad_url}">'}
        # Real triage-review-style scripts write raw UTF-8 JP, not
        # `\uXXXX` escapes — `ensure_ascii=False` is the idiomatic
        # choice for human-readable bodies inside a JSON file.
        (tmp_path / "payload.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        cmd = "gh api repos/o/r/issues -X POST --input payload.json"
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, cwd=tmp_path)
        assert result.returncode == 2

    def test_script_body_with_bad_url_blocks(self, run_hook, tmp_path):
        # The 2026-05-12 triage-review failure: hand-crafted URLs in a
        # Python helper script that wrote out.json, then `gh api --input`
        # POSTed it. The hook reads the script body to catch this.
        bad_url = stamp_url().replace("font=gothic-bold&", "")
        (tmp_path / "build.py").write_text(
            f'body = "{JP_BODY} <img src=\\"{bad_url}\\">"\n'
        )
        cmd = "python3 build.py && gh api repos/o/r/issues -X POST --input out.json"
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, cwd=tmp_path)
        assert result.returncode == 2


class TestMatcherCoverage:
    """`hooks/hooks.json` matcher coverage — names not matching here never
    reach the hook regardless of how robust the hook logic is."""

    @pytest.fixture(scope="class")
    def matcher(self):
        config = json.loads((HOOK.parent / "hooks.json").read_text())
        return re.compile(config["hooks"]["PreToolUse"][0]["matcher"])

    @pytest.mark.parametrize(
        "tool_name",
        [
            "Bash",
            "mcp__github__github_create_pull_request",
            "mcp__mcpm_profile_base__github_add_issue_comment",
            "mcp__gh__github_pull_request_review_write",
        ],
    )
    def test_routed_to_hook(self, matcher, tool_name):
        assert matcher.search(tool_name), f"{tool_name} should be routed to the hook"

    @pytest.mark.parametrize(
        "tool_name",
        [
            "Read",
            "Edit",
            "mcp__octo__create_pull_request",  # alias without `github` — NOT routed
            "mcp__forgejo__pull_request_review_write",
            "mcp__notion__create_page",
        ],
    )
    def test_not_routed_to_hook(self, matcher, tool_name):
        assert not matcher.search(tool_name), f"{tool_name} should NOT be routed to the hook"
