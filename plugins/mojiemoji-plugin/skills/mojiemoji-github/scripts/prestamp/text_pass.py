"""Text-catalog substitution pass — replace catalog term hits with `<img>`.

For each prose segment between fences and ``<summary>`` regions, the
pass masks safe zones (code, links, URLs, existing `<img>` tags),
substitutes catalog matches with rendered stamps using a deterministic
CRC32 + seed variant selection, and restores the masked spans.
"""

from __future__ import annotations

import re
import zlib
from typing import Optional

from lib.sentence import split_sentences

from prestamp.lines import _scan_summary_aware
from prestamp.masker import _Masker, _mask_safe_zones
from prestamp.render import _render_variant


def _filtered_replace(
    text: str,
    *,
    term_re: re.Pattern[str],
    terms: dict,
    defaults: dict,
    base_url: str,
    seed: str,
    state: dict,
    intensity: str,
) -> str:
    """Replace only catalog matches selected by intensity rules (masked text)."""
    matches = list(term_re.finditer(text))
    if not matches:
        return text

    selected: set[int] = set()
    for sent_start, sent_end, _ in split_sentences(text):
        indices = [i for i, m in enumerate(matches) if sent_start <= m.start() < sent_end]
        if not indices:
            continue
        selected.add(indices[0])
        if intensity == "normal":
            selected.add(indices[-1])

    pieces: list[tuple[int, int, str]] = []
    for m_idx, m in enumerate(matches):
        if m_idx not in selected:
            continue
        term = m.group(0)
        variants = terms[term]
        crc_input = f"{seed}:{term}:{state['occurrence']}"
        state["occurrence"] += 1  # occurrence advances only for substituted matches
        variant = variants[zlib.crc32(crc_input.encode("utf-8")) % len(variants)]
        pieces.append((m.start(), m.end(), _render_variant(base_url, term, variant, defaults)))

    out = text
    for start, end, repl in reversed(pieces):
        out = out[:start] + repl + out[end:]
    return out


def _protect_and_replace(
    text: str,
    *,
    term_re: Optional[re.Pattern[str]],
    terms: dict,
    defaults: dict,
    base_url: str,
    seed: str,
    state: dict,
    intensity: str = "aggressive",
) -> str:
    masker = _Masker()
    text = _mask_safe_zones(text, masker)

    if term_re is not None:
        if intensity == "aggressive":
            def _replace_term(m: re.Match) -> str:
                term = m.group(0)
                variants = terms[term]
                crc_input = f"{seed}:{term}:{state['occurrence']}"
                state["occurrence"] += 1
                variant = variants[zlib.crc32(crc_input.encode("utf-8")) % len(variants)]
                return _render_variant(base_url, term, variant, defaults)

            text = term_re.sub(_replace_term, text)
        else:
            text = _filtered_replace(
                text,
                term_re=term_re,
                terms=terms,
                defaults=defaults,
                base_url=base_url,
                seed=seed,
                state=state,
                intensity=intensity,
            )

    return masker.restore(text)


def _transform_line(
    line: str,
    *,
    term_re: Optional[re.Pattern[str]],
    terms: dict,
    defaults: dict,
    base_url: str,
    seed: str,
    state: dict,
    intensity: str = "aggressive",
) -> str:
    def handler(segment: str) -> str:
        return _protect_and_replace(
            segment,
            term_re=term_re, terms=terms, defaults=defaults,
            base_url=base_url, seed=seed, state=state,
            intensity=intensity,
        )

    return _scan_summary_aware(line, state, handler)


__all__ = [
    "_protect_and_replace",
    "_transform_line",
]
