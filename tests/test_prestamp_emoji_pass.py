"""Tests for prestamp.py's emoji-pass (Unicode emoji → mojiemoji `<img>`).

Catalog hits get replaced; uncatalogued / VS16 / inside `<summary>` /
in safe zones are preserved. Consecutive emoji runs are capped at two
to avoid visual crowding.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import CATALOG_DIR, PRESTAMP, run_py


def test_prestamp_replaces_catalog_emoji_with_img() -> None:
    # 🎉 (U+1F389 PARTY POPPER) is in emoji-catalog.yml. The emoji pass
    # should replace it with an <img> stamp.
    proc = run_py(PRESTAMP, "やった 🎉 完成！", "--seed", "3")

    assert proc.returncode == 0
    assert proc.stdout.count('alt="🎉"') == 1
    assert "mojiemoji.jozo.beer/emoji/%F0%9F%8E%89" in proc.stdout


def test_prestamp_leaves_uncatalogued_emoji_raw() -> None:
    # 🚀 (U+1F680 ROCKET) is the canonical "no upstream asset" emoji.
    # prestamp must not generate an <img> for it — the SKILL.md
    # fallback expects it to stay as plain Unicode.
    proc = run_py(PRESTAMP, "発射 🚀 する", "--seed", "4")

    assert proc.returncode == 0
    assert "🚀" in proc.stdout
    assert "mojiemoji.jozo.beer/emoji/%F0%9F%9A%80" not in proc.stdout


def test_prestamp_emoji_skips_safe_zones() -> None:
    body = (
        "プレーン本文に 🎉 を入れる。\n\n"
        "`code 🎉 in inline code` は触らない。\n\n"
        "```\nfenced 🎉 block も触らない\n```\n\n"
        "[リンク](https://example.com/🎉/path) URL 内も触らない。\n\n"
        '<img src="https://mojiemoji.jozo.beer/emoji/🎉" alt="🎉"> 既存 img も触らない。\n'
    )
    proc = run_py(PRESTAMP, body, "--seed", "5")

    assert proc.returncode == 0
    # Only the prose 🎉 gets stamped — exactly one new <img> with alt=🎉.
    new_emoji_stamps = re.findall(
        r'<img src="https://mojiemoji\.jozo\.beer/emoji/%F0%9F%8E%89[^"]*" alt="🎉"',
        proc.stdout,
    )
    assert len(new_emoji_stamps) == 1
    assert "`code 🎉 in inline code`" in proc.stdout
    assert "fenced 🎉 block も触らない" in proc.stdout
    assert "https://example.com/🎉/path" in proc.stdout
    assert '<img src="https://mojiemoji.jozo.beer/emoji/🎉" alt="🎉">' in proc.stdout


def test_prestamp_caps_consecutive_emoji_runs_at_two() -> None:
    # ✅❌👀 are all in the catalog. First two get stamped; third stays
    # raw to avoid visual crowding. Whitespace breaks the run.
    proc = run_py(PRESTAMP, "三連続 ✅❌👀 と 空白付き ✅ ❌ 👀", "--seed", "6")

    assert proc.returncode == 0
    stamps = re.findall(r'alt="([^"]+)"', proc.stdout)
    # Run 1 ("✅❌👀"): ✅+❌ stamped, 👀 raw.
    # Run 2 ("✅ ❌ 👀"): all 3 stamped.
    assert stamps.count("✅") == 2
    assert stamps.count("❌") == 2
    assert stamps.count("👀") == 1


def test_prestamp_strips_vs16_when_matching_emoji_catalog() -> None:
    # `⚠️` is U+26A0 U+FE0F. emoji-catalog stores the base codepoint
    # `⚠` only. prestamp strips VS16 before lookup.
    body = "注意 ⚠️ してください。"
    proc = run_py(PRESTAMP, body, "--seed", "7")

    assert proc.returncode == 0
    assert 'alt="⚠"' in proc.stdout
    # VS16 must not appear in the output.
    assert "⚠️" not in proc.stdout


def test_prestamp_preserves_vs16_on_uncatalogued_emoji() -> None:
    # ❤️ etc. are not currently in emoji-catalog.yml (verified at test
    # time so it auto-skips if the catalog grows). Their VS16 must
    # round-trip — stripping it would silently change emoji-presentation
    # to text-presentation. Regression for codex P1 / Copilot on #90.
    import yaml as _yaml
    catalog_path = CATALOG_DIR / "emoji-catalog.yml"
    with open(catalog_path, encoding="utf-8") as f:
        catalog = (_yaml.safe_load(f) or {}).get("emojis") or {}
    candidates = ["❤", "☀", "🏗", "🛡", "⚙"]
    miss = next((c for c in candidates if c not in catalog), None)
    if miss is None:
        pytest.skip("no uncatalogued VS16 emoji available — catalog grew")

    body = f"{miss}️ は装飾外。"
    proc = run_py(PRESTAMP, body, "--seed", "11")

    assert proc.returncode == 0
    # The exact VS16 sequence must survive untouched.
    assert f"{miss}️" in proc.stdout
    assert f'alt="{miss}"' not in proc.stdout


def test_prestamp_skips_emoji_inside_summary() -> None:
    # codex P2: the emoji pass used to bypass <summary> entirely,
    # producing a stamped emoji inside a summary heading. Pin
    # symmetry with the text pass — both must leave summary alone.
    body = "<details>\n<summary>祝賀 🎉 メモ</summary>\n本文に 🎊 も出る。\n</details>\n"
    proc = run_py(PRESTAMP, body, "--seed", "12")

    assert proc.returncode == 0
    assert "<summary>祝賀 🎉 メモ</summary>" in proc.stdout
    # Body 🎊 outside the summary still gets stamped.
    assert 'alt="🎊"' in proc.stdout
