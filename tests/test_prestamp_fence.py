"""Tests for prestamp.py CommonMark fence detection.

Indented fences, tilde fences, and nested fence markers must all be
recognized so terms / emoji inside them are preserved verbatim. A
shorter inner ``` must NOT close an outer ```` block.
"""

from __future__ import annotations

from conftest import PRESTAMP, run_py


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
