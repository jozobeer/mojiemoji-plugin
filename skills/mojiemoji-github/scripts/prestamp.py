#!/usr/bin/env python3
"""prestamp — CLI shim that delegates to the ``prestamp`` package.

When invoked as ``python3 prestamp.py < input.md > output.md`` this file
runs as ``__main__`` and calls ``prestamp.cli.main``. Python's import
system resolves ``from prestamp.cli import main`` to the sibling
``prestamp/`` package (packages take precedence over same-name modules
in the same directory), so ``import prestamp`` likewise hits the
package — not this shim. Splitting the implementation into a package
(#102) kept this entry path stable so the CI drift check, the
``mojiemoji_md_edit_warn`` hook, and the ``coverage`` /
``generate_catalog`` scripts all continue to invoke ``prestamp.py`` by
its documented path without change.
"""

from __future__ import annotations

import sys

from prestamp.cli import main

if __name__ == "__main__":
    sys.exit(main())
