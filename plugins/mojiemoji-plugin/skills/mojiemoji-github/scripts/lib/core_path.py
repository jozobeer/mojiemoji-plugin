"""Make the ``mojiemoji`` core package importable from a plugin checkout.

The core (catalog loading, the prestamp passes, the renderer) was carved
out into a standalone distribution so it can be installed from an index,
but the plugin still has to run as bare scripts: Claude Code invokes the
hook and the skill scripts with whatever ``python3`` it finds, in a
checkout with nothing installed. So a published wheel cannot be assumed,
and the bundled sources under ``packages/mojiemoji-core/src`` are the
fallback.

Resolution order — the bundled sources win whenever they are present.
The plugin ships the core it was tested against, and its scripts import
APIs from that exact version; an older global installation shadowing it
breaks the plugin at the import that needs the newer API, and a bare
plugin checkout has no way to constrain or upgrade that installation.
Where no bundled copy exists (an installed plugin payload without the
vendored sources) the installed distribution is used, as before.

`bundled_data_dir` is the deliberate exception. The catalog-maintenance
scripts edit the catalogs *as repository sources*; pointing them at an
installed copy would have them rewrite files under `site-packages` that
no commit will ever capture, so they always resolve the checkout.
"""
from __future__ import annotations

import sys
from pathlib import Path

# <root>/skills/mojiemoji-github/scripts/lib/core_path.py → <root>
_REPO_ROOT = Path(__file__).resolve().parents[4]
_BUNDLED_SRC = _REPO_ROOT / "packages" / "mojiemoji-core" / "src"


def ensure_core_importable() -> None:
    """Put the bundled core ahead of anything installed, when it exists.

    Position, not mere presence, is what decides: an entry sitting on the
    tail of ``sys.path`` still loses to a distribution in
    ``site-packages``, and an editable install puts this very directory
    there. So the entry is moved to the front rather than skipped when
    already present. The directory is a src-layout root holding only
    ``mojiemoji``, so it shadows nothing else.

    Idempotent: safe to call from every entry point, and callers need not
    coordinate on who calls it first.
    """
    if not _BUNDLED_SRC.is_dir():
        return
    path = str(_BUNDLED_SRC)
    if sys.path[:1] == [path]:
        return
    while path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)


def bundled_data_dir() -> Path:
    """Directory of the catalogs as checked-in sources, for tools that edit them."""
    return _BUNDLED_SRC / "mojiemoji" / "data"
