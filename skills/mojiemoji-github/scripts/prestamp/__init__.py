"""prestamp — replace catalog terms in markdown with mojiemoji <img>.

Public API re-exported here so existing call sites keep working:

    from prestamp import transform, load_catalog, report_unstamped
    from prestamp import ASCII_KEY_RE, ASCII_LEFT_GUARD, ASCII_RIGHT_GUARD

The `prestamp.py` shim alongside this package still exists so
``python3 prestamp.py < input.md > output.md`` keeps working as the
documented CLI entry — it imports `main` from this package and runs it.
Python's import system resolves ``import prestamp`` to this package
(packages take precedence over same-name modules in the same dir), so
both invocation modes coexist cleanly.
"""

from __future__ import annotations

from prestamp.boundaries import (
    ASCII_KEY_RE,
    ASCII_LEFT_GUARD,
    ASCII_RIGHT_GUARD,
    DIGIT_CHAR_RE,
    HAN_CHAR_RE,
    HAN_RANGE,
    HIRAGANA_RANGE,
    JAPANESE_RUN_RE,
    KATAKANA_RANGE,
    SINGLE_DIGIT_LEFT_GUARD,
    SINGLE_DIGIT_RIGHT_GUARD,
    SINGLE_HAN_LEFT_GUARD,
)
from prestamp.catalog import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_EMOJI_CATALOG_PATH,
    MAX_EMOJI_RUN,
    VS16,
    build_emoji_re,
    build_term_re,
    load_catalog,
    load_emoji_catalog,
)
from prestamp.cli import main, prestamp_text, transform
from prestamp.lines import (
    DISABLE_CLOSE_LINE_RE,
    DISABLE_OPEN_LINE_RE,
    FENCE_RE,
)
from prestamp.unstamped_report import report_unstamped

__all__ = [
    "ASCII_KEY_RE",
    "ASCII_LEFT_GUARD",
    "ASCII_RIGHT_GUARD",
    "DEFAULT_CATALOG_PATH",
    "DEFAULT_EMOJI_CATALOG_PATH",
    "DIGIT_CHAR_RE",
    "DISABLE_CLOSE_LINE_RE",
    "DISABLE_OPEN_LINE_RE",
    "FENCE_RE",
    "HAN_CHAR_RE",
    "HAN_RANGE",
    "HIRAGANA_RANGE",
    "JAPANESE_RUN_RE",
    "KATAKANA_RANGE",
    "MAX_EMOJI_RUN",
    "SINGLE_DIGIT_LEFT_GUARD",
    "SINGLE_DIGIT_RIGHT_GUARD",
    "SINGLE_HAN_LEFT_GUARD",
    "VS16",
    "build_emoji_re",
    "build_term_re",
    "load_catalog",
    "load_emoji_catalog",
    "main",
    "prestamp_text",
    "report_unstamped",
    "transform",
]
