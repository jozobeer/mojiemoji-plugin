"""Tests for the release guards' version tooling.

`read-version.py` and `semver.py` decide whether a merge publishes, so
their failure modes are silent by construction: a version read wrong, or
compared wrong, does not raise anywhere — it just lets the wrong thing
ship (or refuses the right one).
"""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
READ_VERSION = REPO_ROOT / "scripts" / "read-version.py"
SEMVER = REPO_ROOT / "scripts" / "semver.py"
BUMP_CATALOG = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "bump_catalog.py"


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=10,
    )


class TestReadVersion:
    def test_reads_the_plugin_manifest(self):
        proc = run(READ_VERSION, ".claude-plugin/plugin.json")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip()

    def test_reads_the_core_pyproject_without_a_toml_parser(self):
        """3.10 has no `tomllib`, and the guards run with nothing installed."""
        proc = run(READ_VERSION, "packages/mojiemoji-core/pyproject.toml")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip()

    def test_ignores_a_version_under_another_table(self, tmp_path: Path):
        toml = tmp_path / "pyproject.toml"
        toml.write_text(
            '[tool.other]\nversion = "9.9.9"\n\n[project]\nversion = "1.2.3"\n',
            encoding="utf-8",
        )
        proc = run(READ_VERSION, str(toml))
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "1.2.3"

    def test_absent_at_ref_exits_3(self):
        proc = run(READ_VERSION, "no/such/file.toml")
        assert proc.returncode == 3

    def test_malformed_file_exits_2_not_traceback(self, tmp_path: Path):
        toml = tmp_path / "pyproject.toml"
        toml.write_text("[project]\nname = \"x\"\n", encoding="utf-8")
        proc = run(READ_VERSION, str(toml))
        assert proc.returncode == 2
        assert "Traceback" not in proc.stderr


class TestSemver:
    @pytest.mark.parametrize("version", ["0.1.0", "1.0.0-rc.1", "1.0.0+build.1"])
    def test_accepts_well_formed(self, version):
        assert run(SEMVER, "validate", version).returncode == 0

    @pytest.mark.parametrize("version", ["01.2.3", "1.2", "1.2.3-", "v1.2.3"])
    def test_rejects_malformed(self, version):
        assert run(SEMVER, "validate", version).returncode == 1

    @pytest.mark.parametrize(
        ("left", "right", "expected"),
        [
            ("0.25.0", "0.24.28", "1"),
            ("0.24.28", "0.25.0", "-1"),
            ("0.25.0", "0.25.0", "0"),
            # A prerelease sorts below the release it precedes.
            ("1.0.0", "1.0.0-rc.1", "1"),
            ("1.0.0-rc.1", "1.0.0-rc.2", "-1"),
            ("1.0.0-alpha", "1.0.0-alpha.1", "-1"),
            # Build metadata is ignored in precedence.
            ("1.0.0+b1", "1.0.0+b2", "0"),
        ],
    )
    def test_precedence(self, left, right, expected):
        proc = run(SEMVER, "compare", left, right)
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == expected

    def test_compare_rejects_malformed(self):
        assert run(SEMVER, "compare", "1.0", "1.0.0").returncode == 1


class TestPatchBump:
    """`bump_catalog.py --pr` must emit a version the guard accepts."""

    @staticmethod
    def patch_bump(version: str):
        sys.path.insert(0, str(BUMP_CATALOG.parent))
        try:
            module = runpy.run_path(str(BUMP_CATALOG))
        finally:
            sys.path.pop(0)
        return module["patch_bump"](version)

    @pytest.mark.parametrize(
        ("version", "expected"),
        [
            ("0.1.0", "0.1.1"),
            ("1.2.9", "1.2.10"),
            # Splitting on every dot read this as four components and
            # produced `0.2.1.1`, which the version guard then rejected.
            ("0.2.0-rc.1", "0.2.1-rc.1"),
            ("0.2.0+build.5", "0.2.1+build.5"),
        ],
    )
    def test_bumps_only_the_patch_component(self, version, expected):
        assert self.patch_bump(version) == expected

    def test_refuses_a_non_semver_version(self):
        assert self.patch_bump("1.2") is None
