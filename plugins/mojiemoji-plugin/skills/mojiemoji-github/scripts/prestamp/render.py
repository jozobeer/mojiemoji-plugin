"""Render a catalog variant into a mojiemoji ``<img>`` tag.

Forbidden Tailwind 600+ colors are normalized through
``lib/forbidden_colors.py`` as a safety net for hand-written bodies
that hit ``mojiemoji-selector`` or skip the catalog entirely; the
catalog itself was cleaned in #97 so live entries never trigger it.
"""

from __future__ import annotations

import html
import re
from urllib.parse import quote, urlencode

from lib.forbidden_colors import normalize_color_value as _normalize_color_value


PRESTAMP_IMG_RE = re.compile(
    r'<img src="[^"]+/emoji/[^"]+" alt="[^"]*" height="20" align="absmiddle">'
)


def _build_url(base_url: str, text: str, flavor: dict, defaults: dict) -> str:
    merged = {**defaults, **flavor}
    params = [
        ("font", merged.get("font")),
        ("color", _normalize_color_value(merged.get("color"))),
        ("animation", merged.get("animation")),
        ("speed", merged.get("speed")),
        ("background", merged.get("background")),
        ("outline", _normalize_color_value(merged.get("outline"))),
        ("outline_width", merged.get("outline_width")),
    ]
    params = [(k, v) for k, v in params if v is not None]
    encoded = quote(text, safe="")
    return f"{base_url}/emoji/{encoded}?{urlencode(params)}"


def _render_img(base_url: str, text: str, flavor: dict, defaults: dict) -> str:
    url = _build_url(base_url, text, flavor, defaults)
    alt = html.escape(text, quote=True)
    # html.escape with quote=True escapes &, <, >, ", but the Ruby version
    # uses CGI.escapeHTML which also escapes '. Python's html.escape with
    # quote=True does both " and ' since Python 3.2 (' → &#x27;).
    src = html.escape(url, quote=True)
    return f'<img src="{src}" alt="{alt}" height="20" align="absmiddle">'


def _render_variant(base_url: str, term: str, variant: dict, defaults: dict) -> str:
    chunks = variant.get("chunks")
    if not chunks:
        return _render_img(base_url, term, variant, defaults)
    out = []
    for chunk in chunks:
        flavor = {k: v for k, v in chunk.items() if k != "text"}
        out.append(_render_img(base_url, chunk["text"], flavor, defaults))
    return "".join(out)


def _shields_badge_url(url: str) -> bool:
    return bool(re.match(r"\Ahttps?://img\.shields\.io(?:/|\Z)", url, re.IGNORECASE))


__all__ = [
    "PRESTAMP_IMG_RE",
    "_build_url",
    "_render_img",
    "_render_variant",
    "_shields_badge_url",
]
