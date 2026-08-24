"""What the published distribution has to keep true.

These tests exist because the carve-out's failure modes are invisible to
the rest of the suite: the plugin exercises the core through a checkout,
where `__file__`-relative paths and repository layout happen to work. A
wheel has neither. Each test below pins one property that a source
checkout would satisfy by accident and an install would not.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

import mojiemoji
from mojiemoji.lib.constants import BASE_URL_ENV, DEFAULT_BASE_URL
from mojiemoji.prestamp.catalog import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_EMOJI_CATALOG_PATH,
    catalog_exists,
    load_catalog,
)

PUBLIC_API = [
    "BASE_URL_ENV",
    "DEFAULT_BASE_URL",
    "DEFAULT_CATALOG_PATH",
    "DEFAULT_EMOJI_CATALOG_PATH",
    "default_base_url",
    "load_catalog",
    "load_emoji_catalog",
    "prestamp_text",
    "render",
    "report_unstamped",
    "transform",
]


@pytest.mark.parametrize("name", PUBLIC_API)
def test_public_api_is_exported(name: str) -> None:
    """The names downstream code imports must survive any internal reshuffle."""
    assert name in mojiemoji.__all__
    assert hasattr(mojiemoji, name)


@pytest.mark.parametrize("path", [DEFAULT_CATALOG_PATH, DEFAULT_EMOJI_CATALOG_PATH])
def test_catalogs_ship_inside_the_package(path) -> None:
    """Resolved as package data, so an installed wheel finds them too.

    The pre-carve-out code walked out of the package with ``__file__`` to
    reach a sibling ``data/`` directory — a path that simply does not
    exist once the package is installed.
    """
    assert catalog_exists(path)


def test_catalog_loads_without_a_checkout() -> None:
    defaults, terms = load_catalog()
    assert defaults
    assert terms


def test_transform_stamps_japanese_prose() -> None:
    out = mojiemoji.transform("対応を進める。", seed="0")
    assert "<img" in out
    assert DEFAULT_BASE_URL in out


def test_base_url_is_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A self-hosted instance must not require patching the source."""
    monkeypatch.setenv(BASE_URL_ENV, "https://example.test")
    out = mojiemoji.transform("対応を進める。", seed="0")
    assert "https://example.test" in out
    assert DEFAULT_BASE_URL not in out


def test_cli_transforms_stdin() -> None:
    """`[project.scripts] mojiemoji` is a thin wrapper over this entry."""
    proc = subprocess.run(
        [sys.executable, "-m", "mojiemoji.prestamp", "--seed", "0"],
        input="対応を進める。",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "<img" in proc.stdout


def test_cli_rejects_host_policy_flags() -> None:
    """`--surface` is a GitHub concept and stays in the plugin's shim.

    Accepting it here would re-couple the published package to one host's
    posting rules — the whole point of the carve-out.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "mojiemoji.prestamp", "--surface", "pr-body"],
        input="対応を進める。",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0
    assert "--surface" in proc.stderr


# The posting gate imports `mojiemoji.lib.constants` for the service URL,
# and that pulls in the package initializer — which re-exports the catalog
# loaders. A hard PyYAML requirement at import time therefore took down
# every hook invocation on a bare system Python, including the ones that
# never read a catalog.
_BLOCK_YAML = """
import sys


class _NoYaml:
    def find_spec(self, name, path=None, target=None):
        if name == "yaml":
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return None


sys.meta_path.insert(0, _NoYaml())
"""


def _run_without_yaml(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _BLOCK_YAML + body],
        capture_output=True, text=True, timeout=30,
    )


def test_importing_the_package_does_not_require_pyyaml() -> None:
    proc = _run_without_yaml(
        "from mojiemoji.lib.constants import default_base_url\n"
        "print(default_base_url())\n"
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip()


def test_reading_a_catalog_still_reports_the_missing_dependency() -> None:
    proc = _run_without_yaml(
        "from mojiemoji import load_catalog\n"
        "load_catalog()\n"
    )
    assert proc.returncode != 0
    assert "PyYAML is required" in proc.stderr
