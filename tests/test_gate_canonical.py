"""Tests for `validators/canonical.py` — non-canonical values + animation conflicts.

Single-param canonical allowlist (font / animation / color) and the
composite-rule pairs that share the same module:
- color-shifting animation paired with `outline=` (rainbow vs halo)
- rotational animation without `speed=step|slow`

Forbidden-color and 3-kanji-single-stamp rules live in
`test_gate_kanji_color.py` (same module, separated for AC file-size
budget).

Exit code contract: 0 → allow, 2 → block.
"""

from __future__ import annotations

from conftest import assert_skill_agent_guidance, stamp_img

JP_BODY = "これは日本語の本文です。"
JP_PARAGRAPH = (
    "これは日本語のPR本文で、ちゃんとした装飾済みのスタンプが含まれています。"
)


class TestNonCanonicalValues:
    """Service silently falls back to defaults on unknown fonts /
    animations / named colors — hook must value-allowlist them."""

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
        assert_skill_agent_guidance(result.stderr)


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
