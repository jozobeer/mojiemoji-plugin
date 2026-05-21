"""Tests for `validators/catalog_leftovers.py`.

Issue #70: catalog hits should be mechanically replaced *before* AI
starts decorating. Bodies with 10+ catalog terms remaining as plain
text signal that prestamp.py was not run, which means the AI is
burning tokens hand-crafting <img> for words the catalog would
replace for free.

Exit code contract:
- 0 → allow
- 2 → block
"""

from __future__ import annotations

from conftest import stamp_img

JP_PARAGRAPH = (
    "これは日本語のPR本文で、ちゃんとした装飾済みのスタンプが含まれています。"
)


class TestCatalogLeftovers:
    """`validate_catalog_leftovers` — block bodies that skipped prestamp.py."""

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

    def test_ascii_terms_inside_larger_words_do_not_count(self, run_hook):
        # Regression for #98: naive substring matching counted `OS`
        # inside POST and `CI` inside ASCII, tripping the leftover
        # threshold even though no standalone catalog term was present.
        body = f"{JP_PARAGRAPH} {' '.join(['POST', 'ASCII'] * 12)} {stamp_img()}"
        result = run_hook(
            {"tool_name": "Bash", "tool_input": {"command": f'gh pr create --body "{body}"'}}
        )
        assert result.returncode == 0, result.stderr
