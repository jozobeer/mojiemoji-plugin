"""Console entry point for the ``mojiemoji`` command.

Declared as ``[project.scripts] mojiemoji`` so an installed wheel — or
``uvx mojiemoji`` — runs the same stdin-to-stdout transform the
repository exposes through ``prestamp.py``.
"""

from __future__ import annotations

import sys

from mojiemoji.prestamp.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())
