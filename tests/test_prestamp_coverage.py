"""Tests for prestamp.rb and coverage.rb scripts."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PRESTAMP = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "prestamp.rb"
COVERAGE = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "coverage.rb"
GENERATE = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "generate-catalog.rb"


def run_ruby(script: Path, text: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ruby", str(script), *args],
        input=text,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_prestamp_replaces_catalog_hits_and_respects_safe_zones() -> None:
    body = """修正をお願いします。

`修正` はコードです。

<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=gothic-bold&color=3b82f6&animation=bane&background=transparent&outline=darker&outline_width=2" alt="修正">

![修正](https://img.shields.io/badge/修正-ok)

[リンク](https://example.com/修正)

```mermaid
graph TD
A[修正] --> B[完了]
```

```ruby
puts '修正'
```
"""
    proc = run_ruby(PRESTAMP, body, "--seed", "5")

    assert proc.returncode == 0
    assert proc.stdout.count('align="absmiddle"') == 1
    assert "alt=\"修正\"" in proc.stdout
    assert '<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=gothic-bold&color=3b82f6&animation=bane&background=transparent&outline=darker&outline_width=2" alt="修正">' in proc.stdout
    assert "`修正`" in proc.stdout
    assert "https://img.shields.io/badge/修正-ok" in proc.stdout
    assert "[リンク](https://example.com/修正)" in proc.stdout
    assert "A[修正] --> B[完了]" in proc.stdout
    assert "puts '修正'" in proc.stdout


def test_prestamp_uses_longest_match() -> None:
    # 修正版 is not its own catalog entry; the longest match is 修正, leaving
    # 版 as plain text. Both 修正 occurrences in the input get stamped.
    proc = run_ruby(PRESTAMP, "修正版を修正しました。", "--seed", "1")

    assert proc.returncode == 0
    assert proc.stdout.count("mojiemoji.jozo.beer/emoji/") == 2
    assert proc.stdout.count('alt="修正"') == 2
    assert 'alt="修正版"' not in proc.stdout
    # 版 should be plain text immediately after the first stamp's </img> close.
    assert "align=\"absmiddle\">版を" in proc.stdout


def test_prestamp_spreads_variants_for_repeated_keyword() -> None:
    proc = run_ruby(PRESTAMP, "確認 確認 確認 確認", "--seed", "11")

    assert proc.returncode == 0
    srcs = re.findall(r'src="([^"]+)"', proc.stdout)
    assert len(srcs) == 4

    animations = set()
    for src in srcs:
        match = re.search(r"(?:[?&]animation=)([^&]+)", src.replace("&amp;", "&"))
        assert match is not None
        animations.add(match.group(1))
    assert len(animations) >= 2


def test_prestamp_skips_details_summary_but_stamps_details_body() -> None:
    body = "<details>\n<summary>修正方針</summary>\n本文は修正対象です。\n</details>\n"
    proc = run_ruby(PRESTAMP, body, "--seed", "2")

    assert proc.returncode == 0
    assert "<summary>修正方針</summary>" in proc.stdout
    assert 'align="absmiddle"' in proc.stdout


def test_coverage_counts_japanese_characters_and_warn_mode() -> None:
    body = (
        '<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=gothic-bold&color=3b82f6&animation=bane&background=transparent&outline=darker&outline_width=2" alt="修正">'
        "\nあア漢\n"
    )
    proc = run_ruby(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    assert proc.returncode == 0
    assert "japanese_chars=5" in proc.stdout


def test_coverage_blocks_when_below_threshold() -> None:
    proc = run_ruby(COVERAGE, "日本語のみの本文です。", "--surface", "issue-body", "--mode", "block")

    assert proc.returncode == 2
    assert "coverage warning:" in proc.stderr


def test_generate_catalog_emits_diverse_variants_per_term() -> None:
    proc = run_ruby(GENERATE, "完成\n", "--seed", "42", "--variants", "3")

    assert proc.returncode == 0
    fonts = re.findall(r"- font: (\S+)", proc.stdout)
    animations = re.findall(r"animation: (\S+)", proc.stdout)
    colors = re.findall(r'color: "([^"]+)"', proc.stdout)
    assert len(fonts) == 3
    assert len(set(fonts)) == 3
    assert len(set(animations)) == 3
    assert len(set(colors)) == 3


def test_generate_catalog_outline_is_bgr_rotation_of_color() -> None:
    proc = run_ruby(GENERATE, "完成\n", "--seed", "42", "--variants", "3")

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
    proc = run_ruby(GENERATE, "誤検知\n完成\n", "--seed", "1")

    assert proc.returncode == 0
    assert "完成:" in proc.stdout
    assert "誤検知:" in proc.stdout
    assert "chunks:" in proc.stdout
    assert "text: 誤" in proc.stdout
    assert "text: 検知" in proc.stdout


def test_generate_catalog_skips_unsplittable_terms() -> None:
    # 4 hiragana is a single-stamp case (<=4); use something that has no
    # valid 2-stamp decomposition: a long single-script run.
    proc = run_ruby(GENERATE, "完成\nあいうえおか\n", "--seed", "1")

    assert proc.returncode == 0
    assert "完成:" in proc.stdout
    assert "あいうえおか" not in proc.stdout
    assert "あいうえおか" in proc.stderr


def test_generate_catalog_handles_color_shifting_and_rotational_animations() -> None:
    # Sweep many terms / seeds to exercise the kira/disco/psycho and kaiten paths.
    proc = run_ruby(
        GENERATE,
        "\n".join(f"語{i:02d}" for i in range(50)) + "\n",
        "--seed",
        "7",
    )

    assert proc.returncode == 0
    # Whenever a color-shifting animation appears, the variant must suppress
    # the halo via outline_width: "0" and must NOT carry an outline color.
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


def test_prestamp_handles_indented_and_tilde_fences() -> None:
    body = (
        "   ```ruby\n"
        "puts '修正'\n"
        "   ```\n"
        "\n"
        "~~~text\n"
        "修正\n"
        "~~~\n"
        "\n"
        "修正\n"
    )
    proc = run_ruby(PRESTAMP, body, "--seed", "3")

    assert proc.returncode == 0
    # Both fenced blocks preserved verbatim — neither 修正 inside fences stamped.
    assert "puts '修正'" in proc.stdout
    assert "~~~text\n修正\n~~~" in proc.stdout
    # The bare 修正 outside fences is the only stamped occurrence.
    assert proc.stdout.count('align="absmiddle"') == 1


def test_prestamp_handles_nested_fence_markers() -> None:
    # A shorter ``` inside a ```` block must not close the outer fence.
    body = (
        "````md\n"
        "```ruby\n"
        "修正\n"
        "```\n"
        "````\n"
        "\n"
        "修正\n"
    )
    proc = run_ruby(PRESTAMP, body, "--seed", "4")

    assert proc.returncode == 0
    # 修正 inside the nested fence stays plain; only the outer 修正 stamps.
    assert "```ruby\n修正\n```" in proc.stdout
    assert proc.stdout.count('align="absmiddle"') == 1


def test_coverage_ignores_bare_urls_outside_img() -> None:
    # Bare URL inside a markdown link should NOT count as a rendered stamp —
    # only `<img src="…">` wrappers do.
    body = (
        "[ドキュメント](https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3)を参照。\n"
        "確認 修正 完了 重要 緊急\n"
    )
    proc = run_ruby(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    assert proc.returncode == 0
    assert "stamps=0" in proc.stdout


def test_coverage_counts_img_wrapped_stamps_only() -> None:
    body = (
        '<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=gothic-bold&color=3b82f6&animation=bane&background=transparent&outline=darker&outline_width=2" alt="修正"> '
        "そして [リンク](https://mojiemoji.jozo.beer/emoji/%E9%87%8D%E8%A6%81) も。"
    )
    proc = run_ruby(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    assert proc.returncode == 0
    # Only the <img> wrapped occurrence counts.
    assert "stamps=1" in proc.stdout


def test_coverage_detects_paragraph_bias() -> None:
    body = """<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=gothic-bold&color=60a5fa&animation=tate_scroll&background=transparent&outline=darker&outline_width=2" alt="確認"> 段落1

段落2は未装飾です。

段落3も未装飾です。

段落4も未装飾です。
"""
    proc = run_ruby(COVERAGE, body, "--surface", "review-body", "--mode", "block")

    assert proc.returncode == 2
    assert "consecutive_unstamped_paragraphs" in proc.stderr


# ---------------------------------------------------------------------------
# split_term + compound-variant tests (issue #42)
# ---------------------------------------------------------------------------


def _gen_term_yaml(term: str, seed: str = "42", variants: int = 1) -> str:
    """Run generate-catalog on a single term and return only its yaml block."""
    proc = run_ruby(GENERATE, term + "\n", "--seed", seed, "--variants", str(variants))
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
    # the kanji↔hira boundary at index 2 yields `修正` (2 kanji) +
    # `お願い` (hira+kanji+hira = 3 chars), both single-stampable.
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

    # Swap the catalog path in via a copy of prestamp.rb won't work cleanly;
    # instead run prestamp.rb with a temp YAML by symlinking into place via
    # a wrapper that overrides CATALOG_PATH. Simpler: monkey-patch via a
    # heredoc wrapper.
    wrapper = tmp_path / "prestamp-with-catalog.rb"
    wrapper.write_text(
        f'CATALOG_PATH_OVERRIDE = "{catalog}"\n'
        'orig_load = YAML.method(:safe_load_file)\n'
        f'load "{PRESTAMP}"\n',
        encoding="utf-8",
    )

    # Direct approach: copy prestamp.rb and substitute CATALOG_PATH.
    import shutil

    src = PRESTAMP
    dst = tmp_path / "prestamp.rb"
    shutil.copy(src, dst)
    text = dst.read_text(encoding="utf-8")
    text = text.replace(
        'CATALOG_PATH = File.expand_path("../data/prestamp-catalog.yml", __dir__)',
        f'CATALOG_PATH = "{catalog}"',
    )
    dst.write_text(text, encoding="utf-8")

    proc = run_ruby(dst, "未着手の対応", "--seed", "0")

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

    # Find variants whose animation is rotational
    rotational_variants = re.findall(
        r"chunks:\s+- text: [^\n]+\n\s+font: [^\n]+\n\s+color: [^\n]+\n(?:\s+outline: [^\n]+\n)?(?:\s+outline_width: [^\n]+\n)?\s+animation: (kaiten|kage_kaiten)\n\s+speed: (\w+)",
        out,
    )
    for animation, speed in rotational_variants:
        assert speed == "slow", f"{animation} variant must have speed: slow, got {speed}"
