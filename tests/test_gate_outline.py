"""Tests for the outline-value validator (`validators/outline.py`).

Stage 3 in `PIPELINE` — `outline=` must be one of the canonical
shorthands (`darker` / `lighter` / `triadic` / `complement`) or a
lowercase 6-digit hex. Uppercase hex and named palette tokens fall
back to default on the service silently, so the hook blocks them.

Exit code contract:
- 0 → allow
- 2 → block
"""

from __future__ import annotations

from conftest import stamp_img

JP_BODY = "これは日本語の本文です。"
JP_PARAGRAPH = (
    "これは日本語のPR本文で、ちゃんとした装飾済みのスタンプが含まれています。"
)


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
