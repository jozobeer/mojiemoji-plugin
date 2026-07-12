"""Resolve the local usage-cache file path.

Order of precedence (first match wins):
  1. $MOJIEMOJI_CACHE_FILE
  2. ${XDG_DATA_HOME:-$HOME/.local/share}/mojiemoji-plugin/usage.jsonl

Previously copy-pasted across `bump_catalog`, `cache_record`, and
`cache_stats`; resolving env-var rename (#50) used to require three
synchronous edits.
"""

from __future__ import annotations

import os
from pathlib import Path


def default_cache_file() -> str:
    env_override = os.environ.get("MOJIEMOJI_CACHE_FILE")
    if env_override:
        return env_override
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return str(Path(data_home) / "mojiemoji-plugin" / "usage.jsonl")
