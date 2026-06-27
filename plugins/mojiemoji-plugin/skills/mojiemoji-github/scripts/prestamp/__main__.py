"""Enable ``python3 -m prestamp`` invocation alongside the
``python3 prestamp.py`` script entry. Both routes call the same
``cli.main`` so behavior is identical.
"""

from __future__ import annotations

import sys

from prestamp.cli import main

if __name__ == "__main__":
    sys.exit(main())
