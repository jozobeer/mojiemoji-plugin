"""Tests for skills/.../scripts/coverage.py — measurement + warn / block.

Counts Japanese characters vs decorated stamps, blocks when density is
below the per-surface threshold, and ignores bare URLs (only `<img>`
wrappers count). Also pins the issue-#78 regression where `?` inside
stamp URL query strings used to fragment sentence_hit_rate.

`sitecustomize` import-order test (coverage package vs the in-repo
script) lives here because it's an instrumentation concern that
piggybacks on the same script path.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import CATALOG_DIR, COVERAGE, REPO_ROOT, run_py


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


def test_no_warning_on_catalog_hit_unicode_emoji(tmp_path: Path) -> None:
    # prestamp.py now auto-substitutes catalog emoji during the emoji
    # pass (#89). So a Unicode emoji surviving into the coverage check
    # is intentional — either catalog-miss or inside a safe-zone — and
    # the old "uses Unicode X but mojiemoji variant exists in catalog"
    # warning is obsolete.
    import yaml as _yaml
    catalog_path = CATALOG_DIR / "emoji-catalog.yml"
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

    assert "mojiemoji variant exists in catalog" not in proc.stderr


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


def test_coverage_ignores_bare_urls_outside_img() -> None:
    # Bare URL inside a markdown link should NOT count as a rendered
    # stamp — only `<img src="…">` wrappers do.
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
    assert "stamps=1" in proc.stdout


def test_sentence_hit_rate_not_fragmented_by_stamp_url_query(tmp_path: Path) -> None:
    # Regression for issue #78: `?` in mojiemoji `<img>` URL query
    # strings used to be treated as a sentence separator, fragmenting
    # the sentence count AND breaking per-sentence stamp detection.
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
    # AC for issue #78: adding stamps must never DECREASE
    # sentence_hit_rate. Before the fix, more stamps meant more `?` in
    # URLs, fragmenting more sentences and tanking the rate.
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
