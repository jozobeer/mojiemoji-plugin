"""`MOJIEMOJI_HOOK_DISABLED=1` bypass-marker tests.

The marker opts out, but only on the surface the caller controls —
Bash command prefix or MCP top-level body. It must NOT leak from
fixture / documentation files that the hook reads.

Exit code contract: 0 → allow, 2 → block.
"""

from __future__ import annotations

JP_BODY = "これは日本語の本文です。"


class TestBypass:
    def test_bash_bypass_prefix(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f'MOJIEMOJI_HOOK_DISABLED=1 gh issue create --title "x" --body "{JP_BODY}"'
                },
            }
        )
        assert result.returncode == 0

    def test_mcp_bypass_in_body(self, run_hook):
        result = run_hook(
            {
                "tool_name": "mcp__github__github_add_issue_comment",
                "tool_input": {"body": f"MOJIEMOJI_HOOK_DISABLED=1 {JP_BODY}"},
            }
        )
        assert result.returncode == 0

    def test_bash_bypass_must_be_in_command_not_body_file(self, run_hook, tmp_path):
        # MOJIEMOJI_HOOK_DISABLED inside a referenced file should NOT count —
        # otherwise documentation prose or fixtures mentioning the literal
        # would silently disable the gate.
        body_file = tmp_path / "body.md"
        body_file.write_text(f"MOJIEMOJI_HOOK_DISABLED=1 {JP_BODY}")
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh issue create --title "x" --body-file {body_file}'},
            },
            cwd=tmp_path,
        )
        assert result.returncode == 2, "bypass marker leaked from body file"

    def test_legacy_hook_disable_no_longer_bypasses(self, run_hook):
        # `HOOK_DISABLE=1` was deprecated in v0.x and removed in v0.21.0.
        # Must now be treated as plain text and NOT bypass the gate.
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f'HOOK_DISABLE=1 gh issue create --title "x" --body "{JP_BODY}"'
                },
            }
        )
        assert result.returncode == 2, "legacy HOOK_DISABLE=1 must no longer bypass"
