"""Unicode-range and ASCII-boundary constants for the term regex.

Single-char catalog entries need boundary assertions or they over-match.
Single kanji (e.g. ``月`` / ``火`` / ``後``): block when preceded by another
Han char, which would indicate the entry is the tail of a compound
(``先月``). The guard also blocks adjacency to an underscore — that's the
trailing character of the ``__MOJIEMOJI_MASK_<n>__`` sentinel that the
masker leaves in place of ``<img>`` stamps emitted by a previous pass.
Without ``_`` in the negative class, a second prestamp run would see
``編集`` already masked and stamp the dangling ``後`` — breaking the
idempotency that the catalog drift check and
``test_prestamp_is_idempotent_for_emoji_pass`` both rely on.

Single ASCII digit (``1-9``): only stamp when embedded in Japanese
flow — preceded by kana/kanji AND followed by a non-ASCII-identifier char.

The ASCII multi-char tier's boundary helpers live in
``lib/term_boundaries.py`` so the hook's catalog-leftover detector can
share them; they are re-exported here for the same import path.
"""

from __future__ import annotations

import re

from lib.term_boundaries import (
    ASCII_KEY_RE,
    ASCII_LEFT_GUARD,
    ASCII_RIGHT_GUARD,
)

HAN_RANGE = "㐀-䶿一-鿿豈-﫿"
HIRAGANA_RANGE = "぀-ゟ"
KATAKANA_RANGE = "゠-ヿ"
SINGLE_HAN_LEFT_GUARD = f"(?<![{HAN_RANGE}_])"
SINGLE_DIGIT_LEFT_GUARD = f"(?<=[{HAN_RANGE}{HIRAGANA_RANGE}{KATAKANA_RANGE}])"
SINGLE_DIGIT_RIGHT_GUARD = r"(?![A-Za-z0-9_.])"

HAN_CHAR_RE = re.compile(f"[{HAN_RANGE}]")
DIGIT_CHAR_RE = re.compile(r"\A[0-9]\Z")

# Catalog growth signal — see #92 / #93. After prestamp finishes, any
# 2-8 char contiguous run of Kanji or Katakana that survived in prose is
# a candidate for catalog promotion (the term was either novel, too long
# for the sliding window, or simply uncatalogued). Hiragana is excluded
# because solo hiragana runs are dominated by 助詞/助動詞 noise; mixed
# runs naturally break at hiragana boundaries.
JAPANESE_RUN_RE = re.compile(f"[{HAN_RANGE}{KATAKANA_RANGE}]{{2,8}}")

__all__ = [
    "ASCII_KEY_RE",
    "ASCII_LEFT_GUARD",
    "ASCII_RIGHT_GUARD",
    "DIGIT_CHAR_RE",
    "HAN_CHAR_RE",
    "HAN_RANGE",
    "HIRAGANA_RANGE",
    "JAPANESE_RUN_RE",
    "KATAKANA_RANGE",
    "SINGLE_DIGIT_LEFT_GUARD",
    "SINGLE_DIGIT_RIGHT_GUARD",
    "SINGLE_HAN_LEFT_GUARD",
]
