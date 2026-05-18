"""Tests for prestamp.py and coverage.py scripts."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
PRESTAMP = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "prestamp.py"
COVERAGE = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "coverage.py"
GENERATE = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "generate_catalog.py"


def run_py(script: Path, text: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
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
    proc = run_py(PRESTAMP, body, "--seed", "5")

    assert proc.returncode == 0
    assert proc.stdout.count('align="absmiddle"') == 1
    assert "alt=\"修正\"" in proc.stdout
    assert '<img src="https://mojiemoji.jozo.beer/emoji/%E4%BF%AE%E6%AD%A3?font=gothic-bold&color=3b82f6&animation=bane&background=transparent&outline=darker&outline_width=2" alt="修正">' in proc.stdout
    assert "`修正`" in proc.stdout
    assert "https://img.shields.io/badge/修正-ok" in proc.stdout
    assert "[リンク](https://example.com/修正)" in proc.stdout
    assert "A[修正] --> B[完了]" in proc.stdout
    assert "puts '修正'" in proc.stdout


def test_prestamp_decorates_inline_comment_prose_but_preserves_suggestions() -> None:
    body = """このコメントは修正方針を確認します。

```suggestion
修正済みです
```

`確認` はコード引用なので触らない。
"""
    proc = run_py(PRESTAMP, body, "--seed", "13")

    assert proc.returncode == 0
    assert proc.stdout.count('alt="修正"') == 1
    assert proc.stdout.count('alt="確認"') == 1
    assert "修正済みです" in proc.stdout
    assert "`確認`" in proc.stdout


def test_prestamp_uses_longest_match() -> None:
    # 修正版 is not its own catalog entry; the longest match is 修正, leaving
    # 版 as plain text. Both 修正 occurrences in the input get stamped.
    proc = run_py(PRESTAMP, "修正版を修正しました。", "--seed", "1")

    assert proc.returncode == 0
    assert proc.stdout.count("mojiemoji.jozo.beer/emoji/") == 2
    assert proc.stdout.count('alt="修正"') == 2
    assert 'alt="修正版"' not in proc.stdout
    # 版 should be plain text immediately after the first stamp's </img> close.
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
    # (The pre-existing <img alt="🎉"> in the body is preserved verbatim,
    # so the total alt=🎉 count is 2; the new emoji stamps add exactly 1.)
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
    # ✅❌👀 are all in the catalog. The first two get stamped, the
    # third stays raw to avoid visual crowding. Whitespace breaks the
    # run, so `✅ ❌ 👀` stamps all three.
    proc = run_py(PRESTAMP, "三連続 ✅❌👀 と 空白付き ✅ ❌ 👀", "--seed", "6")

    assert proc.returncode == 0
    stamps = re.findall(r'alt="([^"]+)"', proc.stdout)
    # Run 1 ("✅❌👀"): ✅+❌ stamped, 👀 raw.
    # Run 2 ("✅ ❌ 👀"): all 3 stamped.
    # Total stamped alts: ✅×2 + ❌×2 + 👀×1 = 5.
    assert stamps.count("✅") == 2
    assert stamps.count("❌") == 2
    assert stamps.count("👀") == 1
    # The third emoji of the first run survives as plain Unicode
    # immediately after a stamped ❌. The exact char position is
    # brittle to track, but the stamp count above already proves it.


def test_prestamp_strips_vs16_when_matching_emoji_catalog() -> None:
    # `⚠️` is U+26A0 U+FE0F (variation selector). emoji-catalog stores
    # the base codepoint `⚠` only. prestamp strips VS16 before lookup.
    body = "注意 ⚠️ してください。"
    proc = run_py(PRESTAMP, body, "--seed", "7")

    assert proc.returncode == 0
    assert 'alt="⚠"' in proc.stdout
    # VS16 must not appear in the output (it was stripped before lookup
    # and the catalog key has no VS16).
    assert "⚠️" not in proc.stdout


def test_prestamp_does_not_flip_state_on_backticked_summary_tag() -> None:
    # `<summary>` inside inline code is documentation, not a real tag.
    # Regression: a backticked `<summary>` used to flip the state
    # machine and silently skip everything until a real `</summary>`
    # appeared (which can be never), dropping all subsequent stamps.
    #
    # Two representative shapes — `<summary>` alone and the trickier
    # `<details>/<summary>` combo. The latter is what the issue body
    # for #91 hit: a `/` sits between the opening backtick and the
    # `<summary>` token, defeating a naive lookbehind-on-backtick.
    body = (
        "前段で修正が走る。\n"
        "- 仕様は `<summary>` と同じ state machine で扱う。\n"
        "- `<details>/<summary>` の対応も同じ実装で扱う。\n"
        "- 末尾の確認も対応する。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "9")

    assert proc.returncode == 0
    # All four lines have catalog-hit terms and must all be stamped —
    # none should be lost to the phantom summary region.
    assert 'alt="修正"' in proc.stdout
    assert 'alt="仕様"' in proc.stdout
    assert 'alt="実装"' in proc.stdout
    assert 'alt="確認"' in proc.stdout
    # 対応 appears twice in the source.
    assert proc.stdout.count('alt="対応"') == 2
    # The backticked literals must round-trip intact.
    assert "`<summary>`" in proc.stdout
    assert "`<details>/<summary>`" in proc.stdout


def test_prestamp_preserves_vs16_on_uncatalogued_emoji() -> None:
    # ❤️ (U+2764 U+FE0F) and ☀️ (U+2600 U+FE0F) are not currently in
    # emoji-catalog.yml (verified at test time so it auto-skips if the
    # catalog grows). Their VS16 must round-trip — stripping it would
    # silently change emoji-presentation to text-presentation in user
    # content. Regression for codex P1 / Copilot review on PR #90.
    import yaml as _yaml
    catalog_path = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "emoji-catalog.yml"
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
    # No <img> was inserted for this emoji.
    assert f'alt="{miss}"' not in proc.stdout


def test_prestamp_skips_emoji_inside_summary() -> None:
    # codex P2: the emoji pass used to bypass <summary> entirely,
    # producing a stamped emoji inside a summary heading. Pin
    # symmetry with the text pass — both must leave summary content
    # alone.
    body = "<details>\n<summary>祝賀 🎉 メモ</summary>\n本文に 🎊 も出る。\n</details>\n"
    proc = run_py(PRESTAMP, body, "--seed", "12")

    assert proc.returncode == 0
    # Summary 🎉 stays raw, summary 祝賀 also stays raw (text pass
    # already pins this).
    assert "<summary>祝賀 🎉 メモ</summary>" in proc.stdout
    # Body 🎊 outside the summary still gets stamped.
    assert 'alt="🎊"' in proc.stdout


def test_prestamp_is_idempotent_for_emoji_pass() -> None:
    # Running prestamp twice must not double-stamp emoji that the first
    # pass already converted into <img> tags.
    once = run_py(PRESTAMP, "やった 🎉 完成！", "--seed", "8")
    twice = run_py(PRESTAMP, once.stdout, "--seed", "8")

    assert once.returncode == 0
    assert twice.returncode == 0
    assert once.stdout == twice.stdout


def test_prestamp_skips_details_summary_but_stamps_details_body() -> None:
    body = "<details>\n<summary>修正方針</summary>\n本文は修正対象です。\n</details>\n"
    proc = run_py(PRESTAMP, body, "--seed", "2")

    assert proc.returncode == 0
    assert "<summary>修正方針</summary>" in proc.stdout
    assert 'align="absmiddle"' in proc.stdout


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
    # No alt="OS" inside a "P...T" sequence — verify the literal POST survived.
    assert "POST" in proc.stdout
    assert "PATCH" in proc.stdout
    assert "ASCII" in proc.stdout
    assert "PROCESS" in proc.stdout
    assert "APIDocs" in proc.stdout
    assert "URLencoded" in proc.stdout
    # Standalone PR + URL still get stamped (alt attrs present somewhere).
    assert 'alt="PR"' in proc.stdout
    assert 'alt="URL"' in proc.stdout


def test_prestamp_normalizes_tailwind_600_colors_in_output() -> None:
    # Catalog entries still carry some Tailwind 600+ values (e.g. db2777 /
    # 2563eb / ca8a04) which are unreadable on GitHub's dark theme. The
    # render layer must downgrade them to the matching 400-series so
    # output ships safe regardless of catalog state.
    proc = run_py(PRESTAMP, "修正の確認、対応も含めて全体の構造。\n", "--seed", "9")

    assert proc.returncode == 0
    forbidden = (
        "color=ca8a04", "color=16a34a", "color=dc2626", "color=2563eb",
        "color=7c3aed", "color=db2777", "color=0891b2", "color=d97706",
        "color=ea580c", "color=525252",
    )
    for needle in forbidden:
        assert needle not in proc.stdout, f"{needle} should be normalized away"


def test_prestamp_skips_transform_inside_off_on_markers() -> None:
    body = (
        "修正の確認。\n"
        "\n"
        "<!-- mojiemoji:off -->\n"
        "> プレーンな例: これは修正と確認と対応がそのまま。\n"
        "<!-- mojiemoji:on -->\n"
        "\n"
        "ここからまた修正。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "3")

    assert proc.returncode == 0
    before, rest = proc.stdout.split("<!-- mojiemoji:off -->", 1)
    disabled, after = rest.split("<!-- mojiemoji:on -->", 1)

    assert "<img" in before  # pre-off stamped
    assert "<img" not in disabled  # disabled body untouched
    assert "修正" in disabled and "確認" in disabled and "対応" in disabled
    assert "<img" in after  # post-on resumed


def test_prestamp_off_without_on_extends_to_eof() -> None:
    body = (
        "修正前のスタンプ。\n"
        "<!-- mojiemoji:off -->\n"
        "ここから先は修正も確認も対応もスタンプにならない。\n"
        "ファイル末尾まで継続。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "1")

    assert proc.returncode == 0
    _, disabled = proc.stdout.split("<!-- mojiemoji:off -->", 1)
    assert "<img" not in disabled


def test_prestamp_redundant_off_and_on_are_no_ops() -> None:
    body = (
        "<!-- mojiemoji:off -->\n"
        "内側 off も no-op、確認 raw。\n"
        "<!-- mojiemoji:off -->\n"
        "ここも修正 raw。\n"
        "<!-- mojiemoji:on -->\n"
        "ここから修正は stamp。\n"
        "<!-- mojiemoji:on -->\n"
        "redundant on の後も対応はそのまま stamp。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "2")

    assert proc.returncode == 0
    head, tail = proc.stdout.split("<!-- mojiemoji:on -->", 1)
    assert "<img" not in head
    assert "<img" in tail


def test_prestamp_off_on_freezes_emoji_pass_too() -> None:
    body = (
        "🎉 はスタンプされる\n"
        "<!-- mojiemoji:off -->\n"
        "🎉 はそのまま\n"
        "<!-- mojiemoji:on -->\n"
        "🎉 もう一度スタンプ\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "4")

    assert proc.returncode == 0
    # 2 stamps total — outside the off-region only.
    assert proc.stdout.count("<img") == 2


def test_prestamp_off_on_markers_render_invisibly() -> None:
    # GitHub renders HTML comments as nothing — the markers must survive
    # verbatim in the output so author intent is preserved.
    body = (
        "<!-- mojiemoji:off -->\n"
        "raw line\n"
        "<!-- mojiemoji:on -->\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "1")

    assert proc.returncode == 0
    assert "<!-- mojiemoji:off -->" in proc.stdout
    assert "<!-- mojiemoji:on -->" in proc.stdout


def test_prestamp_reports_unstamped_japanese_runs(tmp_path: Path) -> None:
    body = "これは特殊用語と未収録単語のテストです。特殊用語が再度登場。\n"
    proc = run_py(PRESTAMP, body, "--seed", "1", "--report-unstamped")

    assert proc.returncode == 0
    import json
    report = json.loads(proc.stdout)
    terms = {entry["term"]: entry for entry in report["unstamped"]}

    assert "特殊用語" in terms
    assert terms["特殊用語"]["count"] == 2
    assert "未収録単語" in terms
    # catalog hits (テスト, 登場) must NOT appear — they got <img>-stamped.
    assert "テスト" not in terms
    assert "登場" not in terms
    # contexts are clean — no mask token fragments left.
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
    import json
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
    import json
    terms = {entry["term"] for entry in json.loads(proc.stdout)["unstamped"]}

    assert "未収録語" in terms
    # 詳細の漢字は対象 → 詳細 と 漢字 が出るかもしれないが、サマリ部分の語は出ないこと。
    assert "対象外" not in terms


def test_prestamp_unstamped_report_excludes_pure_hiragana() -> None:
    body = "ひらがな ばかり と かんじが まじる いっぽうで 漢字熟語 は 対象。\n"
    proc = run_py(PRESTAMP, body, "--seed", "1", "--report-unstamped")

    assert proc.returncode == 0
    import json
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
    import json
    data = json.loads(report_path.read_text())
    terms = {entry["term"] for entry in data["unstamped"]}
    assert "未収録単語" in terms


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
    import importlib.util

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

    # Failures list must NOT contain any trailing-slot violations.
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
    # The list block (paragraph 2) should not be flagged.
    assert all("paragraph 2" not in line for line in paragraph_warnings), paragraph_warnings


def test_no_warning_on_catalog_hit_unicode_emoji(tmp_path: Path) -> None:
    # prestamp.py now auto-substitutes catalog emoji during the emoji
    # pass (#89). So a Unicode emoji surviving into the coverage check
    # is intentional — either catalog-miss or inside a safe-zone —
    # and the old "uses Unicode X but mojiemoji variant exists in
    # catalog" warning is obsolete. Pin that the warning no longer
    # fires for catalog-hit emoji.
    import yaml as _yaml
    catalog_path = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "emoji-catalog.yml"
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


def test_generate_catalog_emits_diverse_variants_per_term() -> None:
    proc = run_py(GENERATE, "完成\n", "--seed", "42", "--variants", "3")

    assert proc.returncode == 0
    fonts = re.findall(r"- font: (\S+)", proc.stdout)
    animations = re.findall(r"animation: (\S+)", proc.stdout)
    colors = re.findall(r'color: "([^"]+)"', proc.stdout)
    assert len(fonts) == 3
    assert len(set(fonts)) == 3
    assert len(set(animations)) == 3
    assert len(set(colors)) == 3


def test_generate_catalog_outline_is_bgr_rotation_of_color() -> None:
    proc = run_py(GENERATE, "完成\n", "--seed", "42", "--variants", "3")

    assert proc.returncode == 0
    pairs = re.findall(r'color: "([0-9a-f]{6})"\s+outline: "([0-9a-f]{6})"', proc.stdout)
    assert pairs, f"no color+outline pairs found in:\n{proc.stdout}"
    for color, outline in pairs:
        expected = color[4:6] + color[0:2] + color[2:4]
        assert outline == expected, f"{color} -> outline {outline} (expected {expected})"


def test_generate_catalog_splits_3plus_kanji_via_compound_variant() -> None:
    # 誤検知 is 3 kanji, exceeds single-stamp rule (kanji <= 2), so
    # split_term decomposes it via the prefix-modifier heuristic
    # (誤 + 検知) and emits a compound variant with adjacent chunks.
    proc = run_py(GENERATE, "誤検知\n完成\n", "--seed", "1")

    assert proc.returncode == 0
    assert "完成:" in proc.stdout
    assert "誤検知:" in proc.stdout
    assert "chunks:" in proc.stdout
    assert "text: 誤" in proc.stdout
    assert "text: 検知" in proc.stdout


def test_generate_catalog_skips_unsplittable_terms() -> None:
    # 4 hiragana is a single-stamp case (<=4); use something that has no
    # valid 2-stamp decomposition: a long single-script run.
    proc = run_py(GENERATE, "完成\nあいうえおか\n", "--seed", "1")

    assert proc.returncode == 0
    assert "完成:" in proc.stdout
    assert "あいうえおか" not in proc.stdout
    assert "あいうえおか" in proc.stderr


def test_generate_catalog_handles_color_shifting_and_rotational_animations() -> None:
    # Sweep many terms / seeds to exercise the kira/disco/psycho and kaiten paths.
    proc = run_py(
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


def test_prestamp_handles_indented_and_tilde_fences() -> None:
    body = (
        "   ```ruby\n"
        "puts '修正'\n"
        "   ```\n"
        "\n"
        "~~~text\n"
        "修正\n"
        "~~~\n"
        "\n"
        "修正\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "3")

    assert proc.returncode == 0
    # Both fenced blocks preserved verbatim — neither 修正 inside fences stamped.
    assert "puts '修正'" in proc.stdout
    assert "~~~text\n修正\n~~~" in proc.stdout
    # The bare 修正 outside fences is the only stamped occurrence.
    assert proc.stdout.count('align="absmiddle"') == 1


def test_prestamp_handles_nested_fence_markers() -> None:
    # A shorter ``` inside a ```` block must not close the outer fence.
    body = (
        "````md\n"
        "```ruby\n"
        "修正\n"
        "```\n"
        "````\n"
        "\n"
        "修正\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "4")

    assert proc.returncode == 0
    # 修正 inside the nested fence stays plain; only the outer 修正 stamps.
    assert "```ruby\n修正\n```" in proc.stdout
    assert proc.stdout.count('align="absmiddle"') == 1


def test_coverage_ignores_bare_urls_outside_img() -> None:
    # Bare URL inside a markdown link should NOT count as a rendered stamp —
    # only `<img src="…">` wrappers do.
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
    # Only the <img> wrapped occurrence counts.
    assert "stamps=1" in proc.stdout


def test_sentence_hit_rate_not_fragmented_by_stamp_url_query(tmp_path: Path) -> None:
    # Regression for issue #78: `?` in mojiemoji `<img>` URL query strings
    # (e.g. `?font=...`) used to be treated as a sentence separator, which
    # both fragmented the sentence count AND broke per-sentence stamp
    # detection. A single stamped sentence must measure as 1 sentence with
    # full hit rate, regardless of how many `?` appear inside stamp URLs.
    import importlib.util

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
    # Acceptance criterion for issue #78: adding stamps must never DECREASE
    # sentence_hit_rate. Before the fix, more stamps meant more `?` in
    # URLs, fragmenting more sentences and tanking the rate — the opposite
    # of the 下処理 first principle.
    import importlib.util

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


# ---------------------------------------------------------------------------
# split_term + compound-variant tests (issue #42)
# ---------------------------------------------------------------------------


def _gen_term_yaml(term: str, seed: str = "42", variants: int = 1) -> str:
    """Run generate-catalog on a single term and return only its yaml block."""
    proc = run_py(GENERATE, term + "\n", "--seed", seed, "--variants", str(variants))
    assert proc.returncode == 0
    return proc.stdout


def test_split_term_prefix_modifier_unsorted_3kanji() -> None:
    # 不一致 has prefix 不 (modifier) and no suffix nominalizer; split as
    # `不 + 一致`.
    out = _gen_term_yaml("不一致")

    assert "不一致:" in out
    assert "text: 不\n" in out
    assert "text: 一致\n" in out


def test_split_term_suffix_nominalizer_wins_over_prefix() -> None:
    # 初期化 has BOTH prefix 初 (modifier) AND suffix 化 (nominalizer).
    # Suffix wins per the heuristic: `初期 + 化`, not `初 + 期化`.
    out = _gen_term_yaml("初期化")

    assert "初期化:" in out
    assert "text: 初期\n" in out
    assert "text: 化\n" in out


def test_split_term_4kanji_balanced_split() -> None:
    # 4-kanji compound with no prefix/suffix → 2+2 fallback.
    out = _gen_term_yaml("緊急対応")

    assert "緊急対応:" in out
    assert "text: 緊急\n" in out
    assert "text: 対応\n" in out


def test_split_term_katakana_3plus_remainder() -> None:
    # 5-katakana word: prefer 3+remainder split.
    out = _gen_term_yaml("クラッシュ")

    assert "クラッシュ:" in out
    assert "text: クラッ\n" in out
    assert "text: シュ\n" in out


def test_split_term_character_class_boundary() -> None:
    # 修正お願い (kanji 3 + hira 2 = 5 chars). kanji > 2 forces split;
    # the kanji↔hira boundary at index 2 yields `修正` (2 kanji) +
    # `お願い` (hira+kanji+hira = 3 chars), both single-stampable.
    out = _gen_term_yaml("修正お願い")

    assert "修正お願い:" in out
    assert "text: 修正\n" in out
    assert "text: お願い\n" in out


def test_compound_variant_chunks_share_flavor() -> None:
    # Both chunks in a single variant must use the same font/color/animation
    # so the split reads as one cohesive word per SKILL.md guidance.
    out = _gen_term_yaml("緊急対応", variants=1)

    fonts = re.findall(r"font: (\w[\w-]*)", out)
    colors = re.findall(r'color: "([0-9a-f]{6})"', out)
    anims = re.findall(r"animation: (\w+)", out)

    assert len(fonts) == 2
    assert fonts[0] == fonts[1], f"fonts differ across chunks: {fonts}"
    assert len(colors) == 2
    assert colors[0] == colors[1], f"colors differ across chunks: {colors}"
    assert len(anims) == 2
    assert anims[0] == anims[1], f"animations differ across chunks: {anims}"


def test_prestamp_renders_compound_variant_as_adjacent_imgs(tmp_path) -> None:
    # End-to-end: a compound variant in YAML renders as N adjacent <img>
    # tags with no separator, each chunk's text URL-encoded individually.
    catalog = tmp_path / "catalog.yml"
    catalog.write_text(
        "defaults:\n"
        "  background: transparent\n"
        '  outline_width: "2"\n'
        "terms:\n"
        "  未着手:\n"
        "    - chunks:\n"
        "        - text: 未\n"
        "          font: gothic-bold\n"
        '          color: "ef4444"\n'
        '          outline: "4444ef"\n'
        "          animation: gatagata\n"
        "        - text: 着手\n"
        "          font: gothic-bold\n"
        '          color: "ef4444"\n'
        '          outline: "4444ef"\n'
        "          animation: gatagata\n",
        encoding="utf-8",
    )

    # Point prestamp at the fixture catalog via the --catalog flag so we
    # can run it in isolation without touching the repo's real catalog.
    proc = run_py(PRESTAMP, "未着手の対応", "--seed", "0", "--catalog", str(catalog))

    assert proc.returncode == 0
    # Two adjacent <img> tags for the two chunks, with proper URL encoding.
    assert "%E6%9C%AA" in proc.stdout  # 未
    assert "%E7%9D%80%E6%89%8B" in proc.stdout  # 着手
    assert proc.stdout.count('<img src="') == 2
    # The two imgs must be back-to-back (no separator between them).
    assert "><img src=" in proc.stdout


def test_compound_variant_uses_rotational_speed_slow() -> None:
    # Rotational animations (kaiten / kage_kaiten) must include speed: slow
    # in compound variants too (chunks share flavor, so the rotational
    # signal propagates to both chunks).
    out = _gen_term_yaml("緊急対応", variants=64)

    # Find variants whose animation is rotational
    rotational_variants = re.findall(
        r"chunks:\s+- text: [^\n]+\n\s+font: [^\n]+\n\s+color: [^\n]+\n(?:\s+outline: [^\n]+\n)?(?:\s+outline_width: [^\n]+\n)?\s+animation: (kaiten|kage_kaiten)\n\s+speed: (\w+)",
        out,
    )
    for animation, speed in rotational_variants:
        assert speed == "slow", f"{animation} variant must have speed: slow, got {speed}"


# ---------------------------------------------------------------------------
# Single-char catalog entries + boundary assertions (issue #52)
# ---------------------------------------------------------------------------


def _count_imgs(stdout: str) -> int:
    return stdout.count('align="absmiddle"')


def test_single_digit_does_not_stamp_inside_version_string() -> None:
    # `v1.2.3` — every digit is part of a version triple, all preceded
    # by ASCII letter or period, all followed by digit or period.
    proc = run_py(PRESTAMP, "v1.2.3", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_inside_unit_value() -> None:
    # `100ms` — digits are adjacent to other digits or ASCII letter.
    proc = run_py(PRESTAMP, "100ms", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_inside_hash_reference() -> None:
    # `#1234` — `1` preceded by `#` (not Japanese), `2`/`3`/`4` preceded
    # by digit. None pass the lookbehind/lookahead guards.
    proc = run_py(PRESTAMP, "#1234", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0, proc.stdout


def test_single_digit_does_not_stamp_with_only_whitespace_left_context() -> None:
    # `Step 1` — `1` preceded by space (with ASCII to the left of space).
    # The lookbehind requires Japanese char *immediately* before, so block.
    proc = run_py(PRESTAMP, "Step 1 として実装", "--seed", "1")

    assert proc.returncode == 0
    # 実装 stamps, but not `1`.
    assert _count_imgs(proc.stdout) == 1
    assert 'alt="実装"' in proc.stdout
    assert 'alt="1"' not in proc.stdout


def test_promise_all_does_not_stamp() -> None:
    # `Promise.all` has no catalog hits — verify nothing gets stamped
    # (regression guard against accidental ASCII catalog additions).
    proc = run_py(PRESTAMP, "Promise.all", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0


def test_single_digit_stamps_inside_japanese_flow() -> None:
    # `仕様変更1件` — `1` preceded by `更` (Han), followed by `件` (Han,
    # not in catalog). Both guards pass; `1` should stamp.
    proc = run_py(PRESTAMP, "仕様変更1件", "--seed", "1")

    assert proc.returncode == 0
    assert 'alt="1"' in proc.stdout
    # 仕様 and 変更 are 2-kanji multi entries, should also stamp.
    assert 'alt="仕様"' in proc.stdout
    assert 'alt="変更"' in proc.stdout


def test_single_kanji_blocked_when_preceded_by_han() -> None:
    # `先月` — `月` preceded by Han `先` (not in catalog). Block.
    proc = run_py(PRESTAMP, "先月", "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 0


def test_single_kanji_stamps_at_start_of_line() -> None:
    # `火曜の昼` — `火` at SOL (no preceding Han). The rule allows
    # Han to follow (so `火曜` still stamps the leading 火), since
    # the issue's intent is to surface the weekday glyph.
    proc = run_py(PRESTAMP, "火曜の昼", "--seed", "1")

    assert proc.returncode == 0
    assert 'alt="火"' in proc.stdout


def test_full_issue_acceptance_sentence() -> None:
    # The exact verification sentence from issue #52:
    #   "v1.2.3 で 100ms の修正を Step 1 として実装した。後で 火 にレビュー。"
    # Expectation: only 修正 / 実装 / 後 / 火 stamp.
    body = "v1.2.3 で 100ms の修正を Step 1 として実装した。後で 火 にレビュー。"
    proc = run_py(PRESTAMP, body, "--seed", "1")

    assert proc.returncode == 0
    assert _count_imgs(proc.stdout) == 4
    for term in ("修正", "実装", "後", "火"):
        assert f'alt="{term}"' in proc.stdout, f"expected stamp for {term}"
    # Negative — none of these substrings should appear as an alt.
    for plain in ('alt="1"', 'alt="2"', 'alt="3"', 'alt="0"'):
        assert plain not in proc.stdout, f"unexpected stamp: {plain}"


def test_generate_catalog_quotes_numeric_keys() -> None:
    # Bare `1:` parses as Integer in YAML, breaking prestamp.py's
    # Regexp.union over CATALOG.keys (expects String).
    proc = run_py(GENERATE, "1\n2\n", "--seed", "42", "--variants", "1")

    assert proc.returncode == 0
    assert '"1":' in proc.stdout
    assert '"2":' in proc.stdout
    # Non-numeric keys remain unquoted (regression guard).
    proc2 = run_py(GENERATE, "完成\n", "--seed", "42", "--variants", "1")
    assert proc2.returncode == 0
    assert "完成:" in proc2.stdout
    assert '"完成":' not in proc2.stdout


def test_catalog_loads_with_string_keys_for_digits() -> None:
    # End-to-end: after regeneration, the live catalog's digit entries
    # must be loadable as String keys by prestamp.py (no Integer keys
    # silently breaking lookups).
    import yaml

    catalog_path = REPO_ROOT / "skills" / "mojiemoji-github" / "data" / "prestamp-catalog.yml"
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    int_keys = [k for k in data["terms"].keys() if isinstance(k, int)]
    assert int_keys == [], f"integer keys leaked into catalog: {int_keys}"
