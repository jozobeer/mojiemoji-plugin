"""Stage 6 — schema-version drift (issue #80).

The host SKILL.md carries a `<!-- mojiemoji-schema-version: X.Y.Z -->`
marker. Each AI harness (claude / codex / opencode / gemini /
copilot-cli) usually keeps a local copy of SKILL.md under
`$HOME/.config/<harness>/skills/mojiemoji-github/SKILL.md`; when those
copies fall behind the host (because the user updated this repo but
never re-imported the skill), the harness keeps using stale rules.

This stage warns the agent that drift is present, naming each stale
file and its version delta. Default behaviour is warning-only (rc=0)
so a stale harness file does not block legitimate posts. Setting
`MOJIEMOJI_STRICT_VERSION=1` upgrades to blocking (rc=2) for CI use.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


SCHEMA_MARKER_RE = re.compile(
    r"<!--\s*mojiemoji-schema-version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*-->"
)
HOST_SKILL_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "skills" / "mojiemoji-github" / "SKILL.md"
)


def _harness_skill_paths() -> tuple[tuple[str, Path], ...]:
    """Candidate paths for non-host harness SKILL.md copies. Resolved lazily
    so tests can monkeypatch `Path.home()` per test. Names match the
    cross-harness audit script."""
    home = Path.home()
    return (
        ("claude", home / ".config" / "claude" / "skills" / "mojiemoji-github" / "SKILL.md"),
        ("codex", home / ".config" / "codex" / "skills" / "mojiemoji-github" / "SKILL.md"),
        ("opencode", home / ".config" / "opencode" / "skills" / "mojiemoji-github" / "SKILL.md"),
        ("copilot-cli", home / ".config" / "copilot-cli" / "skills" / "mojiemoji-github" / "SKILL.md"),
        ("gemini", home / ".config" / "gemini" / "skills" / "mojiemoji-github" / "SKILL.md"),
        ("gemini (rule)", home / ".config" / "gemini" / "rules" / "mojiemoji-github.md"),
    )


_canonical_version_cache: str | None | object = object()  # sentinel: "not loaded"


def _extract_schema_version(path: Path) -> str | None:
    """Grep the schema-version marker from a SKILL.md / rule file. Returns
    the version string, or None when missing / unreadable."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = SCHEMA_MARKER_RE.search(line)
                if m:
                    return m.group(1)
    except (OSError, UnicodeDecodeError):
        return None
    return None


def _load_canonical_schema_version() -> str | None:
    """Read the host SKILL.md schema marker once and cache the result.
    Returns None if the marker is absent (treat as drift-check disabled)."""
    global _canonical_version_cache
    if isinstance(_canonical_version_cache, str) or _canonical_version_cache is None:
        return _canonical_version_cache  # type: ignore[return-value]
    _canonical_version_cache = _extract_schema_version(HOST_SKILL_PATH)
    return _canonical_version_cache  # type: ignore[return-value]


def validate_schema_version(_text: str) -> int:
    """Warn (or in strict mode block) when any harness SKILL.md copy is
    behind the host. `_text` is unused — version drift is a global
    property — but the signature mirrors `validate_catalog_leftovers` for
    consistency.

    See https://github.com/jozobeer/mojiemoji-plugin/issues/80.
    """
    canonical = _load_canonical_schema_version()
    if canonical is None:
        return 0  # marker missing on host — drift-check disabled.

    drifts: list[tuple[str, Path, str | None]] = []
    for name, path in _harness_skill_paths():
        if not path.exists():
            continue
        found = _extract_schema_version(path)
        if found != canonical:
            drifts.append((name, path, found))

    if not drifts:
        return 0

    strict = os.environ.get("MOJIEMOJI_STRICT_VERSION") == "1"
    summary_lines = [
        "[mojiemoji-skill version drift]",
        f"  expected: {canonical} (host plugin)",
    ]
    for name, path, found in drifts:
        shown = found if found is not None else "(marker missing)"
        summary_lines.append(f"  found:    {shown} — {name} ({path})")
    summary_lines.append(
        "  hint:    re-install the skill (claude plugin marketplace install or git pull)"
    )
    sys.stderr.write("\n".join(summary_lines) + "\n")
    return 2 if strict else 0
