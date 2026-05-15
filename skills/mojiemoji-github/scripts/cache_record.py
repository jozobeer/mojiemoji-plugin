#!/usr/bin/env python3
"""cache_record — append a JSON Lines usage entry to the local cache.

Invoked by mojiemoji-selector after rendering each snippet so the
deterministic bump_catalog can later promote high-frequency entries
into prestamp-catalog.yml.

Cache path resolution (first match wins):
  1. $MOJIEMOJI_CACHE_FILE
  2. ${XDG_DATA_HOME:-$HOME/.local/share}/mojiemoji-plugin/usage.jsonl

The parent directory is created on demand. Failures are reported on
stderr and exit 1 so the caller can decide whether to surface them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Color-shifting animations render their own per-frame colors, so the
# plugin contract allows omitting outline for these.
COLOR_SHIFT_ANIMATIONS = frozenset({"disco", "psycho", "kira"})


def default_cache_file() -> str:
    env_override = os.environ.get("MOJIEMOJI_CACHE_FILE")
    if env_override:
        return env_override
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return str(Path(data_home) / "mojiemoji-plugin" / "usage.jsonl")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append a usage JSONL record for later catalog promotion.",
        usage="cache_record.py --term TERM --font F --color C --animation A --outline O [opts]",
    )
    parser.add_argument("--term")
    parser.add_argument("--font")
    parser.add_argument("--color")
    parser.add_argument("--animation")
    parser.add_argument("--outline")
    parser.add_argument("--outline-width", dest="outline_width", default="2")
    parser.add_argument("--speed")
    parser.add_argument("--source", default="selector", help="selector | direct (default: selector)")
    parser.add_argument(
        "--file",
        dest="file",
        help="Override cache file path (otherwise $MOJIEMOJI_CACHE_FILE or XDG default)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    # Opt-out: users who do not want their selector usage recorded.
    if os.environ.get("MOJIEMOJI_CACHE_DISABLED", "").lower() in {"1", "true", "yes"}:
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)

    outline_required = args.animation not in COLOR_SHIFT_ANIMATIONS
    required = ["term", "font", "color", "animation"]
    if outline_required:
        required.append("outline")
    missing = [name for name in required if not getattr(args, name)]
    if missing:
        flags = ", ".join(f"--{name.replace('_', '-')}" for name in missing)
        print(f"missing required flag(s): {flags}", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    flavor: dict[str, str] = {
        "font": args.font,
        "color": args.color,
        "animation": args.animation,
    }
    if args.outline:
        flavor["outline"] = args.outline
        flavor["outline_width"] = args.outline_width
    if args.speed:
        flavor["speed"] = args.speed

    entry = {
        "term": args.term,
        "flavor": flavor,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": args.source,
    }

    cache_file = args.file or default_cache_file()
    try:
        Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"cache-record: failed to append to {cache_file}: {e}", file=sys.stderr)
        return 1

    print(cache_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
