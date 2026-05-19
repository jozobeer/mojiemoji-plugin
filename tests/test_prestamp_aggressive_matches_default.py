"""Golden parity: default CLI and explicit --intensity aggressive match legacy output."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import PRESTAMP, run_py

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "intensity" / "aggressive"
CASES = ["short", "long", "table", "code", "off_block"]


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("extra_args", [[], ["--intensity", "aggressive"]])
def test_aggressive_matches_golden(name: str, extra_args: list[str]) -> None:
    inp = (FIXTURE_DIR / f"{name}.md.in").read_text(encoding="utf-8")
    expected = (FIXTURE_DIR / f"{name}.md.out").read_text(encoding="utf-8")
    proc = run_py(PRESTAMP, inp, *extra_args)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == expected
