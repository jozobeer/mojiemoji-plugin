"""Tests for hooks/mojiemoji_japanese_gate.py.

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
import sys

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
            [sys.executable, str(HOOK)],
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


# --- MOJIEMOJI_HOOK_DISABLED bypass ----------------------------------------


class TestBypass:
    """`MOJIEMOJI_HOOK_DISABLED=1` opts out, but only on the surface the caller controls."""

    def test_bash_bypass_prefix(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f'MOJIEMOJI_HOOK_DISABLED=1 gh pr create --title "x" --body "{JP_BODY}"'
                },
            }
        )
        assert result.returncode == 0

    def test_mcp_bypass_in_body(self, run_hook):
        result = run_hook(
            {
                "tool_name": "mcp__github__github_create_pull_request",
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
                "tool_input": {"command": f'gh pr create --title "x" --body-file {body_file}'},
            },
            cwd=tmp_path,
        )
        assert result.returncode == 2, "bypass marker leaked from body file"

    def test_legacy_hook_disable_no_longer_bypasses(self, run_hook):
        # The legacy `HOOK_DISABLE=1` name was deprecated in v0.x and
        # removed in v0.21.0. It must now be treated as plain text and
        # therefore NOT bypass the gate.
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f'HOOK_DISABLE=1 gh pr create --title "x" --body "{JP_BODY}"'
                },
            }
        )
        assert result.returncode == 2, "legacy HOOK_DISABLE=1 must no longer bypass"


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


# --- Forbidden colors (Tailwind 600+ / near-black) -------------------------


class TestForbiddenColor:
    """Tailwind 600+ palette + near-black hexes go invisible on dark mode.

    Selector contract + verification.md spotcheck #4 enumerate the
    forbidden list; this enforces it at the hook layer so hand-crafted
    URLs that bypass selector still get rejected (issue #41 — 3-layer
    alignment).
    """

    def test_red_600_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(color="dc2626")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2
        assert "tailwind" in result.stderr.lower() or "600" in result.stderr

    def test_blue_700_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(color="1d4ed8")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_pure_black_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(color="000000")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_gray_900_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(color="111827")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_tailwind_500_passes(self, run_hook):
        # Tailwind 500 range (blue-500 = 3b82f6, green-500 = 22c55e) is
        # dark-mode-safe and explicitly allowed.
        body = f'{JP_PARAGRAPH} {stamp_img(color="3b82f6")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_tailwind_400_passes(self, run_hook):
        # 400 range is the user's most common choice (60a5fa, 4ade80, etc.)
        body = f'{JP_PARAGRAPH} {stamp_img(color="60a5fa")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr


# --- 3-kanji single stamp split rule ---------------------------------------


class TestThreeKanjiSingle:
    """3+ contiguous kanji in a single stamp get crushed at inline h=24.

    Selector contract + verification.md spotcheck #16 require `2+1`
    split; this is the hook-layer enforcement (issue #41).
    """

    def test_three_kanji_single_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(text="致命傷")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2
        assert "2+1" in result.stderr or "kanji" in result.stderr.lower()

    def test_four_kanji_single_blocks(self, run_hook):
        body = f'{JP_BODY} {stamp_img(text="緊急対応")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2

    def test_two_kanji_passes(self, run_hook):
        body = f'{JP_PARAGRAPH} {stamp_img(text="修正")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_single_kanji_passes(self, run_hook):
        # 1-kanji is unusual but not visually crushed; allow it.
        body = f'{JP_PARAGRAPH} {stamp_img(text="可")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_kanji_hiragana_mix_passes(self, run_hook):
        # `お願い` is hiragana+kanji+hiragana mix — not a 3-kanji string
        # (the all-kanji check only fires on pure kanji sequences).
        body = f'{JP_PARAGRAPH} {stamp_img(text="お願い")}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_long_hiragana_with_newline_passes(self, run_hook):
        # 4-char all-hiragana words use `%0A` for the 2-line layout
        # (`よろ\nしく`). Not subject to the kanji split rule.
        body = f'{JP_PARAGRAPH} {stamp_img(text="よろ\nしく")}'
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


# --- LGTM stamp (no special-case handling) ---------------------------------


class TestLgtmStamp:
    """LGTM mojiemoji is not treated specially by the hook. Both inline
    `<img>` form and `![alt](url)` markdown block-image form are allowed
    when they meet the same styling requirements as any other stamp.

    Editorial guidance about WHEN to prefer inline vs block (e.g., when
    using another LGTM-imagery skill alongside) lives in SKILL.md
    § LGTM 画像 — the hook itself doesn't have runtime context to
    enforce that conditional, so it doesn't try.
    """

    def test_inline_lgtm_passes(self, run_hook):
        body = f"{JP_PARAGRAPH} {stamp_img(text='LGTM')}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_block_lgtm_markdown_image_passes(self, run_hook):
        url = stamp_url(text="LGTM")
        body = f"{JP_PARAGRAPH}\n\n![LGTM]({url})"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_block_lgtm_in_mcp_body_passes(self, run_hook):
        url = stamp_url(text="LGTM")
        body = f"{JP_PARAGRAPH}\n\n![LGTM]({url})"
        result = run_hook(
            {
                "tool_name": "mcp__github__github_pull_request_review_write",
                "tool_input": {"body": body, "event": "APPROVE"},
            }
        )
        assert result.returncode == 0, result.stderr


# --- MCP path --------------------------------------------------------------


class TestMcpPath:
    """MCP GitHub tools are gated identically for each body field."""

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

    def test_review_comment_without_own_stamp_blocks(self, run_hook):
        # `pull_request_review_write` carries a top-level body plus
        # inline `comments[].body`. Each body field is its own GitHub
        # prose surface, so a stamped summary must not cover un-stamped
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
                    "comments": [
                        {"path": "x.py", "line": 1, "body": "ここは型エラーです"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f"gh api repos/o/r/pulls/1/reviews --input {payload}"
                },
            },
            cwd=tmp_path,
        )
        assert result.returncode == 2

    def test_gh_api_input_review_with_decorated_comments_passes(self, run_hook, tmp_path):
        # Regression for #112 review feedback: `read_body_files` previously
        # joined extracted JSON body pieces into a single string and
        # `_route_bash` extended a list with it, splitting Japanese into
        # per-character surfaces. Each char then had 0 mojiemoji URLs and
        # the gate falsely blocked properly-decorated review payloads.
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
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f"gh api repos/o/r/pulls/1/reviews --input {payload}"
                },
            },
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr

    def test_japanese_title_with_decorated_body_file_passes(self, run_hook, tmp_path):
        # Regression for #112 review feedback: Japanese in non-body flag
        # values (e.g., `--title "日本語…"`) should not trip the gate.
        # Only body-class surfaces are inspected per BODY_FIELDS policy;
        # title / label / reviewer / etc. are explicitly out of scope.
        body_md = tmp_path / "body.md"
        body_md.write_text(f"{JP_PARAGRAPH} {stamp_img()}")
        cmd = f'gh pr create --title "日本語タイトル" --body-file {body_md}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            cwd=tmp_path,
        )
        assert result.returncode == 0, result.stderr

    def test_japanese_label_with_decorated_body_passes(self, run_hook, tmp_path):
        # `--label "バグ"` is metadata, not posting prose. Should not
        # require mojiemoji decoration even when no body file is used.
        body_md = tmp_path / "body.md"
        body_md.write_text(f"{JP_PARAGRAPH} {stamp_img()}")
        cmd = f'gh pr create --label "バグ" --label "機能追加" --body-file {body_md}'
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            cwd=tmp_path,
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


class TestCatalogLeftovers:
    """`validate_catalog_leftovers` — block bodies that skipped prestamp.py.

    Issue #70: catalog hits should be mechanically replaced *before*
    AI starts decorating. Bodies with 10+ catalog terms remaining as
    plain text signal that prestamp.py was not run, which means the
    AI is burning tokens hand-crafting <img> for words the catalog
    would replace for free.
    """

    PLAIN_TERMS = "対応 修正 確認 完了 実装 検証 追加 削除 重複 既存 対象 統一 移行 検出"

    def test_many_plain_catalog_terms_block(self, run_hook):
        # Body has a valid stamp (so URL/canonical stages pass) plus many
        # plain catalog terms. Leftover stage should block.
        plain = self.PLAIN_TERMS
        body = f"{JP_PARAGRAPH} {plain}。 {stamp_img()}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 2
        assert "prestamp" in result.stderr.lower()

    def test_few_plain_catalog_terms_pass(self, run_hook):
        # Only 2 catalog terms plain — under threshold, should pass.
        body = f"{JP_PARAGRAPH} 対応 修正 を行いました。 {stamp_img()}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_catalog_terms_in_img_alt_pass(self, run_hook):
        # When all 14 terms are inside <img> tags (already stamps),
        # stripping should remove them and leftover count is 0.
        template = (
            '<img src="https://mojiemoji.jozo.beer/emoji/{term}'
            "?font=gothic-bold&color=22c55e&animation=bane"
            '&background=transparent&outline=darker&outline_width=2" '
            'alt="{term}" height="24">'
        )
        img_terms = " ".join(template.format(term=t) for t in self.PLAIN_TERMS.split())
        body = f"{JP_PARAGRAPH} {img_terms}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_catalog_terms_in_fenced_code_pass(self, run_hook):
        # Terms inside fenced code blocks are stripped (legitimate
        # mention of catalog words in code samples / examples).
        body = f"{JP_PARAGRAPH}\n\n```\n{self.PLAIN_TERMS}\n```\n {stamp_img()}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr

    def test_catalog_terms_in_inline_code_pass(self, run_hook):
        # Each term wrapped in inline code — stripped before count.
        coded = " ".join(f"`{t}`" for t in self.PLAIN_TERMS.split())
        body = f"{JP_PARAGRAPH} {coded} {stamp_img()}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr


# --- schema-version drift (issue #80) -------------------------------------

class TestSchemaVersionDrift:
    """Verify validate_schema_version's behaviour across the 4 cases:
    marker present + match / mismatch / missing on harness file, and
    strict mode block.
    """

    @staticmethod
    def _import_hook():
        import importlib.util
        from conftest import HOOK
        spec = importlib.util.spec_from_file_location("gate_hook", HOOK)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _write_skill(path, version):
        path.parent.mkdir(parents=True, exist_ok=True)
        if version is None:
            path.write_text("# SKILL.md (no marker)\n")
        else:
            path.write_text(f"# SKILL.md\n\n<!-- mojiemoji-schema-version: {version} -->\n")

    def test_match_emits_nothing(self, tmp_path, monkeypatch, capsys):
        mod = self._import_hook()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        # Re-cache by clearing the sentinel.
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        # Point all harness paths at one matching file.
        harness_path = tmp_path / "claude" / "SKILL.md"
        self._write_skill(harness_path, "2.0.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("claude", harness_path),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert captured.err == ""

    def test_mismatch_warns_but_does_not_block(self, tmp_path, monkeypatch, capsys):
        mod = self._import_hook()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        stale = tmp_path / "codex" / "SKILL.md"
        self._write_skill(stale, "1.5.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("codex", stale),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0  # warn-only by default
        assert "expected: 2.0.0" in captured.err
        assert "found:    1.5.0" in captured.err
        assert "codex" in captured.err

    def test_missing_marker_on_harness_warns(self, tmp_path, monkeypatch, capsys):
        mod = self._import_hook()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        no_marker = tmp_path / "gemini" / "SKILL.md"
        self._write_skill(no_marker, None)
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("gemini", no_marker),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert "(marker missing)" in captured.err
        assert "gemini" in captured.err

    def test_strict_mode_mismatch_blocks(self, tmp_path, monkeypatch, capsys):
        mod = self._import_hook()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        stale = tmp_path / "opencode" / "SKILL.md"
        self._write_skill(stale, "1.0.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("opencode", stale),)
        )
        monkeypatch.setenv("MOJIEMOJI_STRICT_VERSION", "1")

        rc = mod.validate_schema_version("ダミー")

        assert rc == 2

    def test_host_marker_missing_is_noop(self, tmp_path, monkeypatch, capsys):
        # When the host SKILL.md has no marker (drift-check disabled),
        # the stage must not emit anything regardless of harness state.
        mod = self._import_hook()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "no-marker-host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "no-marker-host.md", None)
        stale = tmp_path / "codex" / "SKILL.md"
        self._write_skill(stale, "1.0.0")
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("codex", stale),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert captured.err == ""

    def test_absent_harness_files_are_skipped(self, tmp_path, monkeypatch, capsys):
        # Harness path doesn't exist — should silently skip, not warn.
        mod = self._import_hook()
        monkeypatch.setattr(mod, "HOST_SKILL_PATH", tmp_path / "host.md")
        monkeypatch.setattr(mod, "_canonical_version_cache", object())
        self._write_skill(tmp_path / "host.md", "2.0.0")
        nonexistent = tmp_path / "windsurf" / "never-existed.md"
        monkeypatch.setattr(
            mod, "_harness_skill_paths", lambda: (("windsurf", nonexistent),)
        )

        rc = mod.validate_schema_version("ダミー")

        captured = capsys.readouterr()
        assert rc == 0
        assert captured.err == ""
