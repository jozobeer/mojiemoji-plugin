"""Tests for `validators/canonical.py` — forbidden colors + 3-kanji split.

Two related rules that live in the canonical module but are split out
from `test_gate_canonical.py` to keep each file under the 200-line
file-size budget:

- Tailwind 600+ palette + near-black hexes (`FORBIDDEN_COLORS`)
- 3-kanji single stamp (must split `2+1` per SKILL.md spotcheck #16)

Exit code contract: 0 → allow, 2 → block.
"""

from __future__ import annotations

from conftest import stamp_img

JP_BODY = "これは日本語の本文です。"
JP_PARAGRAPH = (
    "これは日本語のPR本文で、ちゃんとした装飾済みのスタンプが含まれています。"
)


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
