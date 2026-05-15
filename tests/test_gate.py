"""Tests for hooks/mojiemoji-japanese-gate.py.

Exit code contract:
- 0 → allow (not our target, no Japanese, properly decorated, or bypassed)
- 2 → block (Japanese body missing or with malformed mojiemoji URLs)

Cases are grouped by entry path (Bash vs MCP) and by gate stage
(filtering → bypass → JP detection → URL presence → param presence →
outline value validity → canonical font/animation/color → animation
conflicts → rotational+speed).
"""

from __future__ import annotations

import json
import re
import subprocess

import pytest

from conftest import HOOK, stamp_img, stamp_url

JP_BODY = "これは日本語の本文です。"
JP_PARAGRAPH = (
    "これは日本語のPR本文で、ちゃんとした装飾済みのスタンプが含まれています。"
)


# --- Tool-name filtering ---------------------------------------------------


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
        # `{}` parses fine but lacks `tool_name` — the hook should
        # treat it as a no-op (fail-open on missing fields).
        result = run_hook({})
        assert result.returncode == 0

    def test_unparseable_stdin_is_allowed(self, tmp_path):
        # The hook should never crash a tool call on its own bug.
        # Raw garbage that isn't JSON returns 0 (fail-open).
        result = subprocess.run(
            ["python3", str(HOOK)],
            input=b"not json at all {{{",
            capture_output=True,
            cwd=str(tmp_path),
            timeout=10,
        )
        assert result.returncode == 0


# --- gh edit variants (issue / pr / release edit) -------------------------


class TestGhEditVariants:
    """`edit` subcommands accept body inputs (`--body`, `--notes`, etc.)
    and must trip the gate just like `create` / `comment` / `review`."""

    def test_gh_issue_edit_with_japanese_body_is_blocked(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh issue edit 123 --body "{JP_BODY}"'},
            }
        )
        assert result.returncode == 2

    def test_gh_pr_edit_with_japanese_body_is_blocked(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh pr edit 123 --body "{JP_BODY}"'},
            }
        )
        assert result.returncode == 2

    def test_gh_release_edit_with_japanese_notes_is_blocked(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh release edit v1.0.0 --notes "{JP_BODY}"'},
            }
        )
        assert result.returncode == 2


# --- Language filtering ----------------------------------------------------


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


# --- HOOK_DISABLE bypass ---------------------------------------------------


class TestBypass:
    """`HOOK_DISABLE=1` opts out, but only on the surface the caller controls."""

    def test_bash_bypass_prefix(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f'HOOK_DISABLE=1 gh pr create --title "x" --body "{JP_BODY}"'
                },
            }
        )
        assert result.returncode == 0

    def test_mcp_bypass_in_body(self, run_hook):
        result = run_hook(
            {
                "tool_name": "mcp__github__github_create_pull_request",
                "tool_input": {"body": f"HOOK_DISABLE=1 {JP_BODY}"},
            }
        )
        assert result.returncode == 0

    def test_bash_bypass_must_be_in_command_not_body_file(self, run_hook, tmp_path):
        # HOOK_DISABLE inside a referenced file should NOT count — otherwise
        # documentation prose or fixtures mentioning the literal would
        # silently disable the gate.
        body_file = tmp_path / "body.md"
        body_file.write_text(f"HOOK_DISABLE=1 {JP_BODY}")
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh pr create --title "x" --body-file {body_file}'},
            },
            cwd=tmp_path,
        )
        assert result.returncode == 2, "bypass marker leaked from body file"


# --- Bash happy path & blocking ------------------------------------------


class TestBashHappyPath:
    """Properly-decorated `gh` invocations exit 0."""

    def test_inline_body_with_full_stamp(self, run_hook):
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --title "x" --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_gh_api_reviews_with_full_stamp(self, run_hook):
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        # `gh api .../reviews` is the raw POST form used by batch review skills.
        cmd = f"gh api repos/o/r/pulls/1/reviews -f body=\"{body}\""
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}})
        assert result.returncode == 0, result.stderr


class TestBashBlocking:
    """Bad Bash invocations are blocked."""

    def test_jp_body_with_zero_stamps_blocks(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh pr create --title "x" --body "{JP_BODY}"'},
            }
        )
        assert result.returncode == 2
        assert "mojiemoji" in result.stderr.lower()

    def test_jp_body_with_url_missing_font_blocks(self, run_hook):
        # Drop `font=` — every other param present.
        bad_url = stamp_url().replace("font=gothic-bold&", "")
        body = f'{JP_BODY} <img src="{bad_url}" alt="x">'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_jp_body_with_url_missing_background_blocks(self, run_hook):
        bad_url = stamp_url(background=None)
        body = f'{JP_BODY} <img src="{bad_url}" alt="x">'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_non_canonical_font_blocks(self, run_hook):
        # `fude` is not in CANONICAL_FONTS — service silently fallbacks.
        body = f'{JP_BODY} {stamp_img(font="fude")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2
        assert "font" in result.stderr.lower()

    def test_non_canonical_animation_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(animation="poyon")}'  # typo of poyoon
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_named_color_blocks(self, run_hook):
        # `vivid-purple` is a named palette token, service silently
        # falls back to black on dark mode.
        body = f'{JP_BODY} {stamp_img(color="vivid-purple")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2


# --- Animation conflict cases ----------------------------------------------


class TestAnimationConflicts:
    """disco/psycho/kira fight a fixed outline; kaiten/kage_kaiten need slow."""

    def test_disco_with_outline_blocks(self, run_hook):
        # Color-shifting animation + outline is a styling conflict.
        # Per `required_for`, the URL doesn't need outline params to pass
        # the presence check, but if outline IS present, the
        # `animation+outline` invalid-pair check trips.
        body = f'{JP_BODY} {stamp_img(animation="disco")}'  # outline=darker still attached
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_disco_without_outline_passes(self, run_hook):
        body = (
            f"{JP_PARAGRAPH} "
            f'{stamp_img(animation="disco", outline=None, outline_width=None)}'
        )
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_kaiten_without_speed_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(animation="kaiten")}'  # no speed
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2
        assert "speed" in result.stderr.lower()

    def test_kaiten_with_speed_fast_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(animation="kaiten", speed="fast")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_kaiten_with_speed_slow_passes(self, run_hook):
        body = f'{JP_PARAGRAPH} {stamp_img(animation="kaiten", speed="slow")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_kage_kaiten_with_speed_step_passes(self, run_hook):
        body = f'{JP_PARAGRAPH} {stamp_img(animation="kage_kaiten", speed="step")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_non_rotational_without_speed_passes(self, run_hook):
        # `tate_scroll` is translational, not rotational — no speed needed.
        body = f'{JP_PARAGRAPH} {stamp_img(animation="tate_scroll")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr


# --- Outline value validity ------------------------------------------------


class TestOutlineValidity:
    def test_uppercase_hex_outline_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(outline="DEADBE")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_garbage_outline_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(outline="rainbow")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_lighter_outline_passes(self, run_hook):
        body = f'{JP_PARAGRAPH} {stamp_img(outline="lighter")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr


# --- Body-file / script-file inspection ------------------------------------


class TestFileInspection:
    """File-routed bodies are inspected just like inline ones."""

    def test_body_file_with_bad_url_blocks(self, run_hook, tmp_path):
        bad_url = stamp_url().replace("font=gothic-bold&", "")
        (tmp_path / "body.md").write_text(f'{JP_BODY} <img src="{bad_url}">')
        cmd = "gh pr create --title x --body-file body.md"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            cwd=tmp_path,
        )
        assert result.returncode == 2

    def test_gh_api_input_with_bad_url_blocks(self, run_hook, tmp_path):
        bad_url = stamp_url().replace("font=gothic-bold&", "")
        payload = {"body": f'{JP_BODY} <img src="{bad_url}">'}
        # Mirror what real triage-review-style scripts write: raw UTF-8
        # Japanese, not `\uXXXX` escapes. `ensure_ascii=False` is the
        # idiomatic choice when the body is meant to be human-readable
        # inside the JSON file.
        (tmp_path / "payload.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        cmd = "gh api repos/o/r/issues -X POST --input payload.json"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            cwd=tmp_path,
        )
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
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            cwd=tmp_path,
        )
        assert result.returncode == 2


# --- LGTM block-image rejection --------------------------------------------


class TestLgtmStamp:
    """`![LGTM](mojiemoji.jozo.beer/emoji/LGTM…)` markdown block-image
    syntax is rejected per SKILL.md § LGTM 画像 (block-style LGTM
    mojiemoji is the wrong tool — confirmed across multiple PRs).

    Inline `<img ... height="24" align="absmiddle">` usage of LGTM is
    allowed — the plugin only scopes the block-rendering pattern.
    """

    def _md_block_image_url(self, url: str) -> str:
        # Markdown image syntax: `![alt](url)`.
        return f"![LGTM]({url})"

    def test_block_lgtm_markdown_image_blocks(self, run_hook):
        url = stamp_url(text="LGTM")
        body = f"{JP_PARAGRAPH}\n\n{self._md_block_image_url(url)}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2
        assert "LGTM" in result.stderr
        assert "block" in result.stderr.lower()

    def test_inline_lgtm_html_img_passes(self, run_hook):
        # Inline HTML <img> form is the allowed usage. LGTM as a word
        # embedded mid-prose is fine, like any other inline stamp.
        body = f"{JP_PARAGRAPH} {stamp_img(text='LGTM')}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_block_lgtm_lowercase_blocks(self, run_hook):
        # Path is case-insensitive on the service side; the hook normalizes.
        url = stamp_url(text="LGTM").replace("LGTM", "lgtm")
        body = f"{JP_PARAGRAPH}\n\n![lgtm]({url})"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_block_lgtm_in_mcp_body_blocks(self, run_hook):
        url = stamp_url(text="LGTM")
        body = f"{JP_PARAGRAPH}\n\n{self._md_block_image_url(url)}"
        result = run_hook(
            {
                "tool_name": "mcp__github__github_pull_request_review_write",
                "tool_input": {"body": body, "event": "APPROVE"},
            }
        )
        assert result.returncode == 2

    def test_inline_lgtm_in_mcp_body_passes(self, run_hook):
        body = f"{JP_PARAGRAPH} {stamp_img(text='LGTM')}"
        result = run_hook(
            {
                "tool_name": "mcp__github__github_pull_request_review_write",
                "tool_input": {"body": body, "event": "APPROVE"},
            }
        )
        assert result.returncode == 0, result.stderr

    def test_block_lgtms_word_passes(self, run_hook):
        # `LGTMS` etc — the slug between /emoji/ and the next delimiter
        # is matched as a whole word. `LGTMS` is a different emoji text
        # and shouldn't be rejected by substring.
        url = stamp_url(text="LGTMS")
        body = f"{JP_PARAGRAPH}\n\n![lgtms]({url})"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_block_lgtm_with_hook_disable_bypasses(self, run_hook):
        url = stamp_url(text="LGTM")
        body = f"{JP_PARAGRAPH}\n\n{self._md_block_image_url(url)}"
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'HOOK_DISABLE=1 gh pr create --body "{body}"'},
            }
        )
        assert result.returncode == 0


# --- MCP path --------------------------------------------------------------


class TestMcpPath:
    """MCP GitHub tools are gated identically (body-field only)."""

    # Names that Claude Code's matcher (`hooks/hooks.json`) actually routes
    # to the hook today: the pattern is `Bash|mcp__.*github.*`, so the tool
    # name must contain `github` somewhere. Production coverage is bounded
    # by this matcher — names not matching it never reach the hook.
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

    # Defense-in-depth: even if a future matcher broadens to non-`github`
    # aliases (`mcp__octo__*`, `mcp__forgejo__*`, …), the hook logic itself
    # must still recognize the GH operation suffix. Documenting this
    # separately from the matcher-bound tests above prevents false
    # confidence about what production currently covers.
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

    def test_review_with_comments_aggregates(self, run_hook):
        # `pull_request_review_write` carries a top-level body plus
        # inline `comments[].body`. The gate aggregates them so a
        # stamped summary covers un-stamped findings (matching the
        # SKILL.md "summary decorated, findings un-stamped" policy).
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
        assert result.returncode == 0, result.stderr

    def test_mcp_title_only_jp_passes(self, run_hook):
        # Title is intentionally NOT inspected (BODY_FIELDS = {"body"}).
        # A Japanese title without a body should not trip the gate.
        result = run_hook(
            {
                "tool_name": "mcp__github__github_create_pull_request",
                "tool_input": {"title": "日本語タイトル", "body": ""},
            }
        )
        assert result.returncode == 0


# --- Matcher coverage (hooks/hooks.json) ----------------------------------


class TestMatcherCoverage:
    """The hook only runs for tool names that match the matcher in
    `hooks/hooks.json`. This documents the actual production routing
    boundary — names not matching here never reach the hook regardless
    of how robust the hook logic is."""

    @pytest.fixture(scope="class")
    def matcher(self):
        config = json.loads((HOOK.parent / "hooks.json").read_text())
        pattern = config["hooks"]["PreToolUse"][0]["matcher"]
        return re.compile(pattern)

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
