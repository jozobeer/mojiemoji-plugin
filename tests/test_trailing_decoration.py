"""Tests for coverage.py's trailing-decoration warning (issue #60).

Headings ending in plain Japanese (no `<img>` stamp at the end) get a
soft warning; English headings are exempt; code fences, table rows,
and bullet lists are not "prose paragraphs" so they don't trigger
the warning. Trailing-decoration warnings are reported but never
escalate to block-level failures.
"""

from __future__ import annotations

import importlib.util

from conftest import COVERAGE, run_py


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
    assert all("paragraph 2" not in line for line in paragraph_warnings), paragraph_warnings
