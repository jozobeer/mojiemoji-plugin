"""Make the ``mojiemoji`` core package importable from a plugin checkout.

The core (catalog loading, the prestamp passes, the renderer) was carved
out into a standalone distribution so it can be installed from an index,
but the plugin still has to run as bare scripts: Claude Code invokes the
hook and the skill scripts with whatever ``python3`` it finds, in a
checkout with nothing installed. So a published wheel cannot be assumed,
and the bundled sources under ``packages/mojiemoji-core/src`` are the
fallback.

Resolution order — an installed distribution always wins, so a user who
upgraded the core gets the upgrade instead of the vendored copy.

`bundled_data_dir` is the deliberate exception. The catalog-maintenance
scripts edit the catalogs *as repository sources*; pointing them at an
installed copy would have them rewrite files under `site-packages` that
no commit will ever capture, so they always resolve the checkout.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# <root>/skills/mojiemoji-github/scripts/lib/core_path.py → <root>
_REPO_ROOT = Path(__file__).resolve().parents[4]
_BUNDLED_SRC = _REPO_ROOT / "packages" / "mojiemoji-core" / "src"


def ensure_core_importable() -> None:
    """Splice the bundled core onto ``sys.path`` unless one is installed.

    Idempotent: safe to call from every entry point, and callers need not
    coordinate on who calls it first.
    """
    if importlib.util.find_spec("mojiemoji") is not None:
        return
    path = str(_BUNDLED_SRC)
    if path not in sys.path:
        sys.path.append(path)


def bundled_data_dir() -> Path:
    """Directory of the catalogs as checked-in sources, for tools that edit them."""
    return _BUNDLED_SRC / "mojiemoji" / "data"
