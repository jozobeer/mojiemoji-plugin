"""Tests for compound-variant generation + rendering (issue #42).

`generate_catalog.py`'s split_term heuristic decomposes 3+ kanji /
3+ katakana strings into chunks that satisfy the single-stamp size
budget. Compound variants share font / color / animation across
chunks so the result reads as one cohesive word. prestamp.py
renders adjacent `<img>` tags with no separator.
"""

from __future__ import annotations

import re

from conftest import GENERATE, PRESTAMP, run_py


def _gen_term_yaml(term: str, seed: str = "42", variants: int = 1) -> str:
    """Run generate-catalog on a single term and return its yaml block."""
    proc = run_py(GENERATE, term + "\n", "--seed", seed, "--variants", str(variants))
    assert proc.returncode == 0
    return proc.stdout


def test_split_term_prefix_modifier_unsorted_3kanji() -> None:
    # 不一致 has prefix 不 (modifier) and no suffix nominalizer; split as
    # `不 + 一致`.
    out = _gen_term_yaml("不一致")

    assert "不一致:" in out
    assert "text: 不\n" in out
    assert "text: 一致\n" in out


def test_split_term_suffix_nominalizer_wins_over_prefix() -> None:
    # 初期化 has BOTH prefix 初 (modifier) AND suffix 化 (nominalizer).
    # Suffix wins per the heuristic: `初期 + 化`, not `初 + 期化`.
    out = _gen_term_yaml("初期化")

    assert "初期化:" in out
    assert "text: 初期\n" in out
    assert "text: 化\n" in out


def test_split_term_4kanji_balanced_split() -> None:
    # 4-kanji compound with no prefix/suffix → 2+2 fallback.
    out = _gen_term_yaml("緊急対応")

    assert "緊急対応:" in out
    assert "text: 緊急\n" in out
    assert "text: 対応\n" in out


def test_split_term_katakana_3plus_remainder() -> None:
    # 5-katakana word: prefer 3+remainder split.
    out = _gen_term_yaml("クラッシュ")

    assert "クラッシュ:" in out
    assert "text: クラッ\n" in out
    assert "text: シュ\n" in out


def test_split_term_character_class_boundary() -> None:
    # 修正お願い (kanji 3 + hira 2 = 5 chars). kanji > 2 forces split;
    # the kanji↔hira boundary at index 2 yields `修正` + `お願い`.
    out = _gen_term_yaml("修正お願い")

    assert "修正お願い:" in out
    assert "text: 修正\n" in out
    assert "text: お願い\n" in out


def test_compound_variant_chunks_share_flavor() -> None:
    # Both chunks in a single variant must use the same font/color/animation
    # so the split reads as one cohesive word per SKILL.md guidance.
    out = _gen_term_yaml("緊急対応", variants=1)

    fonts = re.findall(r"font: (\w[\w-]*)", out)
    colors = re.findall(r'color: "([0-9a-f]{6})"', out)
    anims = re.findall(r"animation: (\w+)", out)

    assert len(fonts) == 2
    assert fonts[0] == fonts[1], f"fonts differ across chunks: {fonts}"
    assert len(colors) == 2
    assert colors[0] == colors[1], f"colors differ across chunks: {colors}"
    assert len(anims) == 2
    assert anims[0] == anims[1], f"animations differ across chunks: {anims}"


def test_prestamp_renders_compound_variant_as_adjacent_imgs(tmp_path) -> None:
    # End-to-end: a compound variant in YAML renders as N adjacent <img>
    # tags with no separator, each chunk's text URL-encoded individually.
    catalog = tmp_path / "catalog.yml"
    catalog.write_text(
        "defaults:\n"
        "  background: transparent\n"
        '  outline_width: "2"\n'
        "terms:\n"
        "  未着手:\n"
        "    - chunks:\n"
        "        - text: 未\n"
        "          font: gothic-bold\n"
        '          color: "ef4444"\n'
        '          outline: "4444ef"\n'
        "          animation: gatagata\n"
        "        - text: 着手\n"
        "          font: gothic-bold\n"
        '          color: "ef4444"\n'
        '          outline: "4444ef"\n'
        "          animation: gatagata\n",
        encoding="utf-8",
    )

    proc = run_py(PRESTAMP, "未着手の対応", "--seed", "0", "--catalog", str(catalog))

    assert proc.returncode == 0
    # Two adjacent <img> tags for the two chunks, with proper URL encoding.
    assert "%E6%9C%AA" in proc.stdout  # 未
    assert "%E7%9D%80%E6%89%8B" in proc.stdout  # 着手
    assert proc.stdout.count('<img src="') == 2
    # The two imgs must be back-to-back (no separator between them).
    assert "><img src=" in proc.stdout


def test_compound_variant_uses_rotational_speed_slow() -> None:
    # Rotational animations (kaiten / kage_kaiten) must include speed: slow
    # in compound variants too (chunks share flavor, so the rotational
    # signal propagates to both chunks).
    out = _gen_term_yaml("緊急対応", variants=64)

    rotational_variants = re.findall(
        r"chunks:\s+- text: [^\n]+\n\s+font: [^\n]+\n\s+color: [^\n]+\n(?:\s+outline: [^\n]+\n)?(?:\s+outline_width: [^\n]+\n)?\s+animation: (kaiten|kage_kaiten)\n\s+speed: (\w+)",
        out,
    )
    for animation, speed in rotational_variants:
        assert speed == "slow", f"{animation} variant must have speed: slow, got {speed}"
