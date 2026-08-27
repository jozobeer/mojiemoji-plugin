#!/usr/bin/env python3
"""mojiemoji_markdown — entry point over ``mojiemoji.markdown``.

The single-phrase URL builder moved into the ``mojiemoji`` core, but its
path here is quoted verbatim in places that cannot be updated by editing
this repository alone: the hook's remediation text, the selector agent's
instructions, and the per-harness SKILL.md files that tell other agents
how to invoke it. Keeping the file where it has always been is what lets
the carve-out land without invalidating any of them.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.core_path import ensure_core_importable  # noqa: E402

ensure_core_importable()

from mojiemoji.markdown import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
