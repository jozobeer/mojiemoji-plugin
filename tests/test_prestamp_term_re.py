"""Tests for prestamp.py term-regex / boundary rules.

Covers:
- longest match preference (`修正版` keeps `版` plain after `修正` stamp)
- variant spread for repeated terms
- ASCII-identifier boundary protection (short keys `OS`/`PR`/`URL`)
- single-digit / single-kanji boundary guards (issue #52)
- end-to-end acceptance sentence from #52
"""

from __future__ import annotations

import re

from conftest import PRESTAMP, run_py


def _count_imgs(stdout: str) -> int:
    return stdout.count('align="absmiddle"')


def test_prestamp_uses_longest_match() -> None:
    # 修正版 is not its own catalog entry; the longest match is 修正, leaving
    # 版 as plain text. Both 修正 occurrences get stamped.
    proc = run_py(PRESTAMP, "修正版を修正しました。", "--seed", "1")

    assert proc.returncode == 0
    assert proc.stdout.count("mojiemoji.jozo.beer/emoji/") == 2
    assert proc.stdout.count('alt="修正"') == 2
    assert 'alt="修正版"' not in proc.stdout
    # 版 should sit as plain text immediately after the first stamp's </img> close.
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


def test_prestamp_does_not_split_ascii_identifiers_with_short_keys() -> None:
    # `OS`, `CI`, `PR`, `API`, `URL` etc. are catalog entries — when they
    # sit inside another ASCII identifier (POST / ASCII / PROCESS /
    # APIDocs / URLencoded) prestamp must NOT split them. Standalone
    # tokens with non-alpha boundaries still get stamped.
    body = (
        "POST と PATCH は ASCII 識別子。standalone な PR と URL は対象。\n"
        "PROCESS / APIDocs / URLencoded は触らない。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "7")

    assert proc.returncode == 0
    assert "POST" in proc.stdout
    assert "PATCH" in proc.stdout
    assert "ASCII" in proc.stdout
    assert "PROCESS" in proc.stdout
    assert "APIDocs" in proc.stdout
    assert "URLencoded" in proc.stdout
    assert 'alt="PR"' in proc.stdout
    assert 'alt="URL"' in proc.stdout


def test_single_digit_does_not_stamp_inside_version_string() -> None:
    # `v1.2.3` — every digit is part of a version triple, preceded by
    # ASCII letter or period, followed by digit or period.
    proc = run_py(PRESTAMP, "v1.2.3", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_inside_unit_value() -> None:
    proc = run_py(PRESTAMP, "100ms", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_inside_hash_reference() -> None:
    # `#1234` — `1` preceded by `#`, `2`/`3`/`4` preceded by digit.
    # None pass the lookbehind/lookahead guards.
    proc = run_py(PRESTAMP, "#1234", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_with_only_whitespace_left_context() -> None:
    # `Step 1` — `1` preceded by space (ASCII to the left of space).
    # Lookbehind requires Japanese *immediately* before; block.
    proc = run_py(PRESTAMP, "Step 1 として実装", "--seed", "1")

    assert proc.returncode == 0
    # 実装 stamps, but not `1`.
    assert _count_imgs(proc.stdout) == 1
    assert 'alt="実装"' in proc.stdout
    assert 'alt="1"' not in proc.stdout


def test_promise_all_does_not_stamp() -> None:
    # `Promise.all` has no catalog hits — regression guard against
    # accidental ASCII catalog additions.
    proc = run_py(PRESTAMP, "Promise.all", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0


def test_single_digit_stamps_inside_japanese_flow() -> None:
    # `仕様変更1件` — `1` preceded by `更` (Han), followed by `件` (Han,
    # not in catalog). Both guards pass; `1` should stamp.
    proc = run_py(PRESTAMP, "仕様変更1件", "--seed", "1")

    assert proc.returncode == 0
    assert 'alt="1"' in proc.stdout
    assert 'alt="仕様"' in proc.stdout
    assert 'alt="変更"' in proc.stdout


def test_single_kanji_blocked_when_preceded_by_han() -> None:
    # `先月` — `月` preceded by Han `先` (not in catalog). Block.
    proc = run_py(PRESTAMP, "先月", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0


def test_single_kanji_stamps_at_start_of_line() -> None:
    # `火曜の昼` — `火` at SOL (no preceding Han). The rule allows Han
    # to follow, since the issue's intent is to surface weekday glyphs.
    proc = run_py(PRESTAMP, "火曜の昼", "--seed", "1")

    assert proc.returncode == 0
    assert 'alt="火"' in proc.stdout


def test_full_issue_acceptance_sentence() -> None:
    # Verification sentence from issue #52:
    #   "v1.2.3 で 100ms の修正を Step 1 として実装した。後で 火 にレビュー。"
    # Expectation: only 修正 / 実装 / 後 / 火 stamp.
    body = "v1.2.3 で 100ms の修正を Step 1 として実装した。後で 火 にレビュー。"
    proc = run_py(PRESTAMP, body, "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 4
    for term in ("修正", "実装", "後", "火"):
        assert f'alt="{term}"' in proc.stdout, f"expected stamp for {term}"
    for plain in ('alt="1"', 'alt="2"', 'alt="3"', 'alt="0"'):
        assert plain not in proc.stdout, f"unexpected stamp: {plain}"
