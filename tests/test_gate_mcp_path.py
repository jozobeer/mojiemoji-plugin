"""MCP routing + body-field tests for the gate.

MCP tools surface a structured `tool_input` dict, so the extract layer
pulls each `BODY_FIELDS` value (notably `body` plus nested
`comments[].body`) and feeds them through the same validator pipeline
as Bash bodies. Coverage:

- matcher-bound and matcher-untouched MCP tool names
- decorated vs undecorated body fields
- read-only MCP tools with no body
- per-comment `body` independent enforcement
- `gh api --input` payloads that mirror MCP-shaped JSON
- non-body fields (title / label) explicitly out of scope

Exit code contract: 0 → allow, 2 → block.
"""

from __future__ import annotations

import json

import pytest

from conftest import stamp_img

JP_BODY = "これは日本語の本文です。"
JP_PARAGRAPH = (
    "これは日本語のPR本文で、ちゃんとした装飾済みのスタンプが含まれています。"
)


class TestMcpPath:
    """MCP GitHub tools are gated identically for each body field."""

    # Names that Claude Code's matcher (`hooks/hooks.json`) actually routes
    # to the hook today (pattern: `Bash|mcp__.*github.*`). Production
    # coverage is bounded by this matcher — names not matching it never
    # reach the hook.
    @pytest.mark.parametrize(
        "tool_name",
        [
            "mcp__github__github_create_pull_request",
            "mcp__mcpm_profile_base__github_add_issue_comment",
            "mcp__gh__github_pull_request_review_write",
        ],
    )
    def test_undecorated_jp_body_blocks(self, run_hook, tool_name):
        result = run_hook({"tool_name": tool_name, "tool_input": {"body": JP_BODY}})
        assert result.returncode == 2, f"{tool_name} should have been blocked"

    # Defense-in-depth: if a future matcher broadens to non-`github`
    # aliases (`mcp__octo__*`, etc.), the hook logic itself must still
    # recognize the GH operation suffix.
    @pytest.mark.parametrize(
        "tool_name",
        [
            "mcp__octo__create_pull_request",
            "mcp__octo__pull_request_review_write",
            "mcp__octo__issue_write",
            "mcp__octo__add_issue_comment",
        ],
    )
    def test_aliased_server_name_blocks_when_routed(self, run_hook, tool_name):
        result = run_hook({"tool_name": tool_name, "tool_input": {"body": JP_BODY}})
        assert result.returncode == 2, f"{tool_name} should have been blocked"

    def test_decorated_jp_body_passes(self, run_hook):
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {"tool_name": "mcp__github__github_create_pull_request", "tool_input": {"body": body}}
        )
        assert result.returncode == 0, result.stderr

    def test_read_only_mcp_tool_no_body_passes(self, run_hook):
        # `github_pull_request_read` matches the regex but carries no
        # body field — the gate should not invent a violation.
        result = run_hook(
            {
                "tool_name": "mcp__github__github_pull_request_read",
                "tool_input": {"owner": "o", "repo": "r", "pull_number": 1},
            }
        )
        assert result.returncode == 0

    def test_review_comment_without_own_stamp_blocks(self, run_hook):
        # `pull_request_review_write` carries a top-level body plus
        # inline `comments[].body`. Each body field is its own GitHub
        # prose surface; a stamped summary must not cover un-stamped
        # inline findings.
        result = run_hook(
            {
                "tool_name": "mcp__github__github_pull_request_review_write",
                "tool_input": {
                    "body": f"{JP_PARAGRAPH} {stamp_img()}",
                    "comments": [
                        {"path": "x.py", "line": 1, "body": "ここは型エラーです"},
                        {"path": "y.py", "line": 2, "body": "余分な引数があります"},
                    ],
                },
            }
        )
        assert result.returncode == 2, "comments[].body must be decorated independently"

    def test_review_with_decorated_comments_passes(self, run_hook):
        result = run_hook(
            {
                "tool_name": "mcp__github__github_pull_request_review_write",
                "tool_input": {
                    "body": f"{JP_PARAGRAPH} {stamp_img()}",
                    "comments": [
                        {"path": "x.py", "line": 1, "body": f"ここは型エラーです {stamp_img(text='型')}"},
                        {"path": "y.py", "line": 2, "body": f"余分な引数があります {stamp_img(text='余分')}"},
                    ],
                },
            }
        )
        assert result.returncode == 0, result.stderr

    def test_gh_api_input_review_comments_require_own_stamp(self, run_hook, tmp_path):
        payload = tmp_path / "review.json"
        payload.write_text(
            json.dumps(
                {
                    "body": f"{JP_PARAGRAPH} {stamp_img()}",
                    "comments": [{"path": "x.py", "line": 1, "body": "ここは型エラーです"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f"gh api repos/o/r/pulls/1/reviews --input {payload}"}},
            cwd=tmp_path,
        )
        assert result.returncode == 2

    def test_gh_api_input_review_with_decorated_comments_passes(self, run_hook, tmp_path):
        # Regression for #112: `read_body_files` previously joined
        # extracted JSON body pieces into a single string and `_route_bash`
        # extended a list with it, splitting Japanese into per-character
        # surfaces. Each char then had 0 mojiemoji URLs and the gate
        # falsely blocked properly-decorated review payloads.
        payload = tmp_path / "review.json"
        payload.write_text(
            json.dumps(
                {
                    "body": f"{JP_PARAGRAPH} {stamp_img()}",
                    "comments": [
                        {"path": "x.py", "line": 1, "body": f"型エラーです {stamp_img(text='型')}"},
                        {"path": "y.py", "line": 2, "body": f"余分な引数です {stamp_img(text='余分')}"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f"gh api repos/o/r/pulls/1/reviews --input {payload}"}},
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr

    def test_japanese_title_with_decorated_body_file_passes(self, run_hook, tmp_path):
        # Regression for #112: Japanese in non-body flag values
        # (`--title "日本語…"`) should not trip the gate. Only
        # body-class surfaces are inspected per BODY_FIELDS policy.
        body_md = tmp_path / "body.md"
        body_md.write_text(f"{JP_PARAGRAPH} {stamp_img()}")
        cmd = f'gh pr create --title "日本語タイトル" --body-file {body_md}'
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, cwd=tmp_path)
        assert result.returncode == 0, result.stderr

    def test_japanese_title_variable_assignment_with_decorated_body_passes(
        self,
        run_hook,
        tmp_path,
    ):
        # Regression for #140: a shell prelude variable can feed a
        # non-body flag. The assignment line itself is still metadata,
        # not posting prose, when that variable is consumed by `--title`.
        body_md = tmp_path / "body.md"
        body_md.write_text(f"{JP_PARAGRAPH} {stamp_img()}")
        cmd = f"""title='日本語タイトル'
gh issue create --title "$title" --body-file {body_md}"""
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, cwd=tmp_path)
        assert result.returncode == 0, result.stderr

    def test_body_variable_assignment_reused_as_title_still_blocks(self, run_hook):
        # If a variable is also used by a body-class flag, keep the
        # assignment inspectable so variable-routed body prose cannot
        # bypass the gate.
        cmd = f"""text='{JP_BODY}'
gh issue create --title "$text" --body "$text" """
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}})
        assert result.returncode == 2

    def test_japanese_label_with_decorated_body_passes(self, run_hook, tmp_path):
        # `--label "バグ"` is metadata, not posting prose.
        body_md = tmp_path / "body.md"
        body_md.write_text(f"{JP_PARAGRAPH} {stamp_img()}")
        cmd = f'gh pr create --label "バグ" --label "機能追加" --body-file {body_md}'
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, cwd=tmp_path)
        assert result.returncode == 0, result.stderr

    def test_mcp_title_only_jp_passes(self, run_hook):
        # Title is intentionally NOT inspected (BODY_FIELDS = {"body"}).
        result = run_hook(
            {
                "tool_name": "mcp__github__github_create_pull_request",
                "tool_input": {"title": "日本語タイトル", "body": ""},
            }
        )
        assert result.returncode == 0
