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


def _load_catalog() -> dict:
    """Parse the catalog YAML via PyYAML (declared dependency since #57)."""
    return yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))


# Parse once at module load — pytest.mark.parametrize is evaluated at
# collection time before any fixtures, so we cannot defer this.
_CATALOG = _load_catalog()

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
    return _CATALOG


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


@pytest.mark.parametrize("emoji,variants", list(_CATALOG["emojis"].items()))
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


def test_no_bakusan_in_catalog(catalog):
    # bakusan is canonically block-only — its radial burst obscures the
    # glyph at inline 24px and `generate_catalog.py` explicitly excludes it
    # from the inline pool (`INLINE_PROBLEMATIC_ANIMATIONS`). The emoji
    # catalog is *only* consumed for inline trailing decorations, so any
    # bakusan variant here would generate unreadable stamps.
    offending = [
        (emoji, idx, v["animation"])
        for emoji, variants in catalog["emojis"].items()
        for idx, v in enumerate(variants)
        if v["animation"] == "bakusan"
    ]
    assert not offending, f"bakusan is block-only; remove from inline catalog: {offending}"


def test_vs16_emoji_keys_use_base_codepoint(catalog):
    # Catalog keys are base codepoints (`❤` = U+2764, `⚠` = U+26A0) without
    # the U+FE0F variation selector. This is the intentional convention —
    # SKILL.md's lookup procedure must strip VS16 from inputs before
    # querying. This test pins the convention so a future contributor
    # doesn't accidentally mix VS16-suffixed keys into the catalog (which
    # would create two non-mergeable lookup paths for the same emoji).
    vs16 = "️"
    mixed = [k for k in catalog["emojis"].keys() if vs16 in k]
    assert not mixed, (
        f"catalog keys must not contain U+FE0F; mix found: {mixed!r}. "
        "SKILL.md's procedure strips VS16 before lookup — adding aliases "
        "would split the canonical key set."
    )


def test_all_hex_color_values_are_strings(catalog):
    # YAML auto-types bare hex values that happen to be all digits
    # (e.g. "123456" parses as integer 123456 in some parsers, or as
    # string in others depending on length/leading char). The
    # convention in this project (per prestamp-catalog.yml header) is
    # to always quote hex strings so the type stays predictable across
    # YAML implementations. This test catches drift if someone adds a
    # bare hex value to a new entry.
    offending = []
    for emoji, variants in catalog["emojis"].items():
        for idx, v in enumerate(variants):
            for field in ("color", "outline"):
                val = v.get(field)
                if val is not None and not isinstance(val, str):
                    offending.append((emoji, idx, field, type(val).__name__, val))
    assert not offending, (
        f"hex color/outline values must be strings (quote in YAML): {offending}"
    )
