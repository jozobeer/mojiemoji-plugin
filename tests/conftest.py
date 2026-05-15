"""pytest helpers for the mojiemoji-japanese-gate hook."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "hooks" / "mojiemoji-japanese-gate.py"


@pytest.fixture
def run_hook(tmp_path):
    """Run the hook with a PreToolUse JSON payload on stdin.

    `cwd` defaults to a temp dir so the hook's body-file / script-file
    inspection can resolve relative paths the tests create on disk
    without polluting the real working directory.
    """

    def _run(payload: dict[str, Any], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd or tmp_path),
            timeout=10,
        )

    return _run


# Reusable URL builder for tests. Mirrors what `mojiemoji_markdown.rb`
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
    return f"https://mojiemoji.jozo.beer/emoji/{encoded}?{query}"


# A complete, hook-passing inline `<img>` snippet for fixture bodies.
def stamp_img(**kwargs) -> str:
    alt = kwargs.pop("alt", kwargs.get("text", "テスト"))
    url = stamp_url(**kwargs)
    return f'<img src="{url}" alt="{alt}" height="24" align="absmiddle">'
