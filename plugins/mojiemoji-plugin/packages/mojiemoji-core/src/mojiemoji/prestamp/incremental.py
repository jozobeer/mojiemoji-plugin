"""Protect sentences already processed at the same prestamp intensity."""

from __future__ import annotations

from mojiemoji.lib.sentence import split_sentences

from mojiemoji.prestamp.lines import (
    _observe_summary_tags,
    _scan_summary_aware,
    _walk_lines_outside_fences_with_reason,
)
from mojiemoji.prestamp.masker import _Masker, _mask_safe_zones
from mojiemoji.prestamp.render import PRESTAMP_IMG_RE


def _processed_segment_masked(segment: str, processed: _Masker) -> str:
    safe_zones = _Masker()
    masked = _mask_safe_zones(segment, safe_zones)
    prestamp_tokens = safe_zones.matching_tokens(PRESTAMP_IMG_RE)
    if not prestamp_tokens:
        return segment

    output: list[str] = []
    cursor = 0
    for start, end, _sentence in split_sentences(masked):
        output.append(safe_zones.restore(masked[cursor:start]))
        sentence = masked[start:end]
        restored = safe_zones.restore(sentence)
        output.append(
            processed.mask(restored)
            if any(token in sentence for token in prestamp_tokens)
            else restored
        )
        cursor = end
    output.append(safe_zones.restore(masked[cursor:]))
    return "".join(output)


def processed_sentences_masked(text: str, processed: _Masker) -> str:
    """Mask prose sentences containing prestamp-generated image tags."""
    state = {"in_summary": False}
    output: list[str] = []

    for line, is_prose, reason in _walk_lines_outside_fences_with_reason(text):
        if is_prose:
            output.append(
                _scan_summary_aware(
                    line,
                    state,
                    lambda segment: _processed_segment_masked(segment, processed),
                )
            )
            continue
        if reason == "disabled":
            _observe_summary_tags(line, state)
        output.append(line)

    return "".join(output)


__all__ = ["processed_sentences_masked"]
