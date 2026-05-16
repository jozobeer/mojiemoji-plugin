"""Single provenance for cross-script constants.

Previously duplicated across `bump_catalog`, `cache_record`,
`cache_stats`, `generate_catalog`, `mojiemoji_markdown`, and
`prestamp`. The hook (`hooks/mojiemoji-japanese-gate.py`) still keeps
its own copy because it is loaded outside the skills directory and
cannot import from this package — keep that copy in sync until the
hook decomposition (issue #54 Step 4) lands.

Canonical font / animation values mirror what
`hooks/mojiemoji-japanese-gate.py` validates against and what
`skills/mojiemoji-github/references/parameters.md` documents. Drift is
caught by `scripts/verify-canonical-lists.sh`.
"""

from __future__ import annotations


DEFAULT_BASE_URL = "https://mojiemoji.jozo.beer"


CANONICAL_FONTS: tuple[str, ...] = (
    "akzk", "chikara", "dela", "gothic", "gothic-bold", "hachimaru",
    "kurobara", "maru", "maru-bold", "mincho", "noto", "pixel",
    "rampart", "tamanegi", "toge", "zero",
)


CANONICAL_ANIMATIONS: tuple[str, ...] = (
    "bakusan", "bane", "bure", "chirichiri", "chuuou_zoom", "disco",
    "ekken", "gatagata", "kage_bokashi", "kage_kaiten", "kage_neon",
    "kaiten", "kira", "kirari", "mabataki", "mochimochi", "mozaiku",
    "nami", "neruneru", "norinori", "patapata", "poyoon", "psycho",
    "shuchusen", "tate_ekken", "tate_scroll", "tatemoya", "tenmetsu",
    "yatta", "yoko_scroll", "yokomoya", "yurayura", "zairu", "zanzo",
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
# dark theme. Generators must not pick from this set; the hook
# (`hooks/mojiemoji-japanese-gate.py:222`) rejects URLs containing
# them. Keep this list in lockstep with the hook's `FORBIDDEN_COLORS`
# until the hook can import from this package. `scripts/verify-
# canonical-lists.sh` cross-checks for drift.
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
