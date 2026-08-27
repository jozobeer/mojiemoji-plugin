"""Single provenance for cross-script constants.

Source of truth for the canonical font / animation / forbidden-color
sets — used by the renderer and the prestamp passes in this package,
and by anything built on top of it. In the plugin repository those
downstream consumers are the skill scripts (`bump_catalog`,
`cache_record`, `cache_stats`, `generate_catalog`) and the hook
validators under `hooks/gate/validators/`, which reach these values
through the ordinary `from mojiemoji.lib.constants import …`.

Drift between these constants and the plugin's parameter reference is
caught by that repository's `scripts/verify-lists-vs-docs.sh`.
"""

from __future__ import annotations

import os
import re


DEFAULT_BASE_URL = "https://mojiemoji.jozo.beer"

#: Environment variable that points the renderer at another instance.
BASE_URL_ENV = "MOJIEMOJI_BASE_URL"


def default_base_url() -> str:
    """Base URL of the mojiemoji service to render against.

    Resolution order is caller argument > ``MOJIEMOJI_BASE_URL`` >
    the hosted default, so pointing the pipeline at a self-hosted
    instance needs no code change. Read on every call rather than at
    import time so a caller can set the variable and still be heard.
    """
    return os.environ.get(BASE_URL_ENV, "").strip() or DEFAULT_BASE_URL


def stamp_url_pattern() -> str:
    """Regex source matching one rendered stamp URL, up to its delimiter.

    Derived from the same configuration the renderers build against, so
    a body decorated for a self-hosted instance is still recognized by
    the tools that read stamps back. The hosted default is accepted
    alongside the configured one, so a body written on another machine
    does not become unreadable here. Delimiters: whitespace, `"`, `<`,
    `>`, `)` — the first characters that can end a URL in markdown or
    HTML, so per-URL query parameters stay inspectable.
    """
    origins = dict.fromkeys(
        re.escape(base.split("://", 1)[-1].rstrip("/"))
        for base in (default_base_url(), DEFAULT_BASE_URL)
    )
    return r"https?://(?:%s)/[^\s\"<>)]+" % "|".join(origins)


def stamp_url_re() -> "re.Pattern[str]":
    """Compiled `stamp_url_pattern`, resolved per call like `default_base_url`."""
    return re.compile(stamp_url_pattern())


CANONICAL_FONTS: tuple[str, ...] = (
    "akzk", "chikara", "dela", "gothic", "gothic-bold", "hachimaru",
    "kurobara", "maru", "maru-bold", "mincho", "noto", "pixel",
    "rampart", "tamanegi", "toge", "zero",
)


CANONICAL_ANIMATIONS: tuple[str, ...] = (
    "bakusan", "bane", "bure", "chirichiri", "chuuou_zoom", "disco",
    "darker_zairu", "ekken", "gatagata", "kage_bokashi", "kage_kaiten",
    "kage_neon", "kaiten", "kira", "kirari", "lighter_zairu",
    "mabataki", "mochimochi", "mozaiku", "nami", "neruneru", "norinori",
    "patapata", "poyoon", "psycho", "shuchusen", "tate_ekken",
    "tate_scroll", "tatemoya", "tenmetsu", "yatta", "yoko_scroll",
    "yokomoya", "yurayura", "zairu", "zanzo",
)


# Animations whose hue shifts per frame. Outlines fight the effect so
# the rendering helpers strip outline parameters for these, and the
# hook tolerates the absence.
COLOR_SHIFTING_ANIMATIONS = frozenset({"kira", "disco", "psycho"})


# Animations that rotate the glyph — `kaiten` requires `speed=slow`
# at body height because the default speed shears the kanji.
ROTATIONAL_ANIMATIONS = frozenset({"kaiten", "kage_kaiten"})


# Block-only or otherwise illegible at h=24 inline. Excluded from
# auto-selection pools.
INLINE_PROBLEMATIC_ANIMATIONS = frozenset({"bakusan", "chuuou_zoom"})


# Tailwind 600+ palette values that render black-on-dark in GitHub's
# dark theme. Generators must not pick from this set; the hook's
# `canonical` validator (`hooks/gate/validators/canonical.py`) rejects
# URLs containing them via `FORBIDDEN_COLORS` imported from here.
# `scripts/verify-canonical-lists.sh` cross-checks for drift.
FORBIDDEN_COLORS = frozenset({
    "dc2626", "b91c1c", "991b1b",        # red-600/700/800
    "c2410c",                            # orange-700
    "ca8a04",                            # yellow-600
    "15803d", "16a34a",                  # green-700/600
    "0e7490",                            # cyan-700
    "1d4ed8", "2563eb",                  # blue-700/600
    "4338ca",                            # indigo-700
    "7e22ce",                            # purple-700
    "be185d",                            # pink-700
    "000000", "111827", "1f2937",        # black / gray-900/800
})
