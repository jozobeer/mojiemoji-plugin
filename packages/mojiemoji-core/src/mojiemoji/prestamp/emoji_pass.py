"""Emoji-catalog substitution pass — replace Unicode emoji with `<img>`.

Pass 2 runs after the text-catalog pass. Re-masks all safe zones,
including the `<img>` tags emitted by pass 1, then substitutes catalog
emoji while capping consecutive adjacent hits at ``MAX_EMOJI_RUN`` to
avoid the visually crowded ``🎉🎊🎁🎀`` case. The cap is reset by any
whitespace, other glyph, or already-masked span (because masks become
opaque sentinel tokens that the emoji regex never matches).
"""

from __future__ import annotations

import re
import zlib

from mojiemoji.prestamp.catalog import MAX_EMOJI_RUN, VS16
from mojiemoji.prestamp.lines import _scan_summary_aware
from mojiemoji.prestamp.masker import _Masker, _mask_safe_zones
from mojiemoji.prestamp.render import _render_variant


def _emoji_replace_line(
    line: str,
    *,
    emoji_re: re.Pattern[str],
    emojis: dict,
    defaults: dict,
    base_url: str,
    seed: str,
    state: dict,
    max_emoji_run: int = MAX_EMOJI_RUN,
) -> str:
    """Run the emoji pass on a single non-fenced line.

    Masks the same safe zones as the text pass — including `<img>`
    tags emitted by the text pass — and then replaces Unicode emoji
    that are catalog hits with rendered stamps. Catalog misses stay
    raw.     A run of more than ``max_emoji_run`` adjacent catalog hits
    leaves the overflow as raw Unicode to avoid visual crowding.
    """
    masker = _Masker()
    line = _mask_safe_zones(line, masker)

    run_state = {"last_end": -1, "run": 0}

    def _replace_emoji(m: re.Match) -> str:
        if m.start() == run_state["last_end"]:
            run_state["run"] += 1
        else:
            run_state["run"] = 1
        run_state["last_end"] = m.end()

        if run_state["run"] > max_emoji_run:
            return m.group(0)

        # The regex absorbs an optional trailing VS16, but the catalog
        # is keyed by the bare base codepoint. Strip VS16 for lookup
        # and for the stamp's alt text — catalog-miss emoji never enter
        # this branch because their codepoint is not in the alternation,
        # so their VS16 is preserved by the regex never matching them.
        emoji = m.group(0).replace(VS16, "")
        variants = emojis[emoji]
        crc_input = f"{seed}:{emoji}:{state['occurrence']}"
        state["occurrence"] += 1
        variant = variants[zlib.crc32(crc_input.encode("utf-8")) % len(variants)]
        return _render_variant(base_url, emoji, variant, defaults)

    line = emoji_re.sub(_replace_emoji, line)
    return masker.restore(line)


def _emoji_transform_line(
    line: str,
    *,
    emoji_re: re.Pattern[str],
    emojis: dict,
    defaults: dict,
    base_url: str,
    seed: str,
    state: dict,
    max_emoji_run: int = MAX_EMOJI_RUN,
) -> str:
    def handler(segment: str) -> str:
        return _emoji_replace_line(
            segment,
            emoji_re=emoji_re, emojis=emojis, defaults=defaults,
            base_url=base_url, seed=seed, state=state,
            max_emoji_run=max_emoji_run,
        )

    return _scan_summary_aware(line, state, handler)


__all__ = [
    "_emoji_replace_line",
    "_emoji_transform_line",
]
