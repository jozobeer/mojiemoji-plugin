#!/usr/bin/env python3
"""PreToolUse hook: gate Japanese GitHub body submissions without
properly-styled mojiemoji stamps.

Fires on two posting paths:
  1. Bash tool with `gh` posting the body:
     - `gh (issue|pr|release) (create|comment|review)` (high-level), OR
     - `gh api .../reviews|comments|issues|releases ...` (raw REST POST,
       used by skills like cross-repo-review that batch-publish reviews).
  2. MCP GitHub tools whose `tool_input` carries a Japanese `body`
     field. The MCP matcher uses both server-alias signals (anything
     with `github` in the namespace) AND known GitHub-specific tool
     name patterns (`*pull_request*`, `*issue_write`, `add_issue_comment`,
     `*release*`, etc.) so installations that aliased the GitHub MCP
     server to a non-`github` name are still covered. Title /
     commit_message / file content / description are intentionally NOT
     inspected — only the `body` posting-prose field, matching the
     SKILL.md decoration policy.

And EITHER:
  1. inspected text has zero `mojiemoji.jozo.beer` URLs, OR
  2. at least one mojiemoji URL is missing any of the required style
     parameters (`background=transparent`, `font=*`, `color=*`,
     `animation=*`, `outline=darker`, `outline_width=2`), OR
  3. a URL uses a non-canonical font/animation, an invalid outline
     value, pairs a color-shifting animation with an outline, uses a
     Tailwind 600+ color (invisible on dark mode), or contains a
     3-kanji single-stamp text (must split as 2+1).

The Bash path also reads referenced body files (`--body-file PATH` /
`--input PATH` / `-F body=@PATH`) and interpreter-invoked scripts so
file-routed / dynamically-built bodies are covered too.

When triggered, blocks the tool call (exit 2) and prints reminder to
stderr so Claude sees it before submission. Bypass: include
`MOJIEMOJI_HOOK_DISABLED=1` anywhere in the inspected text — for Bash
that's the command line (prefix idiom matches the git pre-commit hook),
for MCP that's the body itself.

Implementation lives in `hooks/gate/`:
  - `patterns`  — regex / constant table
  - `extract`   — Bash + MCP routing, file/script body inclusion
  - `validators/*` — six per-stage checks behind `VALIDATION_PIPELINE`

This file is the entry point only: stdin → extract → JP check →
pipeline → catalog leftovers → schema drift. Decomposed in #101 so
each validator (and its stderr template) can be edited in isolation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make `gate` importable when Claude Code invokes us by absolute path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate.extract import extract_inspect_text  # noqa: E402
from gate.patterns import JP_RE, MOJI_URL_RE  # noqa: E402
from gate.validators import (  # noqa: E402
    VALIDATION_PIPELINE,
    validate_catalog_leftovers,
    validate_schema_version,
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    inspect_text = extract_inspect_text(data)
    if inspect_text is None:
        return 0
    if not JP_RE.search(inspect_text):
        return 0

    urls = MOJI_URL_RE.findall(inspect_text)
    for stage in VALIDATION_PIPELINE:
        rc = stage(urls)
        if rc != 0:
            return rc

    rc = validate_catalog_leftovers(inspect_text)
    if rc != 0:
        return rc

    rc = validate_schema_version(inspect_text)
    if rc != 0:
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
