"""Shared sentence-split helpers for prestamp and coverage.

Both modules need to agree on sentence boundaries — prestamp uses
them to pick first/last-position matches per sentence, and coverage
uses them to compute sentence-hit-rate. Keeping the regex in one
place prevents drift.
"""

from __future__ import annotations

import re

SENTENCE_SEP_RE = re.compile(r"[。．！？!?\n]+")


def split_sentences(text: str) -> list[tuple[int, int, str]]:
    """Return list of (start, end, sentence_text) for prose sentences.

    Treats lines/paragraphs without sentence punctuation as a single
    pseudo-sentence. Empty sentences are filtered out.
    """
    if not text:
        return []
    if not SENTENCE_SEP_RE.search(text):
        if text.strip():
            return [(0, len(text), text)]
        return []
    out: list[tuple[int, int, str]] = []
    pos = 0
    for m in SENTENCE_SEP_RE.finditer(text):
        seg_end = m.start()
        if seg_end > pos:
            raw = text[pos:seg_end]
            if raw.strip():
                out.append((pos, seg_end, raw))
        pos = m.end()
    if pos < len(text):
        raw = text[pos:]
        if raw.strip():
            out.append((pos, len(text), raw))
    return out
