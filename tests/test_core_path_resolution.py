"""How plugin entry points resolve the `mojiemoji` core.

The plugin ships the core it was tested against and imports APIs from
that exact version. An older `mojiemoji` in `site-packages` shadowing the
bundled copy therefore breaks the plugin at the import that needs the
newer API — and a bare plugin checkout can neither constrain nor upgrade
that installation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"
BUNDLED_SRC = REPO_ROOT / "packages" / "mojiemoji-core" / "src"

# Run out of process: the bootstrap mutates `sys.path` by design, and the
# assertion is about that mutation's position.
PROBE = f"""
import sys
sys.path.insert(0, {str(SCRIPTS)!r})
from lib.core_path import ensure_core_importable
ensure_core_importable()
print(sys.path.index({str(BUNDLED_SRC)!r}))
print("\\n".join(sys.path))
"""


def run_probe() -> tuple[int, list[str]]:
    proc = subprocess.run(
        [sys.executable, "-c", PROBE],
        capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    index, _, rest = proc.stdout.partition("\n")
    return int(index), rest.splitlines()


def test_bundled_core_precedes_every_installed_location() -> None:
    index, path_entries = run_probe()
    installed = [
        i for i, entry in enumerate(path_entries)
        if "site-packages" in entry or "dist-packages" in entry
    ]
    assert installed, "probe env has no site-packages; the test proves nothing"
    assert index < min(installed)


def test_bootstrap_is_idempotent() -> None:
    """Every entry point calls it; none of them coordinate on who is first."""
    index, path_entries = run_probe()
    assert path_entries.count(str(BUNDLED_SRC)) == 1
    assert index == 0
