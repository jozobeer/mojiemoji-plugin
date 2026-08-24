"""Tests for the URL-presence validator (`validators/url_presence.py`).

Stage 1 in `PIPELINE` — fires when a Japanese body contains zero
mojiemoji `<img>` URLs. Also covers:

- Bash happy paths that prove a decorated body reaches the validators
  and clears.
- LGTM stamp shapes — inline `<img>` AND markdown-block `![alt](url)` —
  must be recognized by the URL extractor with no special-casing.

Exit code contract: 0 → allow, 2 → block.
"""

from __future__ import annotations

from conftest import assert_skill_agent_guidance, stamp_img, stamp_url

JP_BODY = "これは日本語の本文です。"
JP_PARAGRAPH = (
    "これは日本語のPR本文で、ちゃんとした装飾済みのスタンプが含まれています。"
)


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


class TestZeroStamps:
    """Japanese body with no mojiemoji URLs is blocked."""

    def test_jp_body_with_zero_stamps_blocks(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh issue create --title "x" --body "{JP_BODY}"'},
            }
        )
        assert result.returncode == 2
        assert "mojiemoji" in result.stderr.lower()
        assert_skill_agent_guidance(result.stderr)

    def test_pr_body_without_stamps_is_allowed_when_policy_unknown(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh pr create --title "x" --body "{JP_BODY}"'},
            }
        )
        assert result.returncode == 0, result.stderr

    def test_force_pr_body_keeps_zero_stamp_gate_enabled(self, run_hook):
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f'MOJIEMOJI_FORCE_PR_BODY=1 gh pr create --title "x" --body "{JP_BODY}"',
                },
            }
        )
        assert result.returncode == 2
        assert "mojiemoji" in result.stderr.lower()


class TestEnglishOptIn:
    """English/Latin gating is opt-in and validates posted body surfaces."""

    def test_body_file_command_is_not_validated_as_english_body(self, run_hook, tmp_path):
        (tmp_path / "body.md").write_text(
            f"Release is ready. {stamp_img(text='DONE', alt='DONE')}",
            encoding="utf-8",
        )
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "MOJIEMOJI_ENGLISH_GATE=1 "
                        "gh issue create --title x --body-file body.md"
                    ),
                },
            },
            cwd=tmp_path,
        )

        assert result.returncode == 0, result.stderr

    def test_mixed_payload_validates_japanese_and_english_bodies(self, run_hook):
        jp_summary = f"MOJIEMOJI_ENGLISH_GATE=1 日本語 summary {stamp_img()}"
        result = run_hook(
            {
                "tool_name": "mcp__github__github_pull_request_review_write",
                "tool_input": {
                    "body": jp_summary,
                    "comments": [
                        {"body": "This English inline review needs a stamp."},
                    ],
                },
            }
        )

        assert result.returncode == 2
        assert "mojiemoji" in result.stderr.lower()


class TestSelfHostedInstance:
    """`MOJIEMOJI_BASE_URL` repoints the renderers; the gate must follow.

    The URL recognizer is derived from the same configuration the
    renderers stamp against. Were it pinned to the hosted host, a body
    decorated for a self-hosted instance would reach the gate with zero
    recognized stamps and be blocked by the very configuration the
    plugin advertises.
    """

    SELF_HOSTED = "https://moji.example.internal"

    def test_self_hosted_stamp_is_recognized(self, run_hook, monkeypatch):
        monkeypatch.setenv("MOJIEMOJI_BASE_URL", self.SELF_HOSTED)
        body = f"{JP_PARAGRAPH} {stamp_img(base_url=self.SELF_HOSTED)}"
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh issue create --title "x" --body "{body}"'},
            }
        )
        assert result.returncode == 0, result.stderr

    def test_hosted_default_stays_recognized(self, run_hook, monkeypatch):
        """A body carried over from another machine must not become unreadable."""
        monkeypatch.setenv("MOJIEMOJI_BASE_URL", self.SELF_HOSTED)
        body = f"{JP_PARAGRAPH} {stamp_img()}"
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh issue create --title "x" --body "{body}"'},
            }
        )
        assert result.returncode == 0, result.stderr

    def test_zero_stamp_message_names_the_configured_instance(self, run_hook, monkeypatch):
        monkeypatch.setenv("MOJIEMOJI_BASE_URL", self.SELF_HOSTED)
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f'gh issue create --title "x" --body "{JP_BODY}"'},
            }
        )
        assert result.returncode == 2
        assert "moji.example.internal" in result.stderr


class TestLgtmStamp:
    """LGTM mojiemoji is not treated specially by the hook. Both inline
    `<img>` and `![alt](url)` markdown block-image forms are allowed
    when they meet the same styling requirements as any other stamp.
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
