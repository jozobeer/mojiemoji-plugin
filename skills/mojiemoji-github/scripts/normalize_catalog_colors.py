#!/usr/bin/env python3
"""Rewrite forbidden hex colors in the prestamp / emoji catalogs.

Reads each catalog file as text (not via PyYAML — round-tripping
through a YAML emitter would reflow whitespace and rewrite comment
blocks the catalog relies on for human readability), then applies a
regex substitution over every quoted hex on `color:` / `outline:`
lines using the SSOT map in `mojiemoji.lib.forbidden_colors`.

Defaults to dry-run. Pass `--apply` to write back. The script is
idempotent — running it on an already-clean catalog produces no
changes and exits 0 with a "no changes" summary.

Exit codes:
  0 — no changes needed (catalog already clean) or `--apply` succeeded
  1 — dry-run found changes (CI guard mode — fail loud)
  2 — usage error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from lib.core_path import bundled_data_dir, ensure_core_importable

ensure_core_importable()

from mojiemoji.lib.forbidden_colors import FORBIDDEN_COLOR_REPLACEMENTS


DATA_DIR = bundled_data_dir()
DEFAULT_CATALOGS = (
    DATA_DIR / "prestamp-catalog.yml",
    DATA_DIR / "emoji-catalog.yml",
)


# Match a `color:` / `outline:` field with a quoted 6-digit hex value
# (with or without `#` prefix, any case). Captures: (1) field+prefix,
# (2) hex digits. Trailing `"` is matched outside the capture to keep
# substitution simple. The catalog uses double-quoted scalars
# uniformly — single-quote support added defensively.
HEX_FIELD_RE = re.compile(
    r"""(?P<head>(?:color|outline):\s*["']\#?)(?P<hex>[0-9a-fA-F]{6})(?P<tail>["'])"""
)


def _rewrite_text(text: str) -> tuple[str, int]:
    """Apply replacements. Returns (new_text, replacement_count)."""
    replacements = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal replacements
        key = m.group("hex").lower()
        if key in FORBIDDEN_COLOR_REPLACEMENTS:
            replacements += 1
            return m.group("head") + FORBIDDEN_COLOR_REPLACEMENTS[key] + m.group("tail")
        return m.group(0)

    return HEX_FIELD_RE.sub(repl, text), replacements


def _process(path: Path, apply: bool) -> int:
    """Returns replacement count for this file (0 = already clean)."""
    original = path.read_text(encoding="utf-8")
    new_text, count = _rewrite_text(original)
    if count == 0:
        print(f"  {path.name}: clean (0 forbidden colors)")
        return 0
    if apply:
        path.write_text(new_text, encoding="utf-8")
        print(f"  {path.name}: rewrote {count} forbidden colors")
    else:
        print(f"  {path.name}: WOULD rewrite {count} forbidden colors")
    return count


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write changes back to disk (default: dry-run).",
    )
    p.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help=(
            "Catalog files to process. Defaults to "
            "prestamp-catalog.yml + emoji-catalog.yml under the "
            "skill's data/ directory."
        ),
    )
    args = p.parse_args(argv)

    paths = args.paths or list(DEFAULT_CATALOGS)
    mode = "apply" if args.apply else "dry-run"
    print(f"normalize-catalog-colors [{mode}]")
    total = 0
    for path in paths:
        if not path.exists():
            print(f"  {path}: SKIP (not found)", file=sys.stderr)
            return 2
        total += _process(path, args.apply)

    if total == 0:
        print("All catalogs clean.")
        return 0
    if args.apply:
        print(f"Rewrote {total} forbidden colors across {len(paths)} catalog(s).")
        return 0
    print(
        f"Found {total} forbidden colors. Re-run with --apply to fix.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
