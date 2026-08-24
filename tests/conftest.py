"""pytest helpers for the mojiemoji_japanese_gate hook."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
# The catalogs are package data of the core distribution now, not skill
# assets. One definition here so a future move is a one-line change.
CATALOG_DIR = REPO_ROOT / "packages" / "mojiemoji-core" / "src" / "mojiemoji" / "data"
HOOK = REPO_ROOT / "hooks" / "mojiemoji_japanese_gate.py"
PRESTAMP = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "prestamp.py"
COVERAGE = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "coverage.py"
GENERATE = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "generate_catalog.py"
LINT_RENDERED_BODY = (
    REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "lint_rendered_body.py"
)


def run_py(script: Path, text: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a script under tests/ skill scripts with `text` on stdin.

    Shared helper for the prestamp / coverage / generate_catalog test
    files split out of test_prestamp_coverage.py (#103). Pinning a
    10-second timeout matches the prior monolithic file's behaviour.
    """
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=text,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.fixture(autouse=True)
def _coverage_subprocess_env(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = REPO_ROOT / "pyproject.toml"
    monkeypatch.setenv("COVERAGE_PROCESS_START", str(cfg))
    monkeypatch.setenv("MOJIEMOJI_COVERAGE_HOOKS", str(REPO_ROOT / "hooks"))
    monkeypatch.setenv(
        "MOJIEMOJI_COVERAGE_SCRIPTS",
        str(REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"),
    )
    # Anchor data file to the repo root; otherwise subprocesses with cwd=tmp_path
    # write to a dir pytest deletes at teardown, silently losing all hits.
    monkeypatch.setenv("COVERAGE_FILE", str(REPO_ROOT / ".coverage"))
    sitecustomize_dir = str(REPO_ROOT / "tests")
    existing = os.environ.get("PYTHONPATH", "")
    new_path = f"{sitecustomize_dir}{os.pathsep}{existing}" if existing else sitecustomize_dir
    monkeypatch.setenv("PYTHONPATH", new_path)


@pytest.fixture
def run_hook(tmp_path):
    """Run the hook with a PreToolUse JSON payload on stdin.

    `cwd` defaults to a temp dir so the hook's body-file / script-file
    inspection can resolve relative paths the tests create on disk
    without polluting the real working directory.
    """

    def _run(payload: dict[str, Any], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd or tmp_path),
            timeout=10,
        )

    return _run


# Reusable URL builder for tests. Mirrors what `mojiemoji_markdown.py`
# would emit when given the canonical 6-parameter set, so a single
# helper covers happy-path URLs across cases.
def stamp_url(
    text: str = "テスト",
    font: str = "gothic-bold",
    color: str = "3b82f6",
    animation: str = "bane",
    background: str | None = "transparent",
    outline: str | None = "darker",
    outline_width: str | None = "2",
    speed: str | None = None,
    base_url: str = "https://mojiemoji.jozo.beer",
) -> str:
    from urllib.parse import quote

    encoded = quote(text, safe="")
    parts = [
        f"font={font}",
        f"color={color}",
        f"animation={animation}",
    ]
    if background is not None:
        parts.append(f"background={background}")
    if outline is not None:
        parts.append(f"outline={outline}")
    if outline_width is not None:
        parts.append(f"outline_width={outline_width}")
    if speed is not None:
        parts.append(f"speed={speed}")
    query = "&".join(parts)
    return f"{base_url.rstrip('/')}/emoji/{encoded}?{query}"


# A complete, hook-passing inline `<img>` snippet for fixture bodies.
def stamp_img(**kwargs) -> str:
    alt = kwargs.pop("alt", kwargs.get("text", "テスト"))
    url = stamp_url(**kwargs)
    return f'<img src="{url}" alt="{alt}" height="24" align="absmiddle">'


def assert_skill_agent_guidance(stderr: str) -> None:
    assert "`Skill(mojiemoji-github)`" in stderr
    assert "`Agent` ツール" in stderr
    # #147: recommend the fully-qualified subagent type; note bare as an
    # environment-dependent fallback.
    assert 'subagent_type: "mojiemoji-github:mojiemoji-selector"' in stderr
    assert "bare `mojiemoji-selector`" in stderr
    assert "Skill ツールには渡せない" in stderr
    # #147: remediation must embed a resolved absolute path — the literal
    # variable is empty in the Bash tool environment.
    assert "${CLAUDE_PLUGIN_ROOT}" not in stderr
