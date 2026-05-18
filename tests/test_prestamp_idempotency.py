"""Tests for prestamp.py idempotency.

Re-running prestamp on already-stamped output must not double-stamp
or otherwise change the input. Covers both the emoji pass and the
single-kanji-tail edge case where the first pass's mask sentinel
prefix (`_`) must satisfy the SINGLE_HAN_LEFT_GUARD on the second run.
"""

from __future__ import annotations

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
