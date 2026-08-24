"""Load + compile the text and emoji catalogs.

The text catalog (``prestamp-catalog.yml``) is a flat dict of
``term -> [variant, ...]``; the emoji catalog (``emoji-catalog.yml``)
mirrors that shape under ``emojis:`` instead of ``terms:``.

The term regex is built in 4 tiers:

  1. Multi-char ASCII-only keys (``URL``, ``PR``, ``OS`` …) wrapped in
     identifier-boundary guards so ``OS`` doesn't match inside ``POST``.
  2. Multi-char non-ASCII keys — plain alternation; can't appear inside
     ASCII identifiers anyway.
  3. Single Han keys — guarded against trailing-of-compound and against
     the masker's ``__MOJIEMOJI_MASK_<n>__`` sentinel tail.
  4. Single ASCII digits — only when embedded in Japanese flow.
"""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path
from typing import Optional

try:
    import yaml
except ModuleNotFoundError as exc:
    raise SystemExit(
        "PyYAML is required to read mojiemoji catalogs. Install it with "
        "`python3 -m pip install --user 'pyyaml>=6.0'`, or run from the "
        "repository with `uv run ...`."
    ) from exc

from mojiemoji.prestamp.boundaries import (
    ASCII_KEY_RE,
    ASCII_LEFT_GUARD,
    ASCII_RIGHT_GUARD,
    DIGIT_CHAR_RE,
    HAN_CHAR_RE,
    SINGLE_DIGIT_LEFT_GUARD,
    SINGLE_DIGIT_RIGHT_GUARD,
    SINGLE_HAN_LEFT_GUARD,
)

# Catalogs ship inside the package, so they resolve from an installed
# wheel as well as from a source checkout. Walking out of the package
# with ``__file__`` only works in the repository layout.
_DATA = files("mojiemoji.data")
DEFAULT_CATALOG_PATH = _DATA / "prestamp-catalog.yml"
DEFAULT_EMOJI_CATALOG_PATH = _DATA / "emoji-catalog.yml"


def _open_text(path):
    """Open a catalog for reading.

    Accepts both a filesystem path and the ``Traversable`` that
    ``importlib.resources`` hands back, which is not guaranteed to be
    ``os.PathLike``.
    """
    opener = getattr(path, "open", None)
    if opener is None:
        return open(path, encoding="utf-8")
    return opener(encoding="utf-8")


def catalog_exists(path) -> bool:
    """Whether a catalog is readable, for paths and resources alike."""
    is_file = getattr(path, "is_file", None)
    return bool(is_file()) if is_file is not None else Path(path).exists()

# Variation selector U+FE0F. Catalog keys are bare base codepoints
# (`⚠` not `⚠️`), per emoji-catalog.yml convention pinned by
# test_vs16_emoji_keys_use_base_codepoint. Strip from inputs before
# emoji lookup so `⚠️` (U+26A0 U+FE0F) still hits the `⚠` key.
VS16 = "️"

# Max consecutive emoji stamps in a single uninterrupted run. The 3rd
# (and beyond) emoji in `🎉🎊🎁🎀` stays raw Unicode — visually crowded
# stamps lose punch. Whitespace, other glyphs, or pre-existing `<img>`
# spans break the run.
MAX_EMOJI_RUN = 2


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> tuple[dict, dict]:
    """Return (defaults, terms) from a prestamp-catalog YAML file."""
    with _open_text(path) as f:
        data = yaml.safe_load(f) or {}
    defaults = data.get("defaults") or {}
    terms = {}
    for key, variants in (data.get("terms") or {}).items():
        # YAML auto-parses bare integer keys to int; coerce back to str so
        # the catalog regex (which is built over .keys()) works uniformly.
        terms[str(key)] = [dict(v) for v in (variants or [])]
    return defaults, terms


def build_term_re(terms: dict) -> Optional[re.Pattern[str]]:
    """Compile the 4-tier alternation pattern (ascii / multi / kanji / digit).

    Multi-char ASCII-only keys (``URL``, ``PR``, ``API``, ``OS`` …)
    need word boundaries — without them ``OS`` matches inside ``POST``
    and ``CI`` matches inside ``ASCII``, splitting identifiers into
    ``P<OS>T`` / ``AS<CI>I``. Non-ASCII multi-char keys (Kanji /
    Katakana compounds) don't need this guard because they can't
    appear inside ASCII identifiers anyway, and adding boundaries
    there would over-block legitimate Japanese contexts.
    """
    multi_keys_all = sorted(
        (k for k in terms if len(k) > 1),
        key=lambda t: (-len(t), t),
    )
    ascii_keys = [k for k in multi_keys_all if ASCII_KEY_RE.match(k)]
    other_multi_keys = [k for k in multi_keys_all if not ASCII_KEY_RE.match(k)]
    kanji_keys = [k for k in terms if len(k) == 1 and HAN_CHAR_RE.match(k)]
    digit_keys = [k for k in terms if len(k) == 1 and DIGIT_CHAR_RE.match(k)]

    parts = []
    if ascii_keys:
        parts.append(
            f"(?:{ASCII_LEFT_GUARD}(?:"
            + "|".join(re.escape(k) for k in ascii_keys)
            + f"){ASCII_RIGHT_GUARD})"
        )
    if other_multi_keys:
        parts.append("(?:" + "|".join(re.escape(k) for k in other_multi_keys) + ")")
    if kanji_keys:
        parts.append(
            f"(?:{SINGLE_HAN_LEFT_GUARD}(?:"
            + "|".join(re.escape(k) for k in kanji_keys)
            + "))"
        )
    if digit_keys:
        parts.append(
            f"(?:{SINGLE_DIGIT_LEFT_GUARD}(?:"
            + "|".join(re.escape(k) for k in digit_keys)
            + f"){SINGLE_DIGIT_RIGHT_GUARD})"
        )

    if not parts:
        return None
    return re.compile("|".join(parts))


def load_emoji_catalog(path: Path = DEFAULT_EMOJI_CATALOG_PATH) -> tuple[dict, dict]:
    """Return (defaults, emojis) from the emoji-catalog YAML file.

    Mirrors load_catalog() but reads the ``emojis:`` top-level key
    instead of ``terms:``. Values are kept as-is so the renderer sees
    the same per-variant schema (font / color / animation / outline /
    speed) as text catalog variants.
    """
    with _open_text(path) as f:
        data = yaml.safe_load(f) or {}
    defaults = data.get("defaults") or {}
    emojis = {}
    for key, variants in (data.get("emojis") or {}).items():
        emojis[str(key)] = [dict(v) for v in (variants or [])]
    return defaults, emojis


def build_emoji_re(emojis: dict) -> Optional[re.Pattern[str]]:
    """Compile an alternation regex matching any catalog emoji.

    Each key is followed by an optional ``️`` (VS16) so the same
    pattern catches both bare (`⚠`) and VS16-suffixed (`⚠️`) inputs —
    catalog keys are always stored bare per the
    ``test_vs16_emoji_keys_use_base_codepoint`` convention. Consuming
    VS16 *only when it follows a catalog hit* preserves VS16 on
    catalog-miss glyphs like `❤️` / `☀️`, which would otherwise
    silently drop their emoji presentation selector.
    """
    keys = sorted(emojis.keys(), key=lambda k: (-len(k), k))
    if not keys:
        return None
    return re.compile("|".join(re.escape(k) + r"️?" for k in keys))


__all__ = [
    "DEFAULT_CATALOG_PATH",
    "catalog_exists",
    "DEFAULT_EMOJI_CATALOG_PATH",
    "MAX_EMOJI_RUN",
    "VS16",
    "build_emoji_re",
    "build_term_re",
    "load_catalog",
    "load_emoji_catalog",
]
