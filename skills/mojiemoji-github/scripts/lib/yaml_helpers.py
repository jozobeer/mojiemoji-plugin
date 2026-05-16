"""YAML value/key quoting helpers used by catalog renderers.

Single provenance for `yaml_value` and `yaml_term_key`. Previously
duplicated across `cache_stats.py` and `bump_catalog.py` with subtly
different rules — `cache_stats.py` had an `Integer` guard for plain
numeric output, `bump_catalog.py` did not. This module is the
integer-aware version, so renderers agree across the catalog
pipeline.
"""

from __future__ import annotations

import re


_IDENT_RE = re.compile(r"\A[a-zA-Z][a-zA-Z0-9_]*\Z")
_HEX6_RE = re.compile(r"\A[0-9a-f]{6}\Z")
_LEADING_DIGIT_RE = re.compile(r"\A\d")
_SAFE_TERM_KEY_RE = re.compile(r"\A[㐀-䶿一-鿿豈-﫿぀-ゟ゠-ヿA-Za-z0-9_]+\Z")


def yaml_value(value: object) -> str:
    """Emit a YAML scalar.

    Plain integers render unquoted; bool is a separate type that must
    be quoted (`"true"`) so the catalog stays string-typed. Strings
    that look like idents render unquoted unless they collide with the
    hex-color shape (always quoted to keep `color: "3b82f6"` from
    parsing as a hex number).
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    s = str(value)
    if _IDENT_RE.match(s) and not _LEADING_DIGIT_RE.match(s) and not _HEX6_RE.match(s):
        return s
    return f'"{s}"'


def yaml_term_key(term: str) -> str:
    """Always quote — term keys may contain YAML-significant characters
    (`:`, `>`, `#`, leading symbols, etc.)."""
    escaped = str(term).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def emit_term_key(term: str) -> str:
    """Quote only when the term contains YAML-unsafe characters.

    Used by `bump_catalog.py` for diff rendering where unquoted keys
    are preferred for legibility. Falls back to fully-escaped quoted
    form when the term isn't in the safe-ident set.
    """
    s = str(term)
    if _SAFE_TERM_KEY_RE.match(s) and not _LEADING_DIGIT_RE.match(s):
        return s
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
