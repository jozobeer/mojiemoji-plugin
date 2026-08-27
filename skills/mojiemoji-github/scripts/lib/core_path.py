"""Make the ``mojiemoji`` core package importable from a plugin checkout.

The core (catalog loading, the prestamp passes, the renderer) was carved
out into a standalone distribution so it can be installed from an index,
but the plugin still has to run as bare scripts: Claude Code invokes the
hook and the skill scripts with whatever ``python3`` it finds, in a
checkout with nothing installed. So a published wheel cannot be assumed,
and the bundled sources under ``packages/mojiemoji-core/src`` are the
fallback.

Resolution order — three tiers, tried in order:

1. Bundled sources win whenever they are present. The plugin ships the
   core it was tested against, and its scripts import APIs from that
   exact version; an older global installation shadowing it breaks the
   plugin at the import that needs the newer API, and a bare plugin
   checkout has no way to constrain or upgrade that installation.
2. Where no bundled copy exists but ``mojiemoji`` is already importable
   (an installed distribution), that installation is used as-is — no
   ``sys.path`` surgery needed, since the normal import machinery already
   finds it.
3. Where neither is true, this process re-execs itself under
   ``uv run --with mojiemoji`` so ``uv`` resolves the published
   distribution on the fly. This tier exists because a skill directory
   can be installed on its own — e.g. via ``npx skills add`` — carrying
   neither the bundled sources (those live in the plugin repository, not
   the skill payload) nor an installed distribution (nothing installs
   dependencies for a bare skill drop). Without this tier, every script
   in that environment fails at import with
   ``ModuleNotFoundError: No module named 'mojiemoji'``.

`bundled_data_dir` is the deliberate exception. The catalog-maintenance
scripts edit the catalogs *as repository sources*; pointing them at an
installed copy would have them rewrite files under `site-packages` that
no commit will ever capture, so they always resolve the checkout.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

# <root>/skills/mojiemoji-github/scripts/lib/core_path.py → <root>
_REPO_ROOT = Path(__file__).resolve().parents[4]
_BUNDLED_SRC = _REPO_ROOT / "packages" / "mojiemoji-core" / "src"

# Env var pinning the distribution spec `uv run --with` installs, so users
# can pin an exact release (e.g. "mojiemoji==0.1.0") instead of always
# floating to latest.
CORE_SPEC_ENV = "MOJIEMOJI_CORE_SPEC"
_DEFAULT_CORE_SPEC = "mojiemoji"

# Set on the re-exec'd child so a second failed attempt raises instead of
# looping: if `uv run --with mojiemoji` still leaves the core unimportable,
# retrying the same re-exec cannot fix that.
_REEXEC_GUARD_ENV = "MOJIEMOJI_CORE_REEXEC"


def ensure_core_importable() -> None:
    """Make ``mojiemoji`` importable, trying bundled, installed, then uv.

    Position, not mere presence, is what decides tier 1: an entry sitting
    on the tail of ``sys.path`` still loses to a distribution in
    ``site-packages``, and an editable install puts this very directory
    there. So the entry is moved to the front rather than skipped when
    already present. The directory is a src-layout root holding only
    ``mojiemoji``, so it shadows nothing else.

    Idempotent: safe to call from every entry point, and callers need not
    coordinate on who calls it first. Tier 3 replaces the process
    (``os.execvp``), so a caller that reaches tier 3 and returns normally
    means tier 3 was not needed after all.
    """
    if _BUNDLED_SRC.is_dir():
        path = str(_BUNDLED_SRC)
        if sys.path[:1] == [path]:
            return
        while path in sys.path:
            sys.path.remove(path)
        sys.path.insert(0, path)
        return

    if importlib.util.find_spec("mojiemoji") is not None:
        return

    _reexec_under_uv()


def bundled_data_dir() -> Path:
    """Directory of the catalogs as checked-in sources, for tools that edit them."""
    return _BUNDLED_SRC / "mojiemoji" / "data"


def _reexec_under_uv() -> None:
    """Re-exec this process under ``uv run --with <spec>`` and never return.

    Raises ``SystemExit`` instead when re-exec cannot work: the guard is
    already set (a prior re-exec did not yield an importable core) or
    ``uv`` is not on PATH.
    """
    if os.environ.get(_REEXEC_GUARD_ENV) == "1":
        raise SystemExit(
            "mojiemoji core is still not importable after re-executing under "
            "`uv run --no-project --with mojiemoji`. This usually means uv "
            "could not resolve the package — check network access, or that "
            f"{CORE_SPEC_ENV} (if set) names a valid distribution spec. "
            "Install the `mojiemoji` distribution into this interpreter "
            "directly as a workaround (`python3 -m pip install mojiemoji`)."
        )

    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit(
            "mojiemoji core is not importable, and this environment has "
            "neither the bundled plugin sources nor an installed `mojiemoji` "
            "distribution — this looks like a skill directory installed on "
            "its own (e.g. via `npx skills add`), which carries neither. "
            "Install uv (https://docs.astral.sh/uv/) so this script can "
            "self-heal via `uv run --with mojiemoji`, or install the "
            "`mojiemoji` distribution into this interpreter directly "
            "(`python3 -m pip install mojiemoji`)."
        )

    spec = os.environ.get(CORE_SPEC_ENV, _DEFAULT_CORE_SPEC)
    os.environ[_REEXEC_GUARD_ENV] = "1"
    os.execvp(
        "uv",
        ["uv", "run", "--no-project", "--with", spec, "python", sys.argv[0], *sys.argv[1:]],
    )
