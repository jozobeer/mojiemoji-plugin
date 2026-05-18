"""Tests for prestamp.py's forbidden-color safety net.

Catalog entries still carry some Tailwind 600+ values (e.g. db2777 /
2563eb / ca8a04) which are unreadable on GitHub's dark theme. The
render layer must downgrade them to the matching 400-series so output
ships safe regardless of catalog state.
"""

from __future__ import annotations

from conftest import PRESTAMP, run_py


def test_prestamp_normalizes_tailwind_600_colors_in_output() -> None:
    proc = run_py(PRESTAMP, "修正の確認、対応も含めて全体の構造。\n", "--seed", "9")

    assert proc.returncode == 0
    forbidden = (
        "color=ca8a04", "color=16a34a", "color=dc2626", "color=2563eb",
        "color=7c3aed", "color=db2777", "color=0891b2", "color=d97706",
        "color=ea580c", "color=525252",
    )
    for needle in forbidden:
        assert needle not in proc.stdout, f"{needle} should be normalized away"
