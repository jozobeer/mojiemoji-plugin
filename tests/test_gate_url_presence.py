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

from conftest import stamp_img, stamp_url

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
                "tool_input": {"command": f'gh pr create --title "x" --body "{JP_BODY}"'},
            }
        )
        assert result.returncode == 2
        assert "mojiemoji" in result.stderr.lower()


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
