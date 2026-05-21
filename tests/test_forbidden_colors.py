"""Tests for the catalog forbidden-color cleanup pipeline.

Covers three layers:

  1. `lib/forbidden_colors.normalize_color_value` — the small helper
     used both by `prestamp.py` (safety net) and the cleanup script.
  2. `scripts/normalize_catalog_colors.py` — the one-shot rewriter,
     verifying dry-run vs --apply and idempotency.
  3. The shipped catalogs — pin that no forbidden hex survives in
     either `prestamp-catalog.yml` or `emoji-catalog.yml`. This is
     the CI-equivalent assertion that fails the moment a regression
     slips in (in addition to the workflow guard).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"
CATALOG_DIR = REPO_ROOT / "skills" / "mojiemoji-github" / "data"
NORMALIZER = SCRIPTS_DIR / "normalize_catalog_colors.py"


@pytest.fixture(scope="module", autouse=True)
def _add_scripts_to_path() -> None:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.mark.parametrize(
    "value,expected",
    [
        # Forbidden 600s rewrite to 400s.
        ("dc2626", "f87171"),
        ("2563eb", "60a5fa"),
        ("16a34a", "4ade80"),
        # Case-insensitive and prefix-tolerant.
        ("DC2626", "f87171"),
        ("#dc2626", "f87171"),
        ("#DC2626", "f87171"),
        # Already-safe 400-series passes through unchanged.
        ("60a5fa", "60a5fa"),
        ("f87171", "f87171"),
        # None passes through (used over Optional fields).
        (None, None),
    ],
)
def test_normalize_color_value(value: str | None, expected: str | None) -> None:
    from lib.forbidden_colors import normalize_color_value

    assert normalize_color_value(value) == expected


def test_forbidden_map_covers_all_tailwind_600() -> None:
    """Every key must map to a value that itself is NOT forbidden — the
    replacement chain should converge in one step, not require a
    second pass."""
    from lib.forbidden_colors import FORBIDDEN_COLOR_REPLACEMENTS

    for key, replacement in FORBIDDEN_COLOR_REPLACEMENTS.items():
        assert key.lower() == key, f"keys must be lowercase: {key!r}"
        assert len(key) == 6, f"keys must be 6-digit hex: {key!r}"
        assert (
            replacement not in FORBIDDEN_COLOR_REPLACEMENTS
        ), f"replacement {replacement!r} for {key!r} is itself forbidden"


def test_shipped_catalogs_have_no_forbidden_colors() -> None:
    """SSOT assertion: every color/outline in both catalogs is safe.

    This is the dogfood guarantee — fails if anyone re-introduces a
    Tailwind 600+ color into the catalog without running the
    normalizer."""
    from lib.forbidden_colors import FORBIDDEN_COLOR_REPLACEMENTS

    def color_entries(value: object):
        if isinstance(value, dict):
            for field in ("color", "outline"):
                val = value.get(field)
                if isinstance(val, str):
                    yield field, val.lstrip("#").lower()
            for child in value.values():
                yield from color_entries(child)
        elif isinstance(value, list):
            for child in value:
                yield from color_entries(child)

    bad = []
    for path in [CATALOG_DIR / "prestamp-catalog.yml", CATALOG_DIR / "emoji-catalog.yml"]:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        top_key = "terms" if "prestamp" in path.name else "emojis"
        for term, variants in (data.get(top_key) or {}).items():
            for field, val in color_entries(variants or []):
                if val in FORBIDDEN_COLOR_REPLACEMENTS:
                    bad.append(f"{path.name}: {term} {field}={val}")
    assert not bad, "Forbidden colors found in catalog:\n  " + "\n  ".join(bad)


def test_normalizer_dry_run_on_clean_catalog_exits_0() -> None:
    """After #97 the shipped catalogs are clean — dry-run must report
    "clean" and exit 0, not 1."""
    result = subprocess.run(
        [sys.executable, str(NORMALIZER)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "clean" in result.stdout.lower()


def test_normalizer_rewrites_forbidden_hex_in_isolated_file(tmp_path: Path) -> None:
    fixture = tmp_path / "tiny-catalog.yml"
    fixture.write_text(
        "terms:\n"
        '  対応:\n'
        '    - color: "dc2626"\n'
        '      outline: "26dc26"\n'
        '    - color: "2563eb"\n'
        '      outline: "eb2563"\n',
        encoding="utf-8",
    )
    # Dry-run reports the count and exits 1.
    dry = subprocess.run(
        [sys.executable, str(NORMALIZER), str(fixture)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert dry.returncode == 1, dry.stderr
    assert "WOULD rewrite 2" in dry.stdout
    # Apply rewrites both hits and exits 0.
    applied = subprocess.run(
        [sys.executable, str(NORMALIZER), "--apply", str(fixture)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert applied.returncode == 0, applied.stderr
    new_text = fixture.read_text(encoding="utf-8")
    assert "dc2626" not in new_text
    assert "2563eb" not in new_text
    assert "f87171" in new_text  # red-600 → red-400
    assert "60a5fa" in new_text  # blue-600 → blue-400
    # Outline fields (already-safe color-flipped hexes) untouched.
    assert "26dc26" in new_text
    assert "eb2563" in new_text


def test_normalizer_is_idempotent(tmp_path: Path) -> None:
    """Running --apply twice on the same file makes no further changes
    on the second run — the second invocation reports clean."""
    fixture = tmp_path / "tiny-catalog.yml"
    fixture.write_text(
        'terms:\n  対応:\n    - color: "dc2626"\n      outline: "26dc26"\n',
        encoding="utf-8",
    )
    first = subprocess.run(
        [sys.executable, str(NORMALIZER), "--apply", str(fixture)],
        capture_output=True, text=True, timeout=10,
    )
    assert first.returncode == 0
    snapshot = fixture.read_text(encoding="utf-8")
    second = subprocess.run(
        [sys.executable, str(NORMALIZER), "--apply", str(fixture)],
        capture_output=True, text=True, timeout=10,
    )
    assert second.returncode == 0
    assert "clean" in second.stdout.lower()
    assert fixture.read_text(encoding="utf-8") == snapshot
