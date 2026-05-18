"""Internal decomposition of `hooks/mojiemoji_japanese_gate.py`.

Each submodule is independently importable for unit tests; the gate
script itself becomes a thin pipeline that wires them together.

Sibling `skills/.../scripts/lib/` is spliced onto `sys.path` here so
any `gate.*` module can `from lib.X import Y` and share constants
with the rest of the plugin. The gate script (`mojiemoji_japanese_gate.py`)
re-applies the same splice for self-contained subprocess execution;
having it here too lets test files import gate submodules directly
without replicating the path setup.
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
