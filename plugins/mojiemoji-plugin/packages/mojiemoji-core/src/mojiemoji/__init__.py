"""mojiemoji — turn Japanese Markdown into mojiemoji image stamps.

Pure transforms only. Nothing in this package knows about GitHub, a
repository's settings, a cache, or an AI harness: callers decide when to
run it and what to do with the result.

    from mojiemoji import transform, load_catalog, report_unstamped

    stamped = transform(markdown_text)

The catalogs ship inside the package, so an installed wheel needs no
files from the source repository.
"""

from __future__ import annotations

from mojiemoji.lib.constants import (
    BASE_URL_ENV,
    DEFAULT_BASE_URL,
    default_base_url,
)
from mojiemoji.markdown import render
from mojiemoji.prestamp import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_EMOJI_CATALOG_PATH,
    load_catalog,
    load_emoji_catalog,
    prestamp_text,
    report_unstamped,
    transform,
)

__all__ = [
    "BASE_URL_ENV",
    "DEFAULT_BASE_URL",
    "DEFAULT_CATALOG_PATH",
    "DEFAULT_EMOJI_CATALOG_PATH",
    "default_base_url",
    "load_catalog",
    "load_emoji_catalog",
    "prestamp_text",
    "render",
    "report_unstamped",
    "transform",
]
