"""Find prose Japanese runs that survived the prestamp transform.

After a full transform, any 2-8 char contiguous Kanji or Katakana run
that still lives in prose is a catalog-promotion candidate (#92 / #93):
the term was either novel, longer than the sliding window, or simply
uncatalogued. The report walks the transformed text fence-aware and
summary-aware, masks the same safe zones as the transform passes —
including the `<img>` stamps emitted by prestamp — then scans the
remaining prose with ``JAPANESE_RUN_RE``.
"""

from __future__ import annotations

import re

from mojiemoji.prestamp.boundaries import JAPANESE_RUN_RE
from mojiemoji.prestamp.lines import (
    _observe_summary_tags,
    _scan_summary_aware,
    _walk_lines_outside_fences_with_reason,
)
from mojiemoji.prestamp.masker import _Masker, _mask_safe_zones

UNSTAMPED_CONTEXT_RADIUS = 20
UNSTAMPED_MAX_CONTEXTS_PER_TERM = 3
# When a context window slice cuts a `__MOJIEMOJI_MASK_<n>__` token at
# either edge, the partial fragment fails to restore. Render restored
# `<img>` stamps and orphan fragments as a single ellipsis so the user
# sees the term in clean surrounding prose, not URL-laden HTML.
_PARTIAL_MASK_RE = re.compile(r"[A-Z0-9_]*__[A-Z0-9_]*")
_RESTORED_IMG_RE = re.compile(r"<img [^>]+>")


def report_unstamped(text: str) -> dict:
    """Return ``{"unstamped": [{"term", "count", "contexts"}, ...]}``.

    Sorted by descending count, then term ascending. ``contexts`` is a
    list of up to ``UNSTAMPED_MAX_CONTEXTS_PER_TERM`` snippets with
    ``UNSTAMPED_CONTEXT_RADIUS`` chars on either side of each
    occurrence; mask tokens are restored, then collapsed back to a
    single ellipsis so the snippet reads as prose, not HTML.
    """
    candidates: dict[str, dict] = {}

    def observe(segment: str) -> str:
        masker = _Masker()
        masked = _mask_safe_zones(segment, masker)
        for m in JAPANESE_RUN_RE.finditer(masked):
            term = m.group(0)
            start, end = m.start(), m.end()
            ctx_start = max(0, start - UNSTAMPED_CONTEXT_RADIUS)
            ctx_end = min(len(masked), end + UNSTAMPED_CONTEXT_RADIUS)
            context = masker.restore(masked[ctx_start:ctx_end])
            context = _RESTORED_IMG_RE.sub("…", context)
            context = _PARTIAL_MASK_RE.sub("…", context)
            context = context.strip()
            entry = candidates.setdefault(term, {"count": 0, "contexts": []})
            entry["count"] += 1
            if len(entry["contexts"]) < UNSTAMPED_MAX_CONTEXTS_PER_TERM:
                entry["contexts"].append(context)
        return segment

    state = {"in_summary": False}
    for line, is_prose, reason in _walk_lines_outside_fences_with_reason(text):
        if is_prose:
            _scan_summary_aware(line, state, observe)
        elif reason == "disabled":
            _observe_summary_tags(line, state)

    return {
        "unstamped": [
            {"term": t, "count": v["count"], "contexts": v["contexts"]}
            for t, v in sorted(
                candidates.items(),
                key=lambda kv: (-kv[1]["count"], kv[0]),
            )
        ]
    }


__all__ = [
    "UNSTAMPED_CONTEXT_RADIUS",
    "UNSTAMPED_MAX_CONTEXTS_PER_TERM",
    "report_unstamped",
]
