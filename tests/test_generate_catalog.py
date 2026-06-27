"""Tests for skills/.../scripts/generate_catalog.py.

Covers variant diversity, color↔outline BGR-rotation rule, kanji /
katakana split delegation to split_term, animation-specific
suppressions (kira/disco/psycho outline; kaiten/kage_kaiten speed),
and the digit-key quoting required for YAML→Regexp.union safety.
"""

from __future__ import annotations

import importlib.util
import re
import sys

import pytest
import yaml

from conftest import GENERATE, REPO_ROOT, run_py


@pytest.fixture(scope="module", autouse=True)
def _add_scripts_to_path() -> None:
    scripts_dir = str(GENERATE.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


def _load_generate_catalog_module():
    spec = importlib.util.spec_from_file_location("generate_catalog", GENERATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_catalog_emits_diverse_variants_per_term() -> None:
    proc = run_py(GENERATE, "完成\n", "--seed", "42", "--variants", "3")

    assert proc.returncode == 0
    fonts = re.findall(r"- font: (\S+)", proc.stdout)
    animations = re.findall(r"animation: (\S+)", proc.stdout)
    colors = re.findall(r'color: "([^"]+)"', proc.stdout)
    assert len(fonts) == 3
    assert len(set(fonts)) == 3
    assert len(set(animations)) == 3
    assert len(set(colors)) == 3


def test_generate_catalog_outline_is_bgr_rotation_of_color() -> None:
    proc = run_py(GENERATE, "完成\n", "--seed", "42", "--variants", "3")

    assert proc.returncode == 0
    pairs = re.findall(r'color: "([0-9a-f]{6})"\s+outline: "([0-9a-f]{6})"', proc.stdout)
    assert pairs, f"no color+outline pairs found in:\n{proc.stdout}"
    for color, outline in pairs:
        expected = color[4:6] + color[0:2] + color[2:4]
        assert outline == expected, f"{color} -> outline {outline} (expected {expected})"


def test_generate_catalog_splits_3plus_kanji_via_compound_variant() -> None:
    # 誤検知 is 3 kanji, exceeds single-stamp rule (kanji <= 2), so
    # split_term decomposes it via the prefix-modifier heuristic
    # (誤 + 検知) and emits a compound variant with adjacent chunks.
    proc = run_py(GENERATE, "誤検知\n完成\n", "--seed", "1")

    assert proc.returncode == 0
    assert "完成:" in proc.stdout
    assert "誤検知:" in proc.stdout
    assert "chunks:" in proc.stdout
    assert "text: 誤" in proc.stdout
    assert "text: 検知" in proc.stdout


def test_generate_catalog_splits_long_ascii_mixed_japanese_terms() -> None:
    proc = run_py(GENERATE, "GitHub対応\n", "--seed", "1", "--variants", "1")

    assert proc.returncode == 0
    assert "GitHub対応:" in proc.stdout
    assert "chunks:" in proc.stdout
    assert "text: GitHub" in proc.stdout
    assert "text: 対応" in proc.stdout


def test_generate_catalog_skips_unsplittable_terms() -> None:
    # 4 hiragana is single-stamp OK; use a long single-script run with
    # no valid 2-stamp decomposition.
    proc = run_py(GENERATE, "完成\nあいうえおか\n", "--seed", "1")

    assert proc.returncode == 0
    assert "完成:" in proc.stdout
    assert "あいうえおか" not in proc.stdout
    assert "あいうえおか" in proc.stderr


def test_generate_catalog_handles_color_shifting_and_rotational_animations() -> None:
    # Sweep many terms / seeds to exercise the kira/disco/psycho and
    # kaiten paths.
    proc = run_py(
        GENERATE,
        "\n".join(f"語{i:02d}" for i in range(50)) + "\n",
        "--seed",
        "7",
    )

    assert proc.returncode == 0
    # Color-shifting animation → suppress outline via outline_width: "0"
    # and drop the outline key entirely.
    for match in re.finditer(
        r"(?ms)^    - font:.*?(?=^    - font:|^  \S|\Z)", proc.stdout
    ):
        block = match.group(0)
        animation = re.search(r"animation: (\S+)", block).group(1)
        if animation in {"kira", "disco", "psycho"}:
            assert 'outline_width: "0"' in block, f"missing suppression in:\n{block}"
            assert "outline:" not in block, f"unexpected outline for {animation}:\n{block}"
        if animation in {"kaiten", "kage_kaiten"}:
            assert "speed: slow" in block, f"missing speed: slow for {animation}:\n{block}"


def test_generate_catalog_quotes_numeric_keys() -> None:
    # Bare `1:` parses as Integer in YAML, breaking prestamp.py's
    # Regexp.union over CATALOG.keys (expects String).
    proc = run_py(GENERATE, "1\n2\n", "--seed", "42", "--variants", "1")

    assert proc.returncode == 0
    assert '"1":' in proc.stdout
    assert '"2":' in proc.stdout
    # Non-numeric keys remain unquoted (regression guard).
    proc2 = run_py(GENERATE, "完成\n", "--seed", "42", "--variants", "1")
    assert proc2.returncode == 0
    assert "完成:" in proc2.stdout
    assert '"完成":' not in proc2.stdout


def test_catalog_loads_with_string_keys_for_digits() -> None:
    # End-to-end: after regeneration, the live catalog's digit entries
    # must be loadable as String keys by prestamp.py (no Integer keys
    # silently breaking lookups).
    catalog_path = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "prestamp-catalog.yml"
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    int_keys = [k for k in data["terms"].keys() if isinstance(k, int)]
    assert int_keys == [], f"integer keys leaked into catalog: {int_keys}"


def test_live_prestamp_catalog_has_no_duplicate_term_keys() -> None:
    catalog_path = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "prestamp-catalog.yml"
    keys = re.findall(r"(?m)^  ([^\s:\n][^:\n]*):$", catalog_path.read_text(encoding="utf-8"))
    duplicates = sorted({key for key in keys if keys.count(key) > 1})

    assert duplicates == []


def test_advertised_english_terms_exist_in_runtime_catalog() -> None:
    catalog_path = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "prestamp-catalog.yml"
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))

    for term in ["PUSH", "PULL", "FIX", "OPEN"]:
        assert term in data["terms"]


def test_generate_catalog_han_range_excludes_hangul_yi_pua() -> None:
    generate_catalog = _load_generate_catalog_module()

    assert generate_catalog.char_classes("語日本")["kanji"] == 3
    assert generate_catalog.char_classes("한국어")["kanji"] == 0
    assert generate_catalog.char_classes("ꀀ")["kanji"] == 0
    assert generate_catalog.char_classes("\ue000")["kanji"] == 0


def test_generate_catalog_palette_excludes_forbidden_replacement_keys() -> None:
    generate_catalog = _load_generate_catalog_module()
    from lib.forbidden_colors import FORBIDDEN_COLOR_REPLACEMENTS

    forbidden = set(FORBIDDEN_COLOR_REPLACEMENTS)
    assert not (set(generate_catalog.TAILWIND_PALETTE) & forbidden)
