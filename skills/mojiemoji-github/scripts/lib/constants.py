"""Single provenance for cross-script constants.

Source of truth for every consumer that needs canonical font /
animation / forbidden-color sets:

- skill scripts: `bump_catalog`, `cache_record`, `cache_stats`,
  `generate_catalog`, `mojiemoji_markdown`, `prestamp`
- hook validators: `hooks/gate/validators/canonical.py`,
  `required_params.py` (the hook decomposition in #101 spliced
  `skills/mojiemoji-github/scripts/` onto `sys.path` so the
  validators can `from lib.constants import …` directly)

Drift between these constants and the docs in
`skills/mojiemoji-github/references/parameters.md` is caught by
`scripts/verify-lists-vs-docs.sh`.
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
