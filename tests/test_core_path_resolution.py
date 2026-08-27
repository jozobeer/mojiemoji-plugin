"""How plugin entry points resolve the `mojiemoji` core.

The plugin ships the core it was tested against and imports APIs from
that exact version. An older `mojiemoji` in `site-packages` shadowing the
bundled copy therefore breaks the plugin at the import that needs the
newer API — and a bare plugin checkout can neither constrain nor upgrade
that installation.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

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


def _import_core_path_module():
    """Import `lib.core_path` in-process, for monkeypatching its internals.

    The probe above runs out of process on purpose (it asserts on a real
    `sys.path` mutation); the tier-3 self-heal below is the opposite case —
    it must never actually spawn a subprocess, so the module is imported
    in-process and `os.execvp` / `shutil.which` / `find_spec` are stubbed.
    """
    import importlib

    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module("lib.core_path")


class TestUvSelfHealTier:
    """Tier 3 (#162): re-exec under uv when skill dir is installed alone.

    A skill directory copied on its own (e.g. via `npx skills add`) carries
    neither the bundled `packages/mojiemoji-core/src` (that lives in the
    plugin repository) nor an installed `mojiemoji` distribution. Every
    case below stubs `os.execvp` so a bug here cannot actually spawn `uv`.
    """

    @pytest.fixture(autouse=True)
    def _clean_reexec_guard(self, mod):
        # `ensure_core_importable` sets this directly on `os.environ` (it
        # has to survive into the re-exec'd child), so `monkeypatch` never
        # sees the write and cannot revert it automatically.
        yield
        os.environ.pop(mod._REEXEC_GUARD_ENV, None)

    @pytest.fixture()
    def mod(self):
        return _import_core_path_module()

    def test_bundled_present_skips_reexec(self, mod, monkeypatch):
        calls = []
        monkeypatch.setattr(mod.os, "execvp", lambda *a, **kw: calls.append((a, kw)))
        # Bundled sources are real in this checkout; tier 1 must win before
        # tier 2/3 are even consulted.
        mod.ensure_core_importable()
        assert calls == []

    def test_installed_distribution_skips_reexec(self, mod, monkeypatch, tmp_path):
        monkeypatch.setattr(mod, "_BUNDLED_SRC", tmp_path / "no-bundled-src")
        monkeypatch.setattr(mod.importlib.util, "find_spec", lambda name: object())
        calls = []
        monkeypatch.setattr(mod.os, "execvp", lambda *a, **kw: calls.append((a, kw)))

        mod.ensure_core_importable()

        assert calls == []

    def test_neither_available_reexecs_uv_with_expected_argv(self, mod, monkeypatch, tmp_path):
        monkeypatch.setattr(mod, "_BUNDLED_SRC", tmp_path / "no-bundled-src")
        monkeypatch.setattr(mod.importlib.util, "find_spec", lambda name: None)
        monkeypatch.setattr(mod.shutil, "which", lambda name: "/opt/homebrew/bin/uv")
        monkeypatch.delenv(mod._REEXEC_GUARD_ENV, raising=False)
        monkeypatch.delenv(mod.CORE_SPEC_ENV, raising=False)
        monkeypatch.setattr(sys, "argv", ["/tmp/x/mojiemoji-github/scripts/prestamp.py", "--surface", "issue-body"])
        calls = []
        monkeypatch.setattr(mod.os, "execvp", lambda file, args: calls.append((file, args)))

        mod.ensure_core_importable()

        assert calls == [(
            "uv",
            [
                "uv", "run", "--no-project", "--with", "mojiemoji", "python",
                "/tmp/x/mojiemoji-github/scripts/prestamp.py", "--surface", "issue-body",
            ],
        )]
        assert os.environ[mod._REEXEC_GUARD_ENV] == "1"

    def test_core_spec_env_pins_the_with_argument(self, mod, monkeypatch, tmp_path):
        monkeypatch.setattr(mod, "_BUNDLED_SRC", tmp_path / "no-bundled-src")
        monkeypatch.setattr(mod.importlib.util, "find_spec", lambda name: None)
        monkeypatch.setattr(mod.shutil, "which", lambda name: "/opt/homebrew/bin/uv")
        monkeypatch.delenv(mod._REEXEC_GUARD_ENV, raising=False)
        monkeypatch.setenv(mod.CORE_SPEC_ENV, "mojiemoji==0.1.0")
        monkeypatch.setattr(sys, "argv", ["/tmp/x/prestamp.py"])
        calls = []
        monkeypatch.setattr(mod.os, "execvp", lambda file, args: calls.append((file, args)))

        mod.ensure_core_importable()

        assert calls[0][1] == [
            "uv", "run", "--no-project", "--with", "mojiemoji==0.1.0", "python",
            "/tmp/x/prestamp.py",
        ]

    def test_recursion_guard_already_set_raises_system_exit(self, mod, monkeypatch, tmp_path):
        monkeypatch.setattr(mod, "_BUNDLED_SRC", tmp_path / "no-bundled-src")
        monkeypatch.setattr(mod.importlib.util, "find_spec", lambda name: None)
        monkeypatch.setenv(mod._REEXEC_GUARD_ENV, "1")
        calls = []
        monkeypatch.setattr(mod.os, "execvp", lambda *a, **kw: calls.append((a, kw)))

        with pytest.raises(SystemExit) as exc_info:
            mod.ensure_core_importable()

        assert calls == []
        assert "uv run" in str(exc_info.value)

    def test_no_uv_on_path_raises_mentioning_uv(self, mod, monkeypatch, tmp_path):
        monkeypatch.setattr(mod, "_BUNDLED_SRC", tmp_path / "no-bundled-src")
        monkeypatch.setattr(mod.importlib.util, "find_spec", lambda name: None)
        monkeypatch.delenv(mod._REEXEC_GUARD_ENV, raising=False)
        monkeypatch.setattr(mod.shutil, "which", lambda name: None)
        calls = []
        monkeypatch.setattr(mod.os, "execvp", lambda *a, **kw: calls.append((a, kw)))

        with pytest.raises(SystemExit) as exc_info:
            mod.ensure_core_importable()

        assert calls == []
        assert "uv" in str(exc_info.value)
        assert "mojiemoji" in str(exc_info.value)
