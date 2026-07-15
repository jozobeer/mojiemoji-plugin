"""Tests for prestamp.py idempotency.

Re-running prestamp on already-stamped output must not double-stamp
or otherwise change the input. Covers both the emoji pass and the
single-kanji-tail edge case where the first pass's mask sentinel
prefix (`_`) must satisfy the SINGLE_HAN_LEFT_GUARD on the second run.
"""

from __future__ import annotations

import pytest

from conftest import PRESTAMP, run_py


def test_prestamp_is_idempotent_for_emoji_pass() -> None:
    # Running prestamp twice must not double-stamp emoji that the first
    # pass already converted into <img> tags.
    once = run_py(PRESTAMP, "やった 🎉 完成！", "--seed", "8")
    twice = run_py(PRESTAMP, once.stdout, "--seed", "8")

    assert once.returncode == 0
    assert twice.returncode == 0
    assert once.stdout == twice.stdout


def test_prestamp_is_idempotent_for_compound_with_single_kanji_tail() -> None:
    # `編集後` mixes a 2-char multi-key (`編集`) with a single-kanji tail
    # (`後`). First pass: regex sees `編集後`, longest-match takes `編集`,
    # leaves `後` blocked by SINGLE_HAN_LEFT_GUARD because `集` (Han) sits
    # to the left. Second pass: `編集` is now a `__MOJIEMOJI_MASK_N__`
    # sentinel — the char left of `後` is `_`, not Han. Without the `_`
    # in the negative lookbehind, `後` would stamp on the second pass and
    # break idempotency / the CI drift check.
    once = run_py(PRESTAMP, "編集後の確認。\n", "--seed", "6")
    twice = run_py(PRESTAMP, once.stdout, "--seed", "6")

    assert once.returncode == 0
    assert twice.returncode == 0
    assert once.stdout == twice.stdout


@pytest.mark.parametrize("intensity", ["normal", "minimal"])
def test_prestamp_is_idempotent_with_intensity_sentinel(intensity: str) -> None:
    once = run_py(PRESTAMP, "実装と確認と修正を進めます。\n", "--intensity", intensity)
    twice = run_py(PRESTAMP, once.stdout, "--intensity", intensity)

    assert once.returncode == 0
    assert twice.returncode == 0
    assert once.stdout == twice.stdout
    assert twice.stdout.count(f"<!-- mojiemoji-intensity:{intensity} -->") == 1


@pytest.mark.parametrize("intensity", ["normal", "minimal"])
def test_prestamp_processes_new_sentence_before_existing_sentinel(intensity: str) -> None:
    once = run_py(PRESTAMP, "修正を進めます。\n", "--intensity", intensity)
    sentinel = f"<!-- mojiemoji-intensity:{intensity} -->\n"
    edited = once.stdout.removesuffix(sentinel) + "確認します。\n" + sentinel
    updated = run_py(PRESTAMP, edited, "--intensity", intensity)

    assert once.returncode == 0
    assert updated.returncode == 0
    assert updated.stdout.startswith(once.stdout.removesuffix(sentinel))
    assert 'alt="確認"' in updated.stdout
    assert updated.stdout.count(sentinel) == 1


@pytest.mark.parametrize("intensity", ["normal", "minimal"])
def test_prestamp_processes_new_sentence_after_existing_sentinel(intensity: str) -> None:
    once = run_py(PRESTAMP, "修正を進めます。\n", "--intensity", intensity)
    edited = once.stdout + "確認します。\n"
    updated = run_py(PRESTAMP, edited, "--intensity", intensity)

    assert once.returncode == 0
    assert updated.returncode == 0
    assert 'alt="確認"' in updated.stdout
    assert updated.stdout.count(f"<!-- mojiemoji-intensity:{intensity} -->") == 1


def test_prestamp_collapses_duplicate_trailing_intensity_sentinels() -> None:
    sentinel = "<!-- mojiemoji-intensity:minimal -->\n"
    once = run_py(PRESTAMP, "修正を進めます。\n", "--intensity", "minimal")
    cleaned = run_py(PRESTAMP, once.stdout + sentinel, "--intensity", "minimal")

    assert once.returncode == 0
    assert cleaned.returncode == 0
    assert cleaned.stdout == once.stdout


@pytest.mark.parametrize("intensity", ["normal", "minimal"])
def test_prestamp_without_trailing_newline_remains_idempotent(intensity: str) -> None:
    once = run_py(PRESTAMP, "実装と確認と修正", "--intensity", intensity)
    twice = run_py(PRESTAMP, once.stdout, "--intensity", intensity)

    assert once.returncode == 0
    assert twice.returncode == 0
    assert once.stdout == twice.stdout
    assert f"\n<!-- mojiemoji-intensity:{intensity} -->\n" in twice.stdout


def test_processed_sentence_mask_does_not_collide_with_inline_code_mask() -> None:
    intensity = "minimal"
    sentinel = f"<!-- mojiemoji-intensity:{intensity} -->\n"
    once = run_py(PRESTAMP, "修正します。", "--intensity", intensity)
    processed = once.stdout.removesuffix(sentinel).rstrip("\n")
    edited = f"{processed}`code` を確認します。\n{sentinel}"
    updated = run_py(PRESTAMP, edited, "--intensity", intensity)

    assert updated.returncode == 0
    assert 'alt="修正"' in updated.stdout
    assert "`code`" in updated.stdout
    assert 'alt="確認"' in updated.stdout


def test_minimal_emoji_overflow_is_idempotent() -> None:
    once = run_py(PRESTAMP, "✅❌👀\n", "--intensity", "minimal")
    twice = run_py(PRESTAMP, once.stdout, "--intensity", "minimal")

    assert once.returncode == 0
    assert twice.returncode == 0
    assert once.stdout == twice.stdout


def test_aggressive_mode_removes_stale_intensity_sentinel() -> None:
    normal = run_py(PRESTAMP, "修正と確認を進めます。\n", "--intensity", "normal")
    aggressive = run_py(PRESTAMP, normal.stdout, "--intensity", "aggressive")

    assert normal.returncode == 0
    assert aggressive.returncode == 0
    assert "<!-- mojiemoji-intensity:" not in aggressive.stdout


def test_intensity_sentinel_inside_fence_is_not_processing_metadata() -> None:
    body = "```text\n<!-- mojiemoji-intensity:minimal -->\n"
    result = run_py(PRESTAMP, body, "--intensity", "minimal")

    assert result.returncode == 0
    assert result.stdout.startswith(body)
    assert result.stdout.endswith("<!-- mojiemoji-intensity:minimal -->\n")
    assert result.stdout.count("<!-- mojiemoji-intensity:minimal -->") == 2
