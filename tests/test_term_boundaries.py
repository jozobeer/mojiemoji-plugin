"""Tests for skills/mojiemoji-github/scripts/lib/term_boundaries.py.

The boundary helpers are consumed by both `prestamp.py` (mechanical
replacement) and `hooks/mojiemoji_japanese_gate.py` (catalog-leftover
detection). Drift between the two would mean: a body the hook blocks
as "uncovered" cannot be auto-fixed by prestamp, leaving the author
no path forward. These tests pin that the two paths agree on what
counts as a standalone catalog hit.

Coverage:

  1. `is_ascii_key` classification matches the prestamp 4-tier split.
  2. `count_occurrences` applies ASCII word boundaries for keys like
     ``OS`` / ``CI`` / ``URL`` so larger identifiers don't false-match.
  3. Non-ASCII keys (Kanji / Katakana) keep plain substring semantics,
     matching the hook's pre-#98 behaviour.
  4. The same import works whether called from the scripts directory
     (prestamp) or via the sys.path injection used by the hook.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"


@pytest.fixture(scope="module", autouse=True)
def _add_scripts_to_path() -> None:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.mark.parametrize(
    "term,expected",
    [
        ("URL", True),
        ("PR", True),
        ("OS", True),
        ("CI", True),
        ("E2E", True),
        ("snake_case", True),
        ("API_KEY", True),
        ("対応", False),
        ("ハンマー", False),
        ("致命傷", False),
        ("月", False),
        ("ASCII×日本語", False),
    ],
)
def test_is_ascii_key_classification(term: str, expected: bool) -> None:
    from lib.term_boundaries import is_ascii_key

    assert is_ascii_key(term) is expected


@pytest.mark.parametrize(
    "term,text,expected",
    [
        # Standalone ASCII keys count.
        ("OS", "OS は重要", 1),
        ("CI", "CI が通った", 1),
        ("URL", "URL を貼る", 1),
        # ASCII keys inside larger identifiers do NOT count (the bug
        # #98 exists to fix).
        ("OS", "POST リクエスト", 0),
        ("CI", "ASCII エンコード", 0),
        ("PR", "PRINT 文", 0),
        ("URL", "URLEncode 関数", 0),
        # Multiple standalone hits accumulate.
        ("PR", "PR を出して PR を merge", 2),
        # Mixed: standalone + inside-identifier → only the standalone
        # counts.
        ("OS", "OS と POST と OS", 2),
        # Underscore is part of the identifier boundary character
        # class, so `URL_HELPER` does NOT count as a `URL` hit.
        ("URL", "URL_HELPER という変数", 0),
        # Digits too: `CI2` is one identifier, not `CI`.
        ("CI", "CI2 stage", 0),
    ],
)
def test_count_occurrences_ascii_boundary(term: str, text: str, expected: int) -> None:
    from lib.term_boundaries import count_occurrences

    assert count_occurrences(text, term) == expected


@pytest.mark.parametrize(
    "term,text,expected",
    [
        # Non-ASCII keys use plain substring counting — Japanese flow
        # does not have an "identifier character" notion.
        ("対応", "対応します", 1),
        ("対応", "対応して、もう一度対応", 2),
        # No word boundary applied — the catalog term `対` would
        # still hit inside `絶対` if it were a multi-char compound
        # registered as `絶対`. We pin plain substring semantics here.
        ("致命", "致命傷を負う", 1),
        ("ハンマー", "ハンマー投げ", 1),
    ],
)
def test_count_occurrences_non_ascii_substring(term: str, text: str, expected: int) -> None:
    from lib.term_boundaries import count_occurrences

    assert count_occurrences(text, term) == expected


def test_prestamp_and_helper_agree_on_ascii_keys() -> None:
    """The prestamp regex tier-split and the helper's ASCII detection
    must classify catalog keys identically — otherwise prestamp could
    rewrite a hit that the hook ignores, or vice versa."""
    prestamp = importlib.import_module("prestamp")
    from lib.term_boundaries import is_ascii_key

    sample_keys = [
        "URL", "PR", "API", "OS", "CI", "URI", "UX",  # ASCII
        "対応", "確認", "検証", "致命",  # Han compounds
        "ハンマー",  # Katakana
        "snake_case", "API_KEY",  # ASCII identifiers
        "月", "後",  # single Han
    ]
    for k in sample_keys:
        assert is_ascii_key(k) == bool(prestamp.ASCII_KEY_RE.match(k)), k


def test_bounded_re_matches_standalone_only() -> None:
    from lib.term_boundaries import bounded_re

    pattern = bounded_re("OS")
    assert pattern.findall("OS は POST より速い") == ["OS"]
    assert pattern.findall("POSTER という単語") == []


def test_helper_constants_match_prestamp_constants() -> None:
    """If prestamp's local constants drift from the shared module, the
    4-tier regex would build with one boundary while the hook applies
    another — pin equality so this can't happen silently."""
    prestamp = importlib.import_module("prestamp")
    from lib import term_boundaries

    assert prestamp.ASCII_KEY_RE.pattern == term_boundaries.ASCII_KEY_RE.pattern
    assert prestamp.ASCII_LEFT_GUARD == term_boundaries.ASCII_LEFT_GUARD
    assert prestamp.ASCII_RIGHT_GUARD == term_boundaries.ASCII_RIGHT_GUARD
