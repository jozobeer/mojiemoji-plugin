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
    proc = run_ruby(PRESTAMP, "修正版を修正しました。", "--seed", "1")

    assert proc.returncode == 0
    assert proc.stdout.count("mojiemoji.jozo.beer/emoji/") == 2
    assert "alt=\"修正版\"" in proc.stdout
    assert "alt=\"修正\"" in proc.stdout


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


def test_generate_catalog_skips_terms_exceeding_length_rule() -> None:
    proc = run_ruby(GENERATE, "誤検知\n完成\n", "--seed", "1")

    assert proc.returncode == 0
    assert "完成:" in proc.stdout
    assert "誤検知" not in proc.stdout
    assert "誤検知" in proc.stderr


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


def test_coverage_detects_paragraph_bias() -> None:
    body = """<img src="https://mojiemoji.jozo.beer/emoji/%E7%A2%BA%E8%AA%8D?font=gothic-bold&color=60a5fa&animation=tate_scroll&background=transparent&outline=darker&outline_width=2" alt="確認"> 段落1

段落2は未装飾です。

段落3も未装飾です。

段落4も未装飾です。
"""
    proc = run_ruby(COVERAGE, body, "--surface", "review-body", "--mode", "block")

    assert proc.returncode == 2
    assert "consecutive_unstamped_paragraphs" in proc.stderr
