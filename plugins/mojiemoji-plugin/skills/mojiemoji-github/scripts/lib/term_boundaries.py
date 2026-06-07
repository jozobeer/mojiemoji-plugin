"""Shared ASCII word-boundary helpers for catalog-term matching.

Single provenance for the regex fragments and helpers that decide
whether a catalog key is an "ASCII identifier-like" term (``URL``,
``PR``, ``OS``, ``CI`` …) and how to count its occurrences in a body
of text without false-matching inside larger identifiers (``POST``
contains ``OS``, ``ASCII`` contains ``CI``).

Both `skills/mojiemoji-github/scripts/prestamp.py` and
`hooks/mojiemoji_japanese_gate.py` consume these primitives so the two
agree on what counts as a standalone catalog hit. Drift between them
manifests as "the hook blocked a body, but prestamp could not auto-
replace it" or vice-versa — the body author then has no path forward.
See issue #98 for the original incident.

Non-ASCII keys (Kanji / Katakana compounds) intentionally use plain
substring matching: they cannot appear inside ASCII identifiers and
adding word boundaries via `\\b` would over-block legitimate Japanese
contexts where the catalog term sits flush against surrounding kana.
"""

from __future__ import annotations

import re


ASCII_KEY_RE = re.compile(r"\A[A-Za-z0-9_]+\Z")

ASCII_LEFT_GUARD = r"(?<![A-Za-z0-9_])"
ASCII_RIGHT_GUARD = r"(?![A-Za-z0-9_])"


def is_ascii_key(term: str) -> bool:
    """Return True when ``term`` is composed entirely of ASCII identifier
    characters and therefore needs word-boundary guards to avoid
    matching inside larger identifiers."""
    return bool(ASCII_KEY_RE.match(term))


def bounded_re(term: str) -> re.Pattern[str]:
    """Compile a regex that matches ``term`` only as a standalone token.

    ASCII keys get ``(?<![A-Za-z0-9_])TERM(?![A-Za-z0-9_])`` so they
    won't match inside larger identifiers. Non-ASCII keys get plain
    substring matching (`re.escape(term)`) — they can't collide with
    ASCII identifiers and Japanese flow doesn't have an equivalent
    "identifier character" notion.
    """
    if is_ascii_key(term):
        return re.compile(f"{ASCII_LEFT_GUARD}{re.escape(term)}{ASCII_RIGHT_GUARD}")
    return re.compile(re.escape(term))


def count_occurrences(text: str, term: str) -> int:
    """Count standalone occurrences of ``term`` in ``text``.

    Equivalent to ``text.count(term)`` for non-ASCII keys, but applies
    ASCII word boundaries for keys like ``URL`` / ``PR`` / ``OS`` so
    ``POST`` does not false-match ``OS``. Counting (not matching) is
    what the hook's leftover detector needs — a body with 10 plain-
    text ``対応`` should still trigger the block even if the same body
    contains the word ``POST`` (which used to count as an ``OS`` hit
    under naive substring matching).
    """
    if is_ascii_key(term):
        return len(bounded_re(term).findall(text))
    return text.count(term)
