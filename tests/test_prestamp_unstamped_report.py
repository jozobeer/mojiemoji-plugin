"""Tests for prestamp.py's `--report-unstamped` JSON output.

After the term + emoji passes, prestamp emits a JSON report listing
2–8 char Kanji / Katakana runs that survived (i.e. catalog misses
worth proposing as new entries). Safe zones, summary sections, and
pure-hiragana runs are excluded. `--report-unstamped-to <file>`
writes to disk while keeping markdown on stdout.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import PRESTAMP, run_py


def test_prestamp_reports_unstamped_japanese_runs(tmp_path: Path) -> None:
    body = "これは特殊用語と未収録単語のテストです。特殊用語が再度登場。\n"
    proc = run_py(PRESTAMP, body, "--seed", "1", "--report-unstamped")

    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    terms = {entry["term"]: entry for entry in report["unstamped"]}

    assert "特殊用語" in terms
    assert terms["特殊用語"]["count"] == 2
    assert "未収録単語" in terms
    # Catalog hits (テスト, 登場) must NOT appear — they got <img>-stamped.
    assert "テスト" not in terms
    assert "登場" not in terms
    # Contexts are clean — no mask token fragments left.
    for entry in report["unstamped"]:
        for ctx in entry["contexts"]:
            assert "MOJIEMOJI" not in ctx
            assert "__" not in ctx


def test_prestamp_unstamped_report_excludes_safe_zones() -> None:
    body = (
        "本文では未収録単語を扱う。\n"
        "\n"
        "```python\n"
        "# 漢字の固有名詞は code fence なので対象外\n"
        "```\n"
        "\n"
        "`inline_漢字_inline` も対象外。\n"
        "[リンク先](https://example.com/専門用語) のリンク target も対象外。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "1", "--report-unstamped")

    assert proc.returncode == 0
    terms = {entry["term"] for entry in json.loads(proc.stdout)["unstamped"]}

    assert "未収録単語" in terms
    assert "固有名詞" not in terms
    assert "専門用語" not in terms


def test_prestamp_unstamped_report_skips_summary_content() -> None:
    body = (
        "本文の未収録語は対象。\n"
        "<details>\n"
        "<summary>サマリ部分の漢字は対象外</summary>\n"
        "詳細の漢字は対象。\n"
        "</details>\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "1", "--report-unstamped")

    assert proc.returncode == 0
    terms = {entry["term"] for entry in json.loads(proc.stdout)["unstamped"]}

    assert "未収録語" in terms
    assert "対象外" not in terms


def test_prestamp_unstamped_report_excludes_pure_hiragana() -> None:
    body = "ひらがな ばかり と かんじが まじる いっぽうで 漢字熟語 は 対象。\n"
    proc = run_py(PRESTAMP, body, "--seed", "1", "--report-unstamped")

    assert proc.returncode == 0
    terms = {entry["term"] for entry in json.loads(proc.stdout)["unstamped"]}

    # No pure-hiragana run should be reported (regex excludes hiragana).
    for term in terms:
        assert not all("぀" <= ch <= "ゟ" for ch in term)


def test_prestamp_unstamped_to_file_writes_json_and_keeps_markdown(tmp_path: Path) -> None:
    body = "未収録単語のテスト。\n"
    report_path = tmp_path / "report.json"
    proc = run_py(
        PRESTAMP, body, "--seed", "1",
        "--report-unstamped-to", str(report_path),
    )

    assert proc.returncode == 0
    # Markdown still goes to stdout.
    assert "align=\"absmiddle\"" in proc.stdout
    # JSON report on disk.
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    terms = {entry["term"] for entry in data["unstamped"]}
    assert "未収録単語" in terms
