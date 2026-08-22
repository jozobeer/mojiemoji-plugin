"""Tests for prestamp.py masker behavior.

Safe-zone masking: inline code, fenced code, link targets, badge URLs,
existing `<img>` tags, `<details>/<summary>` headers, and the
backticked-`<summary>` regression that used to flip the state machine
silently. Covers term stamping at the prose layer.
"""

from __future__ import annotations

from conftest import PRESTAMP, run_py


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


def test_prestamp_does_not_flip_state_on_backticked_summary_tag() -> None:
    # `<summary>` inside inline code is documentation, not a real tag.
    # Regression: a backticked `<summary>` used to flip the state
    # machine and silently skip everything until a real `</summary>`
    # appeared, dropping all subsequent stamps. Two representative
    # shapes — `<summary>` alone and `<details>/<summary>` (the trickier
    # combo that defeats a naive lookbehind-on-backtick).
    body = (
        "前段で修正が走る。\n"
        "- 仕様は `<summary>` と同じ state machine で扱う。\n"
        "- `<details>/<summary>` の対応も同じ実装で扱う。\n"
        "- 末尾の確認も対応する。\n"
    )
    proc = run_py(PRESTAMP, body, "--seed", "9")

    assert proc.returncode == 0
    # All four lines have catalog-hit terms; none should be lost to the
    # phantom summary region.
    assert 'alt="修正"' in proc.stdout
    assert 'alt="仕様"' in proc.stdout
    assert 'alt="実装"' in proc.stdout
    assert 'alt="確認"' in proc.stdout
    # 対応 appears twice in the source.
    assert proc.stdout.count('alt="対応"') == 2
    # Backticked literals must round-trip intact.
    assert "`<summary>`" in proc.stdout
    assert "`<details>/<summary>`" in proc.stdout


def test_prestamp_skips_details_summary_but_stamps_details_body() -> None:
    body = "<details>\n<summary>修正方針</summary>\n本文は修正対象です。\n</details>\n"
    proc = run_py(PRESTAMP, body, "--seed", "2")

    assert proc.returncode == 0
    assert "<summary>修正方針</summary>" in proc.stdout
    assert 'align="absmiddle"' in proc.stdout
def test_prestamp_preserves_github_alert_markers() -> None:
    body = """> [!NOTE]
> この NOTE は本文です。修正をお願いします。

> [!WARNING]
> 警告の本文。
"""
    proc = run_py(PRESTAMP, body, "--seed", "5")

    assert proc.returncode == 0
    assert "> [!NOTE]" in proc.stdout
    assert "> [!WARNING]" in proc.stdout
