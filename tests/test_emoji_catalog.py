"""Validate skills/mojiemoji-github/data/emoji-catalog.yml against the canonical
parameter sets enforced by hooks/mojiemoji-japanese-gate.py.

The catalog is consumed by SKILL.md (trailing-decoration 2-step rule) and may
later be consumed by a render helper / prestamp integration. Either way every
variant must satisfy the same hook rules that text stamps do — otherwise
trailing decorations will be silently rejected at submission time.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "emoji-catalog.yml"

# Canonical lists must mirror parameters.md / hook constants. Kept inline so the
# test catches drift in either direction (catalog adds value not in canon, or
# canon shrinks under an existing catalog entry).
CANONICAL_ANIMATIONS = frozenset({
    "tate_scroll", "yoko_scroll", "ekken", "tate_ekken", "bane", "gatagata",
    "bure", "chuuou_zoom", "kirari", "kira", "tenmetsu", "shuchusen", "kaiten",
    "neruneru", "patapata", "yurayura", "mabataki", "bakusan", "norinori",
    "mochimochi", "mozaiku", "poyoon", "yatta", "tatemoya", "nami", "yokomoya",
    "zairu", "zanzo", "chirichiri", "disco", "psycho", "kage_kaiten",
    "kage_bokashi", "kage_neon",
})
CANONICAL_FONTS = frozenset({
    "maru-bold", "gothic-bold", "noto", "dela", "akzk", "zero", "kurobara",
    "hachimaru", "chikara", "tamanegi", "toge", "rampart", "maru", "gothic",
    "mincho", "pixel",
})
# Mirrors FORBIDDEN_COLORS in hooks/mojiemoji-japanese-gate.py. Tailwind 600+
# fills (and near-black greys) go invisible on dark mode.
FORBIDDEN_COLORS = frozenset({
    "dc2626", "b91c1c", "991b1b",
    "c2410c",
    "ca8a04",
    "15803d", "16a34a",
    "0e7490",
    "1d4ed8", "2563eb",
    "4338ca",
    "7e22ce",
    "be185d",
    "000000", "111827", "1f2937",
})
COLOR_SHIFTING_ANIMATIONS = frozenset({"disco", "psycho", "kira"})
ROTATIONAL_ANIMATIONS = frozenset({"kaiten", "kage_kaiten"})

HEX6_RE = re.compile(r"\A[0-9a-f]{6}\Z")


@pytest.fixture(scope="module")
def catalog():
    return yaml.safe_load(CATALOG_PATH.read_text())


def test_catalog_has_top_level_keys(catalog):
    assert "defaults" in catalog
    assert "emojis" in catalog
    assert catalog["defaults"]["background"] == "transparent"
    assert catalog["defaults"]["outline_width"] == "2"


def test_catalog_covers_full_upstream_count(catalog):
    # Upstream jozobeer/mojiemoji/assets/emoji had 162 PNG files at issue
    # creation. New uploads may grow this number — relax the floor if the test
    # fails after a deliberate sync. The catalog should never *shrink* below
    # the documented baseline without an explicit issue.
    assert len(catalog["emojis"]) >= 162, (
        f"catalog shrank to {len(catalog['emojis'])} entries — restore the baseline"
    )


@pytest.mark.parametrize("emoji,variants", [
    (e, vs) for e, vs in yaml.safe_load(CATALOG_PATH.read_text())["emojis"].items()
])
def test_variants_use_canonical_values(emoji, variants):
    assert 1 <= len(variants) <= 4, f"{emoji}: variant count {len(variants)} outside 1-4"
    for i, v in enumerate(variants):
        assert v["animation"] in CANONICAL_ANIMATIONS, (
            f"{emoji}#{i}: animation {v['animation']!r} not in canonical 34"
        )
        assert v["font"] in CANONICAL_FONTS, (
            f"{emoji}#{i}: font {v['font']!r} not in canonical 16"
        )
        color = v["color"].lower()
        assert HEX6_RE.match(color), f"{emoji}#{i}: color {color!r} not 6-hex"
        assert color not in FORBIDDEN_COLORS, (
            f"{emoji}#{i}: color {color} is in FORBIDDEN_COLORS (Tailwind 600+ / near-black)"
        )
        # Color-shifting animations cycle hue; a fixed outline fights the cycle.
        # Must drop outline entirely and set outline_width to "0".
        if v["animation"] in COLOR_SHIFTING_ANIMATIONS:
            assert "outline" not in v, (
                f"{emoji}#{i}: color-shifting {v['animation']} must not carry outline"
            )
            assert v.get("outline_width") == "0", (
                f"{emoji}#{i}: color-shifting {v['animation']} must set outline_width=0"
            )
        # Rotational animations spin too fast at the service default.
        if v["animation"] in ROTATIONAL_ANIMATIONS:
            assert v.get("speed") in {"slow", "step"}, (
                f"{emoji}#{i}: rotational {v['animation']} must set speed=slow or step"
            )


def test_unsupported_emoji_not_in_catalog(catalog):
    # Sanity: 🚀 (U+1F680) is the canonical "fallback to Unicode" example in
    # SKILL.md and the #51 motivation. If someone adds it to the catalog
    # without also adding the upstream asset, trailing-decoration agents will
    # generate URLs that return placeholder/static GIFs.
    assert "🚀" not in catalog["emojis"], (
        "🚀 (U+1F680) has no upstream asset — it must stay out of the catalog "
        "so the trailing-decoration fallback path keeps using plain Unicode"
    )
