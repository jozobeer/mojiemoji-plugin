"""Auditable Japanese Unicode regex ranges.

Use escaped bounds instead of visually ambiguous glyphs. In particular,
the lower bound for CJK Compatibility Ideographs is U+F900, not the
lookalike U+8C48 glyph that would accidentally span Hangul, Yi, and PUA.
"""

from __future__ import annotations


HAN_RANGE = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
HIRAGANA_RANGE = r"\u3040-\u309f"
KATAKANA_RANGE = r"\u30a0-\u30ff"


__all__ = [
    "HAN_RANGE",
    "HIRAGANA_RANGE",
    "KATAKANA_RANGE",
]
