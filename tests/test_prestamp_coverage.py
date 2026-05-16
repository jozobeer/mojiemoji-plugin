"""Tests for prestamp.py and coverage.py scripts."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
PRESTAMP = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "prestamp.py"
COVERAGE = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "coverage.py"
GENERATE = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "generate_catalog.py"


def run_py(script: Path, text: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
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
    proc = run_py(PRESTAMP, body, "--seed", "5")

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
    proc = run_py(PRESTAMP, "修正版を修正しました。", "--seed", "1")

    assert proc.returncode == 0
    assert proc.stdout.count("mojiemoji.jozo.beer/emoji/") == 2
    assert proc.stdout.count('alt="修正"') == 2
    assert 'alt="修正版"' not in proc.stdout
    # 版 should be plain text immediately after the first stamp's </img> close.
    assert "align=\"absmiddle\">版を" in proc.stdout


def test_prestamp_spreads_variants_for_repeated_keyword() -> None:
    proc = run_py(PRESTAMP, "確認 確認 確認 確認", "--seed", "11")

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
    proc = run_py(PRESTAMP, body, "--seed", "2")

    assert proc.returncode == 0
    assert "<summary>修正方針</summary>" in proc.stdout
    assert 'align="absmiddle"' in proc.stdout


def test_coverage_counts_japanese_characters_and_warn_mode() -> None:
    body = (
        '<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=gothic-bold&color=3b82f6&animation=bane&background=transparent&outline=darker&outline_width=2" alt="修正">'
        "\nあア漢\n"
    )
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    assert proc.returncode == 0
    assert "japanese_chars=5" in proc.stdout


def test_coverage_blocks_when_below_threshold() -> None:
    proc = run_py(COVERAGE, "日本語のみの本文です。", "--surface", "issue-body", "--mode", "block")

    assert proc.returncode == 2
    assert "coverage warning:" in proc.stderr


def test_trailing_decoration_warns_on_undecorated_heading() -> None:
    body = "# 概要\n\n本文だけです。\n"
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    assert "trailing-slot" in proc.stderr
    assert "heading lacks trailing decoration" in proc.stderr


def test_trailing_decoration_skips_english_heading() -> None:
    body = "# TL;DR\n\n本文だけです。\n"
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    # English heading should NOT trigger trailing-decoration warning.
    assert "heading lacks trailing decoration" not in proc.stderr


def test_trailing_decoration_warnings_excluded_from_failures() -> None:
    # Unit-call check_failures() directly to verify trailing-slot
    # violations are routed to the warning channel (heading_warnings /
    # paragraph_warnings) and NOT included in the block-failing failures
    # list. This is the contract that issue #60 Option 1 specifies.
    import importlib.util

    spec = importlib.util.spec_from_file_location("coverage_script", COVERAGE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    metrics = {
        "stamp_count": 100,
        "japanese_char_count": 100,
        "density": 100.0,
        "sentence_hits": 10,
        "sentence_total": 10,
        "sentence_hit_rate": 1.0,
        "paragraph_hits": 5,
        "paragraph_total": 5,
        "paragraph_hit_rate": 1.0,
        "max_consecutive_unstamped": 0,
        "heading_warnings": ["line 1: heading lacks trailing decoration"],
        "paragraph_warnings": ["paragraph 1 lacks trailing decoration"],
    }
    threshold = mod.SURFACE_THRESHOLDS["issue-body"]
    failures = mod.check_failures(metrics, threshold)

    # Failures list must NOT contain any trailing-slot violations.
    assert failures == [], failures


def test_trailing_decoration_skips_fenced_code_block() -> None:
    body = (
        "本文があります。\n\n"
        "```python\n"
        "# これはコードブロック内の見出しコメント\n"
        "def foo(): pass\n"
        "```\n"
    )
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    # The `# これはコードブロック内の見出しコメント` inside ```python``` must
    # not be flagged as an undecorated heading.
    assert "heading lacks trailing decoration" not in proc.stderr


def test_trailing_decoration_skips_table_row() -> None:
    body = (
        "テーブルの前文があります全部書きます。\n\n"
        "| 項目 | 説明 |\n"
        "|---|---|\n"
        "| 名前です | 必須です |\n"
        "| 年齢です | 任意です |\n"
    )
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    # Table block (paragraph 2) is not a prose paragraph — must not be flagged.
    paragraph_warnings = [
        line for line in proc.stderr.splitlines()
        if "trailing-slot" in line and "paragraph 2" in line
    ]
    assert paragraph_warnings == [], paragraph_warnings


def test_trailing_decoration_skips_list() -> None:
    body = (
        "リストの前文があります。\n\n"
        "- 項目その一\n"
        "- 項目その二\n"
        "- 項目その三\n"
    )
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    # Bullet list is not a prose paragraph for trailing-deco purposes.
    paragraph_warnings = [
        line for line in proc.stderr.splitlines()
        if "paragraph" in line and "lacks trailing decoration" in line
    ]
    # The list block (paragraph 2) should not be flagged.
    assert all("paragraph 2" not in line for line in paragraph_warnings), paragraph_warnings


def test_trailing_decoration_warns_on_unicode_emoji_with_catalog_variant(tmp_path: Path) -> None:
    # Create a tiny emoji-catalog.yml in a temp location, then point at it
    # via a sibling script. Since coverage.py uses a fixed DEFAULT path, we
    # use the actual repo catalog. Pick a known catalog Unicode emoji.
    import yaml as _yaml
    catalog_path = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "emoji-catalog.yml"
    if not catalog_path.exists():
        pytest.skip("emoji-catalog.yml not found")
    with open(catalog_path, encoding="utf-8") as f:
        data = _yaml.safe_load(f) or {}
    emojis = list((data.get("emojis") or {}).keys())
    if not emojis:
        pytest.skip("emoji-catalog.yml has no entries")
    sample = emojis[0]

    body = f"# 概要 {sample}\n\n本文ここに{sample}。\n"
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    assert "mojiemoji variant exists in catalog" in proc.stderr


@pytest.mark.skipif(
    importlib.util.find_spec("coverage") is None,
    reason="coverage.py package not installed",
)
def test_sitecustomize_prefers_coverage_package_over_repo_script(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "tests")
    env["COVERAGE_PROCESS_START"] = str(REPO_ROOT / "pyproject.toml")
    env["COVERAGE_FILE"] = str(tmp_path / ".coverage")

    proc = subprocess.run(
        [sys.executable, "-c", "import coverage; print(coverage.__file__)"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(COVERAGE.parent),
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    assert str(COVERAGE) not in proc.stdout


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


def test_generate_catalog_skips_unsplittable_terms() -> None:
    # 4 hiragana is a single-stamp case (<=4); use something that has no
    # valid 2-stamp decomposition: a long single-script run.
    proc = run_py(GENERATE, "完成\nあいうえおか\n", "--seed", "1")

    assert proc.returncode == 0
    assert "完成:" in proc.stdout
    assert "あいうえおか" not in proc.stdout
    assert "あいうえおか" in proc.stderr


def test_generate_catalog_handles_color_shifting_and_rotational_animations() -> None:
    # Sweep many terms / seeds to exercise the kira/disco/psycho and kaiten paths.
    proc = run_py(
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
    proc = run_py(PRESTAMP, body, "--seed", "3")

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
    proc = run_py(PRESTAMP, body, "--seed", "4")

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
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    assert proc.returncode == 0
    assert "stamps=0" in proc.stdout


def test_coverage_counts_img_wrapped_stamps_only() -> None:
    body = (
        '<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=gothic-bold&color=3b82f6&animation=bane&background=transparent&outline=darker&outline_width=2" alt="修正"> '
        "そして [リンク](https://mojiemoji.jozo.beer/emoji/%E9%87%8D%E8%A6%81) も。"
    )
    proc = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")

    assert proc.returncode == 0
    # Only the <img> wrapped occurrence counts.
    assert "stamps=1" in proc.stdout


def test_sentence_hit_rate_not_fragmented_by_stamp_url_query(tmp_path: Path) -> None:
    # Regression for issue #78: `?` in mojiemoji `<img>` URL query strings
    # (e.g. `?font=...`) used to be treated as a sentence separator, which
    # both fragmented the sentence count AND broke per-sentence stamp
    # detection. A single stamped sentence must measure as 1 sentence with
    # full hit rate, regardless of how many `?` appear inside stamp URLs.
    import importlib.util

    spec = importlib.util.spec_from_file_location("coverage_script", COVERAGE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    stamp = (
        '<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3'
        '?font=gothic-bold&color=3b82f6&animation=bane'
        '&background=transparent&outline=darker&outline_width=2" alt="修正">'
    )
    body = f"本文に{stamp}が含まれます。"

    metrics = mod.measure(body)

    assert metrics["sentence_total"] == 1, metrics
    assert metrics["sentence_hits"] == 1, metrics
    assert metrics["sentence_hit_rate"] == 1.0, metrics


def test_sentence_hit_rate_monotonic_with_stamp_count(tmp_path: Path) -> None:
    # Acceptance criterion for issue #78: adding stamps must never DECREASE
    # sentence_hit_rate. Before the fix, more stamps meant more `?` in
    # URLs, fragmenting more sentences and tanking the rate — the opposite
    # of the 下処理 first principle.
    import importlib.util

    spec = importlib.util.spec_from_file_location("coverage_script", COVERAGE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    stamp = (
        '<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3'
        '?font=gothic-bold&color=3b82f6&animation=bane'
        '&background=transparent&outline=darker&outline_width=2" alt="修正">'
    )
    one_stamp = f"これは{stamp}を含む文です。"
    three_stamps = f"これは{stamp}{stamp}{stamp}を含む文です。"

    rate_one = mod.measure(one_stamp)["sentence_hit_rate"]
    rate_three = mod.measure(three_stamps)["sentence_hit_rate"]

    assert rate_three >= rate_one, (rate_one, rate_three)
    assert rate_three == 1.0, rate_three


def test_coverage_detects_paragraph_bias() -> None:
    body = """<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=gothic-bold&color=60a5fa&animation=tate_scroll&background=transparent&outline=darker&outline_width=2" alt="確認"> 段落1

段落2は未装飾です。

段落3も未装飾です。

段落4も未装飾です。
"""
    proc = run_py(COVERAGE, body, "--surface", "review-body", "--mode", "block")

    assert proc.returncode == 2
    assert "consecutive_unstamped_paragraphs" in proc.stderr


# ---------------------------------------------------------------------------
# split_term + compound-variant tests (issue #42)
# ---------------------------------------------------------------------------


def _gen_term_yaml(term: str, seed: str = "42", variants: int = 1) -> str:
    """Run generate-catalog on a single term and return only its yaml block."""
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

    # Point prestamp at the fixture catalog via the --catalog flag so we
    # can run it in isolation without touching the repo's real catalog.
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

    # Find variants whose animation is rotational
    rotational_variants = re.findall(
        r"chunks:\s+- text: [^\n]+\n\s+font: [^\n]+\n\s+color: [^\n]+\n(?:\s+outline: [^\n]+\n)?(?:\s+outline_width: [^\n]+\n)?\s+animation: (kaiten|kage_kaiten)\n\s+speed: (\w+)",
        out,
    )
    for animation, speed in rotational_variants:
        assert speed == "slow", f"{animation} variant must have speed: slow, got {speed}"


# ---------------------------------------------------------------------------
# Single-char catalog entries + boundary assertions (issue #52)
# ---------------------------------------------------------------------------


def _count_imgs(stdout: str) -> int:
    return stdout.count('align="absmiddle"')


def test_single_digit_does_not_stamp_inside_version_string() -> None:
    # `v1.2.3` — every digit is part of a version triple, all preceded
    # by ASCII letter or period, all followed by digit or period.
    proc = run_py(PRESTAMP, "v1.2.3", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_inside_unit_value() -> None:
    # `100ms` — digits are adjacent to other digits or ASCII letter.
    proc = run_py(PRESTAMP, "100ms", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_inside_hash_reference() -> None:
    # `#1234` — `1` preceded by `#` (not Japanese), `2`/`3`/`4` preceded
    # by digit. None pass the lookbehind/lookahead guards.
    proc = run_py(PRESTAMP, "#1234", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_with_only_whitespace_left_context() -> None:
    # `Step 1` — `1` preceded by space (with ASCII to the left of space).
    # The lookbehind requires Japanese char *immediately* before, so block.
    proc = run_py(PRESTAMP, "Step 1 として実装", "--seed", "1")

    assert proc.returncode == 0
    # 実装 stamps, but not `1`.
    assert _count_imgs(proc.stdout) == 1
    assert 'alt="実装"' in proc.stdout
    assert 'alt="1"' not in proc.stdout


def test_promise_all_does_not_stamp() -> None:
    # `Promise.all` has no catalog hits — verify nothing gets stamped
    # (regression guard against accidental ASCII catalog additions).
    proc = run_py(PRESTAMP, "Promise.all", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0


def test_single_digit_stamps_inside_japanese_flow() -> None:
    # `仕様変更1件` — `1` preceded by `更` (Han), followed by `件` (Han,
    # not in catalog). Both guards pass; `1` should stamp.
    proc = run_py(PRESTAMP, "仕様変更1件", "--seed", "1")

    assert proc.returncode == 0
    assert 'alt="1"' in proc.stdout
    # 仕様 and 変更 are 2-kanji multi entries, should also stamp.
    assert 'alt="仕様"' in proc.stdout
    assert 'alt="変更"' in proc.stdout


def test_single_kanji_blocked_when_preceded_by_han() -> None:
    # `先月` — `月` preceded by Han `先` (not in catalog). Block.
    proc = run_py(PRESTAMP, "先月", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0


def test_single_kanji_stamps_at_start_of_line() -> None:
    # `火曜の昼` — `火` at SOL (no preceding Han). The rule allows
    # Han to follow (so `火曜` still stamps the leading 火), since
    # the issue's intent is to surface the weekday glyph.
    proc = run_py(PRESTAMP, "火曜の昼", "--seed", "1")

    assert proc.returncode == 0
    assert 'alt="火"' in proc.stdout


def test_full_issue_acceptance_sentence() -> None:
    # The exact verification sentence from issue #52:
    #   "v1.2.3 で 100ms の修正を Step 1 として実装した。後で 火 にレビュー。"
    # Expectation: only 修正 / 実装 / 後 / 火 stamp.
    body = "v1.2.3 で 100ms の修正を Step 1 として実装した。後で 火 にレビュー。"
    proc = run_py(PRESTAMP, body, "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 4
    for term in ("修正", "実装", "後", "火"):
        assert f'alt="{term}"' in proc.stdout, f"expected stamp for {term}"
    # Negative — none of these substrings should appear as an alt.
    for plain in ('alt="1"', 'alt="2"', 'alt="3"', 'alt="0"'):
        assert plain not in proc.stdout, f"unexpected stamp: {plain}"


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
    import yaml

    catalog_path = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "prestamp-catalog.yml"
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    int_keys = [k for k in data["terms"].keys() if isinstance(k, int)]
    assert int_keys == [], f"integer keys leaked into catalog: {int_keys}"
