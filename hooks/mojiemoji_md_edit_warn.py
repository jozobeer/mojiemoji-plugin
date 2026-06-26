#!/usr/bin/env python3
"""PostToolUse hook: warn (not block) when an Edit/Write/MultiEdit on a
documentation `*.md` file leaves prestamp drift.

Local file edits never flow through the gh / MCP gate, so README /
docs / SKILL.md / agents prompts can silently drift away from the
catalog without anyone noticing — exactly the dogfood-followup problem
the project keeps re-discovering (#91). This hook reads the file after
the edit lands, runs `prestamp.py` over it in a subprocess, and if the
output differs from the current contents, emits a unified diff to
stderr with the suggested transform.

It never blocks — the goal is awareness, not enforcement. The CI
drift check (#91 / catalog-drift-check sibling) is the hard gate.

Matched file paths (anything else is silently ignored):
  - any `*.md` under the repo root, restricted to:
    - `README.md`
    - `docs/**/*.md`
    - `agents/**/*.md`
    - `skills/**/SKILL.md`
    - `CHANGELOG.md`

Authors who want a clean before/after region can wrap it with
`<!-- mojiemoji:off -->` / `<!-- mojiemoji:on -->` — prestamp respects
the markers, so this hook will be silent for those segments.

Exit code is always 0. Output on stderr only fires when there is
something the author should look at.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_MD_SUFFIX = "SKILL.md"
JP_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")
# Also consider Latin for English/i18n drift warnings (#148)
LATIN_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")


def _is_documentation_md(path: Path, repo_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except (ValueError, OSError):
        return False
    rel_str = str(rel).replace(os.sep, "/")
    if rel_str == "README.md" or rel_str == "CHANGELOG.md":
        return True
    if rel_str.startswith("docs/") and rel_str.endswith(".md"):
        return True
    if rel_str.startswith("agents/") and rel_str.endswith(".md"):
        return True
    if rel_str.startswith("skills/") and rel_str.endswith(SKILL_MD_SUFFIX):
        return True
    return False


def _has_japanese(text: str) -> bool:
    return JP_RE.search(text) is not None


def _has_latin(text: str) -> bool:
    return LATIN_RE.search(text) is not None


def _find_repo_root(start: Path) -> Path | None:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists() or (parent / ".claude-plugin").exists():
            return parent
    return None


def _file_path_from_payload(payload: dict) -> Path | None:
    tool_input = payload.get("tool_input") or {}
    raw = tool_input.get("file_path")
    if isinstance(raw, str) and raw:
        return Path(raw)
    return None


def _run_prestamp(text: str, plugin_root: Path) -> tuple[str, int]:
    script = plugin_root / "skills" / "mojiemoji-github" / "scripts" / "prestamp.py"
    if not script.exists():
        return "", -1
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=text,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return proc.stdout, proc.returncode


def _unified_diff(original: str, transformed: str, label: str) -> str:
    import difflib
    diff_lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        transformed.splitlines(keepends=True),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
        n=2,
    )
    return "".join(diff_lines)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name") or ""
    if tool_name not in {"Edit", "Write", "MultiEdit"}:
        return 0

    file_path = _file_path_from_payload(payload)
    if file_path is None:
        return 0
    if file_path.suffix != ".md":
        return 0

    plugin_root_env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    plugin_root = Path(plugin_root_env) if plugin_root_env else None
    repo_root = _find_repo_root(file_path.parent) or plugin_root
    if repo_root is None:
        return 0
    if not _is_documentation_md(file_path, repo_root):
        return 0
    if not file_path.exists():
        return 0

    try:
        current = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    if not (_has_japanese(current) or _has_latin(current)):
        return 0

    prestamp_root = plugin_root or repo_root
    transformed, rc = _run_prestamp(current, prestamp_root)
    if rc != 0:
        return 0
    if transformed == current:
        return 0

    try:
        rel_label = str(file_path.resolve().relative_to(repo_root.resolve()))
    except (ValueError, OSError):
        rel_label = file_path.name

    diff = _unified_diff(current, transformed, rel_label)
    if not diff.strip():
        return 0

    sys.stderr.write(
        "📎 mojiemoji prestamp drift detected on doc edit "
        f"({rel_label}). The catalog would transform this further "
        "— run `prestamp.py` on the file if you want to apply, or "
        "wrap the affected region in `<!-- mojiemoji:off -->` … "
        "`<!-- mojiemoji:on -->` if it should stay raw. "
        "Suggested diff:\n\n"
    )
    sys.stderr.write(diff)
    sys.stderr.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
