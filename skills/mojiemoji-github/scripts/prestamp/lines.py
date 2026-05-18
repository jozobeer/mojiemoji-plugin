"""Line-level iteration that respects fences, escape markers, and <summary>.

Both transform passes (text catalog, emoji catalog) walk the input the
same way: they skip CommonMark fenced code blocks, honor the
``<!-- mojiemoji:off -->`` / ``:on`` author-controlled escape (#91), and
preserve content inside ``<summary>…</summary>`` so disclosure-widget
headings are stamp-free.

Off-regions take precedence over fence state — a fence opened inside an
off-region stays raw without flipping ``in_fence``, so the on-marker
reliably resumes prose handling no matter what shape the disabled body
has.
"""

from __future__ import annotations

import re
from typing import Optional

# Fenced code blocks: CommonMark allows up to 3 leading spaces, and either
# ``` or ~~~ as the fence marker. The opening fence's marker and length
# determine the closing fence — track both.
FENCE_RE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})")

# Author-controlled escape. `<!-- mojiemoji:off -->` on its own line
# (whitespace allowed) freezes both passes verbatim until a matching
# `<!-- mojiemoji:on -->` line or EOF. Evaluated before fence detection
# so off-regions can quarantine entire sections including code fences
# and before/after examples (#91). Nesting is flat: redundant off
# inside an already-off region and redundant on outside any off region
# are both no-ops. Markers themselves are HTML comments — GitHub
# renders nothing for them, so they leave no visible trace.
DISABLE_OPEN_LINE_RE = re.compile(r"^\s*<!--\s*mojiemoji:off\s*-->\s*$")
DISABLE_CLOSE_LINE_RE = re.compile(r"^\s*<!--\s*mojiemoji:on\s*-->\s*$")

_SUMMARY_OPEN_RE = re.compile(r"<summary\b[^>]*>")
_SUMMARY_CLOSE_RE = re.compile(r"</summary>")


def _inside_inline_code(line: str, pos: int) -> bool:
    """Return True if ``line[pos]`` falls inside an inline code span.

    Approximate: counts unescaped backticks before ``pos`` on the same
    line — odd count = inside. Handles the common `<details>/<summary>`
    documentation case (e.g. ``the `<details>/<summary>` element``)
    where a literal `<summary>` token sits between matched backticks but
    is not preceded by a backtick directly. Without this check the
    state machine flips into "skip until </summary>" mode and silently
    drops every catalog hit until a real `</summary>` shows up (which
    can be never — the issue body for #91 lost 58 stamps to this).
    """
    return line[:pos].count("`") % 2 == 1


def _find_real_summary_tag(pattern: re.Pattern[str], line: str, start: int) -> Optional[re.Match]:
    """Like ``pattern.search(line, start)`` but skips matches inside
    inline code spans.
    """
    cursor = start
    while True:
        m = pattern.search(line, cursor)
        if m is None:
            return None
        if not _inside_inline_code(line, m.start()):
            return m
        cursor = m.end()


def _scan_summary_aware(line: str, state: dict, prose_handler) -> str:
    """Process a line, calling ``prose_handler`` on prose segments.

    Content inside ``<summary>…</summary>`` is preserved verbatim —
    summary text is a heading that the user wrote intentionally, and
    stamping into it both visually conflicts with the disclosure-widget
    UX and would have to be reapplied on every fold/unfold.

    ``state["in_summary"]`` carries the open/close state across lines.
    Used by both the text-catalog pass and the emoji-catalog pass so
    the two stay symmetric (codex P2 found that the emoji pass alone
    was stamping inside ``<summary>``, breaking that symmetry).
    """
    out = []
    cursor = 0
    while True:
        if state["in_summary"]:
            close = _find_real_summary_tag(_SUMMARY_CLOSE_RE, line, cursor)
            if close:
                out.append(line[cursor : close.end()])
                cursor = close.end()
                state["in_summary"] = False
                continue
            out.append(line[cursor:])
            break

        open_match = _find_real_summary_tag(_SUMMARY_OPEN_RE, line, cursor)
        if open_match:
            segment = line[cursor : open_match.start()]
            out.append(prose_handler(segment))
            out.append(open_match.group(0))
            cursor = open_match.end()
            state["in_summary"] = True
            continue

        out.append(prose_handler(line[cursor:]))
        break
    return "".join(out)


def _walk_lines_outside_fences(text: str):
    """Yield (line, is_prose) tuples for the transform passes.

    Tracks three forms of "skip this line": CommonMark fences,
    fence-marker lines themselves, and the author-controlled
    ``<!-- mojiemoji:off/on -->`` escape (#91). Off-regions take
    precedence over fence state — a fence opened inside an off-region
    stays raw without flipping ``in_fence`` so the on-marker reliably
    resumes prose handling no matter what shape the disabled body has.
    """
    in_fence = False
    fence_marker: Optional[str] = None
    in_disabled = False
    for line in text.splitlines(keepends=True):
        if in_disabled:
            if DISABLE_CLOSE_LINE_RE.match(line):
                in_disabled = False
            yield line, False
            continue
        if DISABLE_OPEN_LINE_RE.match(line):
            in_disabled = True
            yield line, False
            continue

        m = FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            if in_fence:
                if marker[0] == fence_marker[0] and len(marker) >= len(fence_marker):
                    in_fence = False
                    fence_marker = None
            else:
                in_fence = True
                fence_marker = marker
            yield line, False
        elif in_fence:
            yield line, False
        else:
            yield line, True


__all__ = [
    "DISABLE_CLOSE_LINE_RE",
    "DISABLE_OPEN_LINE_RE",
    "FENCE_RE",
    "_scan_summary_aware",
    "_walk_lines_outside_fences",
]
