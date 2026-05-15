#!/usr/bin/env python3
"""cache_stats — emit promotion candidates from the usage JSONL cache.

A "candidate" is a unique (term, flavor) pair whose occurrence count is
at least --threshold across the cache. Identical flavors are
deduplicated. Output is a YAML fragment compatible with the
`terms:` block of prestamp-catalog.yml:

    <term>:
      - font: <font>
        color: "<hex>"
        outline: "<hex|directive>"
        outline_width: "2"
        animation: <animation>
        [speed: <speed>]

Malformed JSONL lines are skipped with a stderr notice.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


def default_cache_file() -> str:
    env_override = os.environ.get("MOJIEMOJI_CACHE_FILE")
    if env_override:
        return env_override
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return str(Path(data_home) / "mojiemoji-plugin" / "usage.jsonl")


_IDENT_RE = re.compile(r"\A[a-zA-Z][a-zA-Z0-9_]*\Z")
_HEX6_RE = re.compile(r"\A[0-9a-f]{6}\Z")
_LEADING_DIGIT_RE = re.compile(r"\A\d")


def yaml_value(value: object) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    s = str(value)
    if _IDENT_RE.match(s) and not _LEADING_DIGIT_RE.match(s) and not _HEX6_RE.match(s):
        return s
    return f'"{s}"'


def yaml_term_key(term: str) -> str:
    """Always quote — term keys may contain YAML-significant characters
    (`:`, `>`, `#`, leading symbols, etc.)."""
    escaped = str(term).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def aggregate(cache_path: Path, threshold: int) -> tuple[dict[str, list[dict]], int]:
    """Return (candidates_by_term, skipped_malformed_lines)."""
    counts: dict[tuple[str, tuple], dict] = {}
    skipped = 0

    with open(cache_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            term = entry.get("term")
            flavor = entry.get("flavor")
            if not isinstance(term, str) or not isinstance(flavor, dict):
                continue
            fingerprint = (
                flavor.get("font"),
                flavor.get("color"),
                flavor.get("animation"),
                flavor.get("outline"),
                flavor.get("outline_width"),
                flavor.get("speed"),
            )
            key = (term, fingerprint)
            bucket = counts.setdefault(key, {"flavor": flavor, "count": 0})
            bucket["count"] += 1

    candidates: dict[str, list[dict]] = {}
    for (term, _fingerprint), bucket in counts.items():
        if bucket["count"] >= threshold:
            candidates.setdefault(term, []).append(bucket["flavor"])
    return candidates, skipped


def render(candidates: dict[str, list[dict]]) -> str:
    out = []
    for term in sorted(candidates.keys()):
        out.append(f"  {yaml_term_key(term)}:")
        for flavor in candidates[term]:
            out.append(f"    - font: {flavor['font']}")
            out.append(f"      color: {yaml_value(flavor['color'])}")
            if flavor.get("outline"):
                out.append(f"      outline: {yaml_value(flavor['outline'])}")
            if flavor.get("outline_width"):
                out.append(f"      outline_width: {yaml_value(flavor['outline_width'])}")
            out.append(f"      animation: {flavor['animation']}")
            if flavor.get("speed"):
                out.append(f"      speed: {flavor['speed']}")
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit promotion candidates from the usage JSONL cache.",
        usage="cache_stats.py [--file PATH] [--threshold N]",
    )
    parser.add_argument(
        "--file",
        help="JSONL cache file (default: $MOJIEMOJI_CACHE_FILE or XDG default)",
    )
    parser.add_argument("--threshold", type=int, default=2,
                        help="Minimum occurrence per (term, flavor) (default 2)")
    args = parser.parse_args(argv)

    cache_path = Path(args.file or default_cache_file())
    if not cache_path.is_file():
        return 0

    candidates, skipped = aggregate(cache_path, args.threshold)
    if skipped:
        print(f"cache-stats: skipped {skipped} malformed line(s)", file=sys.stderr)
    if not candidates:
        return 0

    print(render(candidates))
    return 0


if __name__ == "__main__":
    sys.exit(main())
