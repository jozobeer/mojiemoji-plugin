#!/usr/bin/env python3
"""generate_catalog — produce YAML catalog variants for prestamp.py.

Reads a list of stampable terms (one per line) from --input or stdin and
emits a `terms:`-shaped YAML fragment to stdout. Variants are picked
deterministically per term: different font, animation, and color across
the N variants. Outline hex is BGR-rotated from the fill color. Rotational
animations get speed: slow. Color-shifting animations get outline_width: "0"
to suppress the halo. Inline-problematic animations are excluded.

Note: PRNG output differs from the legacy Ruby implementation because
Python's random.Random and Ruby's Random use different MT19937 seeding
and shuffle order. Logic is preserved; specific font/color/animation
picks change per term.
"""

from __future__ import annotations

import argparse
import hashlib
import random
import re
import sys
from typing import Iterable, Optional

from lib.core_path import ensure_core_importable

ensure_core_importable()

from mojiemoji.lib.constants import (
    CANONICAL_ANIMATIONS,
    CANONICAL_FONTS,
    COLOR_SHIFTING_ANIMATIONS,
    FORBIDDEN_COLORS,
    INLINE_PROBLEMATIC_ANIMATIONS,
    ROTATIONAL_ANIMATIONS,
)
from mojiemoji.lib.forbidden_colors import FORBIDDEN_COLOR_REPLACEMENTS
from mojiemoji.lib.japanese_ranges import HAN_RANGE, HIRAGANA_RANGE, KATAKANA_RANGE

from lib.flavor import Flavor


# Tailwind palette used for variant generation. Curated to exclude
# hook-forbidden colors and dark-theme-dim cleanup replacements. The
# runtime filter is defense in depth — kept so any future palette
# regression still gets sanitized — but the source pool remains the
# single provenance.
# `scripts/verify-lists-vs-docs.sh` enforces that the raw palette has
# no overlap with either forbidden set.
_RAW_TAILWIND_PALETTE = (
    "ef4444", "f97316", "fb923c", "f59e0b", "fbbf24",
    "eab308", "22c55e", "34d399", "10b981",
    "06b6d4", "22d3ee", "3b82f6", "60a5fa", "8b5cf6",
    "a78bfa", "a855f7", "c084fc", "d946ef", "ec4899",
    "f472b6", "fb7185", "f43f5e", "fdba74",
)
_GENERATOR_FORBIDDEN_COLORS = FORBIDDEN_COLORS | set(FORBIDDEN_COLOR_REPLACEMENTS)
TAILWIND_PALETTE = tuple(c for c in _RAW_TAILWIND_PALETTE if c not in _GENERATOR_FORBIDDEN_COLORS)

POOLED_ANIMATIONS = tuple(a for a in CANONICAL_ANIMATIONS if a not in INLINE_PROBLEMATIC_ANIMATIONS)

_HAN_RE = re.compile(f"[{HAN_RANGE}]")
_HIRA_RE = re.compile(f"[{HIRAGANA_RANGE}]")
_KATA_RE = re.compile(f"[{KATAKANA_RANGE}]")
_ASCII_RE = re.compile(r"[A-Za-z0-9]")
_DIGIT_KEY_RE = re.compile(r"\A\d+\Z")
_HEX6_RE = re.compile(r"\A[0-9a-fA-F]{6}\Z")


def char_classes(term: str) -> dict[str, int]:
    return {
        "kanji": len(_HAN_RE.findall(term)),
        "hira": len(_HIRA_RE.findall(term)),
        "kata": len(_KATA_RE.findall(term)),
        "ascii": len(_ASCII_RE.findall(term)),
    }


def fits_single_stamp(term: str) -> bool:
    c = char_classes(term)
    jp_chars = c["kanji"] + c["kata"] + c["hira"]
    if jp_chars > 0:
        # Traditional JP morpheme limits (kanji compounds, katakana runs, hiragana)
        return (
            c["kanji"] <= 2
            and c["kata"] <= 3
            and c["hira"] <= 4
            and c["ascii"] <= 3
        )
    # Pure ASCII/Latin terms for English + dev terminology (i18n #148).
    # English words are whole words (not JP-style compounds), so allow
    # up to ~8 chars (e.g. MERGE, REVIEW, SHIP, TODO, PASS, FAIL...).
    return c["ascii"] <= 8


def char_class_of(c: str) -> str:
    if _HAN_RE.match(c):
        return "kanji"
    if _HIRA_RE.match(c):
        return "hira"
    if _KATA_RE.match(c):
        return "kata"
    if _ASCII_RE.match(c):
        return "ascii"
    return "other"


# Common 1-char kanji prefixes that modify a 2-kanji core. Suffix
# nominalizers take priority when both match.
KANJI_PREFIX_MODIFIERS = frozenset({
    "不", "未", "誤", "再", "副", "要", "非", "初", "永", "拡", "超", "最",
    "前", "後", "旧", "新", "全", "半", "各", "同", "異", "逆", "反", "主", "準",
})

KANJI_SUFFIX_NOMINALIZERS = frozenset({
    "度", "性", "化", "像", "点", "感", "観", "論", "様", "力", "法", "体", "系", "軸", "値",
})


def split_term(term: str) -> Optional[tuple[str, str]]:
    """Split into 2 adjacent-stamp chunks when the term exceeds the
    single-stamp length rule. Returns (left, right) or None.

    Priority: character-class boundary → kanji morpheme (suffix > prefix >
    2+1 / 2+2 fallback) → katakana 3+remainder.
    """
    chars = list(term)
    if len(chars) < 2:
        return None
    classes = [char_class_of(c) for c in chars]

    # 1. Character-class boundary.
    for idx in range(1, len(chars)):
        if classes[idx] == classes[idx - 1]:
            continue
        left = "".join(chars[:idx])
        right = "".join(chars[idx:])
        if fits_single_stamp(left) and fits_single_stamp(right):
            return left, right

    # 2. Pure-kanji words.
    if set(classes) == {"kanji"}:
        if len(chars) == 3:
            if chars[-1] in KANJI_SUFFIX_NOMINALIZERS:
                return "".join(chars[:-1]), chars[-1]
            if chars[0] in KANJI_PREFIX_MODIFIERS:
                return chars[0], "".join(chars[1:])
            return "".join(chars[:2]), "".join(chars[2:])
        if len(chars) == 4:
            return "".join(chars[:2]), "".join(chars[2:])

    # 3. Pure katakana ≥4.
    if set(classes) == {"kata"} and len(chars) >= 4:
        for split_at in (3, 2):
            left = "".join(chars[:split_at])
            right = "".join(chars[split_at:])
            if fits_single_stamp(left) and fits_single_stamp(right):
                return left, right

    return None


def bgr_rotate(hex_str: str) -> str:
    if not _HEX6_RE.match(hex_str):
        raise ValueError(f"bad hex: {hex_str}")
    return hex_str[4:6] + hex_str[0:2] + hex_str[2:4]


def seeded_random(seed: str, term: str, axis: str) -> random.Random:
    raw = hashlib.sha256(f"{seed}:{term}:{axis}".encode("utf-8")).hexdigest()
    return random.Random(int(raw, 16) % (1 << 32))


def shuffled_pools(term: str, *, seed: str) -> dict[str, list[str]]:
    fonts = list(CANONICAL_FONTS)
    animations = list(POOLED_ANIMATIONS)
    colors = list(TAILWIND_PALETTE)
    seeded_random(seed, term, "font").shuffle(fonts)
    seeded_random(seed, term, "anim").shuffle(animations)
    seeded_random(seed, term, "color").shuffle(colors)
    return {"fonts": fonts, "animations": animations, "colors": colors}


def flavor_at(pools: dict[str, list[str]], index: int) -> dict[str, str]:
    fonts, animations, colors = pools["fonts"], pools["animations"], pools["colors"]
    font = fonts[index % len(fonts)]
    animation = animations[index % len(animations)]
    color = colors[index % len(colors)]
    flavor: dict[str, str] = {
        "font": font,
        "color": color,
        "animation": animation,
    }
    if animation in COLOR_SHIFTING_ANIMATIONS:
        flavor["outline_width"] = "0"
    else:
        flavor["outline"] = bgr_rotate(color)
    if animation in ROTATIONAL_ANIMATIONS:
        flavor["speed"] = "slow"
    return flavor


def generate_variants(term: str, *, seed: str, count: int) -> list[dict]:
    pools = shuffled_pools(term, seed=seed)
    return [flavor_at(pools, i) for i in range(count)]


def generate_compound_variants(term: str, chunks: tuple[str, str], *, seed: str, count: int) -> list[dict]:
    pools = shuffled_pools(term, seed=seed)
    out = []
    for i in range(count):
        flavor = flavor_at(pools, i)
        out.append({"chunks": [{**flavor, "text": c} for c in chunks]})
    return out


def yaml_safe_key(term: str) -> str:
    return f'"{term}"' if _DIGIT_KEY_RE.match(term) else term


def render_variant(variant: dict, indent: str) -> str:
    return "\n".join(Flavor.from_dict(variant).to_yaml_lines(indent=indent))


def render_compound_variant(variant: dict, indent: str) -> str:
    lines = [f"{indent}- chunks:"]
    for chunk in variant["chunks"]:
        lines.append(f"{indent}    - text: {chunk['text']}")
        lines.append(f"{indent}      font: {chunk['font']}")
        lines.append(f'{indent}      color: "{chunk["color"]}"')
        if chunk.get("outline"):
            lines.append(f'{indent}      outline: "{chunk["outline"]}"')
        if chunk.get("outline_width"):
            lines.append(f'{indent}      outline_width: "{chunk["outline_width"]}"')
        lines.append(f"{indent}      animation: {chunk['animation']}")
        if chunk.get("speed"):
            lines.append(f"{indent}      speed: {chunk['speed']}")
    return "\n".join(lines)


def _parse_terms(source: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in source.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # First whitespace-delimited token is the term.
        term = line.split()[0] if line.split() else ""
        if term and term not in seen:
            seen.add(term)
            out.append(term)
    return out


def render_term_block(term: str, *, seed: str, variants: int) -> Optional[str]:
    """Render the YAML block for one term, or None if it must be skipped.

    Skipped terms log a notice via stderr from the caller; this function
    returns None to signal that.
    """
    if fits_single_stamp(term):
        out = [f"  {yaml_safe_key(term)}:"]
        for variant in generate_variants(term, seed=seed, count=variants):
            out.append(render_variant(variant, "    "))
        return "\n".join(out)
    split = split_term(term)
    if split:
        out = [f"  {yaml_safe_key(term)}:"]
        for variant in generate_compound_variants(term, split, seed=seed, count=variants):
            out.append(render_compound_variant(variant, "    "))
        return "\n".join(out)
    return None


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate prestamp catalog variants for a list of terms.",
        usage="generate_catalog.py [--seed SEED] [--variants N] [--input FILE] < terms.txt",
    )
    parser.add_argument("--seed", default="0", help="Seed for deterministic variant selection")
    parser.add_argument("--variants", type=int, default=3, help="Variants per term (default 3)")
    parser.add_argument("--input", default=None, help="Read terms from FILE instead of stdin")
    args = parser.parse_args(argv)

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            source = f.read()
    else:
        source = sys.stdin.read()

    terms = _parse_terms(source)
    for term in terms:
        block = render_term_block(term, seed=args.seed, variants=args.variants)
        if block is None:
            counts = char_classes(term)
            print(
                f"skip: {term} — no valid split "
                f"(kanji={counts['kanji']} kata={counts['kata']} "
                f"ascii={counts['ascii']} hira={counts['hira']})",
                file=sys.stderr,
            )
            continue
        # Match Ruby: a blank line precedes each term block.
        print()
        print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
