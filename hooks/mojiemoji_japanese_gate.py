#!/usr/bin/env python3
"""PreToolUse hook: gate Japanese GitHub body submissions without properly-styled mojiemoji stamps.

Fires on two posting paths:
  1. Bash tool with `gh` posting the body:
     - `gh (issue|pr|release) (create|comment|review)` (high-level), OR
     - `gh api .../reviews|comments|issues|releases ...` (raw REST POST,
       used by skills like cross-repo-review that batch-publish reviews).
  2. MCP GitHub tools whose `tool_input` carries a Japanese `body`
     field, including nested review `comments[].body` fields. The MCP
     matcher uses both server-alias signals (anything
     with `github` in the namespace) AND known GitHub-specific tool
     name patterns (`*pull_request*`, `*issue_write`, `add_issue_comment`,
     `*release*`, etc.) so installations that aliased the GitHub MCP
     server to a non-`github` name are still covered. Title /
     commit_message / file content / description are intentionally NOT
     inspected — only the `body` posting-prose field is inspected, and
     each body value must be decorated on its own.

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

Implementation lives in `hooks/gate/` — this script is the thin entry
pipeline that wires the routing / validator modules together. See
https://github.com/jozobeer/mojiemoji-plugin/issues/101.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# `hooks/gate/__init__.py` already splices the skill scripts dir onto
# sys.path, but Claude Code invokes this file as `python3 hooks/...`
# rather than as a package member, so `gate` itself isn't importable
# until `hooks/` is on the path. Splice both — hooks/ for `import gate`,
# scripts/ for any direct `from lib.X import Y` consumers downstream.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from gate.extract import JP_RE, MOJI_URL_RE, command_forces_pr_body, extract_inspect_text  # noqa: E402
from gate.extract import is_pr_body_submission  # noqa: E402
from gate.validators import (  # noqa: E402
    PIPELINE,
    validate_catalog_leftovers,
    validate_schema_version,
)
from lib.repo_policy import should_skip_pr_body  # noqa: E402


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    inspect_texts = extract_inspect_text(data)
    if inspect_texts is None:
        return 0
    jp_texts = [text for text in inspect_texts if JP_RE.search(text)]
    if not jp_texts:
        return 0
    cwd = data.get("cwd", "")
    if (
        is_pr_body_submission(data)
        and not command_forces_pr_body(data)
        and not any(MOJI_URL_RE.search(text) for text in jp_texts)
        and should_skip_pr_body(cwd=Path(cwd) if cwd else None)
    ):
        return 0

    for inspect_text in jp_texts:
        urls = MOJI_URL_RE.findall(inspect_text)
        for stage in PIPELINE:
            rc = stage(urls)
            if rc != 0:
                return rc

        rc = validate_catalog_leftovers(inspect_text)
        if rc != 0:
            return rc

    rc = validate_schema_version("\n".join(jp_texts))
    if rc != 0:
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
