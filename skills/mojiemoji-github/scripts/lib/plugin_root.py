"""Resolve the plugin root for remediation messages (#147).

Claude Code injects ``CLAUDE_PLUGIN_ROOT`` into hook subprocesses but NOT
into the interactive Bash tool environment, so remediation text that asks
the agent to run a command must embed the *resolved* absolute path — a
literal ``${CLAUDE_PLUGIN_ROOT}`` expands to nothing where the agent runs
it, and every guided command degrades to ``/skills/...``.

Lives in ``lib`` (not ``hooks/gate``) so both the package-context import
and the standalone ``spec_from_file_location`` loading used by tests
resolve it the same way as every other ``from lib.X import Y``.
"""
from __future__ import annotations

import os
from pathlib import Path


def plugin_root() -> str:
    """Absolute plugin root: env when injected, else derived from __file__."""
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return env.rstrip("/")
    # <root>/skills/mojiemoji-github/scripts/lib/plugin_root.py → <root>
    return str(Path(__file__).resolve().parents[4])
