"""Behavioral tests for prestamp --intensity (normal / minimal) modes."""

from __future__ import annotations

import re

from conftest import PRESTAMP, run_py


def _img_count(text: str) -> int:
    return len(re.findall(r"<img\b", text))


def test_intensity_monotonic_img_counts() -> None:
    body = "実装と確認と修正を進めます。問題と対応とレビューを続けます。\n"
    a = run_py(PRESTAMP, body, "--intensity", "aggressive").stdout
    n = run_py(PRESTAMP, body, "--intensity", "normal", "--seed", "0").stdout
    m = run_py(PRESTAMP, body, "--intensity", "minimal").stdout
    ca, cn, cm = _img_count(a), _img_count(n), _img_count(m)
    assert ca >= cn >= cm, (ca, cn, cm)


def test_minimal_keeps_only_first_and_last_hit_per_sentence() -> None:
    # Three catalog hits: first / middle / last in one sentence — minimal drops the middle.
    body = "実装と確認と修正を進めます。\n"
    agg = run_py(PRESTAMP, body, "--intensity", "aggressive").stdout
    minimal = run_py(PRESTAMP, body, "--intensity", "minimal").stdout
    assert agg.count('<img') == 3
    assert minimal.count('<img') == 2
    assert 'alt="確認"' not in minimal


def test_normal_mode_is_deterministic_with_seed() -> None:
    body = "修正と対応を繰り返します。確認も必要です。\n"
    a = run_py(PRESTAMP, body, "--intensity", "normal", "--seed", "7").stdout
    b = run_py(PRESTAMP, body, "--intensity", "normal", "--seed", "7").stdout
    assert a == b


def test_intensity_sentinel_comment_on_non_aggressive_stdout() -> None:
    body = "今日は雑務です。\n"
    agg = run_py(PRESTAMP, body, "--intensity", "aggressive").stdout
    nrm = run_py(PRESTAMP, body, "--intensity", "normal", "--seed", "1").stdout
    mino = run_py(PRESTAMP, body, "--intensity", "minimal").stdout
    assert "<!-- mojiemoji-intensity:" not in agg
    assert nrm.rstrip().endswith("<!-- mojiemoji-intensity:normal -->")
    assert mino.rstrip().endswith("<!-- mojiemoji-intensity:minimal -->")
