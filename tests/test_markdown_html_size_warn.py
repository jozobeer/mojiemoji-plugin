"""Tests for intrinsic-size stderr warning when `--html` omits dimensions.

Issue #136: warn when `--html` is used without `--height` and `--width`.
`--inline` expands to a fixed height before the HTML branch, so it stays silent.
"""

from __future__ import annotations

from pathlib import Path

from conftest import run_py


REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_SCRIPT = REPO_ROOT / "skills/mojiemoji-github/scripts/mojiemoji_markdown.py"


def test_html_without_dimensions_warns_intrinsic_size() -> None:
    proc = run_py(MARKDOWN_SCRIPT, "", "--text", "hi", "--html")
    assert proc.returncode == 0
    assert "intrinsic size" in proc.stderr


def test_inline_emits_no_intrinsic_size_warning() -> None:
    proc = run_py(MARKDOWN_SCRIPT, "", "--text", "hi", "--inline")
    assert proc.returncode == 0
    assert "intrinsic size" not in proc.stderr


def test_html_with_height_emits_no_intrinsic_size_warning() -> None:
    proc = run_py(MARKDOWN_SCRIPT, "", "--text", "hi", "--html", "--height", "20")
    assert proc.returncode == 0
    assert "intrinsic size" not in proc.stderr


def test_html_with_width_emits_no_intrinsic_size_warning() -> None:
    proc = run_py(MARKDOWN_SCRIPT, "", "--text", "hi", "--html", "--width", "20")
    assert proc.returncode == 0
    assert "intrinsic size" not in proc.stderr


def test_markdown_mode_emits_no_intrinsic_size_warning() -> None:
    proc = run_py(MARKDOWN_SCRIPT, "", "--text", "hi")
    assert proc.returncode == 0
    assert "intrinsic size" not in proc.stderr


def test_html_without_dimensions_stdout_is_plain_img_without_dimensions() -> None:
    proc = run_py(MARKDOWN_SCRIPT, "", "--text", "hi", "--html")
    assert proc.returncode == 0
    expected = (
        '<img src="https://mojiemoji.jozo.beer/emoji/hi?background=transparent" '
        'alt="hi">'
    )
    assert proc.stdout.rstrip("\n") == expected
    assert 'height="' not in proc.stdout
    assert 'width="' not in proc.stdout
