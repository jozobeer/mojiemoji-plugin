"""Splice the skill's `scripts/` directory onto sys.path.

Centralises the path injection that all hook submodules need to do
before `from lib.constants import ...` (or similar) can resolve to the
shared `skills/mojiemoji-github/scripts/lib/` package. Importing this
module is enough — the side effect happens at import time, exactly
once, idempotently.

Resolved against `__file__` so the hook works both when invoked by
Claude Code (from anywhere) and when invoked by tests via subprocess.
"""

from __future__ import annotations

import sys
from pathlib import Path


_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "skills" / "mojiemoji-github" / "scripts"
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
