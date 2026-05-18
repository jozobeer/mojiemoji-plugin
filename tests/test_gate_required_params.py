"""Tests for the required-params validator (`validators/required_params.py`).

Stage 2 in `PIPELINE` — each mojiemoji URL must carry the full
styling param set (font / color / animation / background / outline /
outline_width). Color-shifting animations are exempt from the outline
pair; that exemption is covered in `test_gate_canonical.py` (the
animation+outline conflict rule lives in `canonical.py`).

Exit code contract:
- 0 → allow
- 2 → block
"""

from __future__ import annotations

from conftest import stamp_img, stamp_url

JP_BODY = "これは日本語の本文です。"


class TestMissingParams:
    """Per-URL required-param presence."""

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
