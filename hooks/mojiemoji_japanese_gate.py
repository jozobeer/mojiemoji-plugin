#!/usr/bin/env python3
"""PreToolUse hook: gate Japanese (and opt-in English/Latin #148) GitHub body submissions without properly-styled mojiemoji stamps.

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

from gate.extract import JP_RE, LATIN_RE, MOJI_URL_RE, extract_inspect_text  # noqa: E402
from gate.extract import forces_pr_body, is_pr_body_submission, pr_body_target_repo  # noqa: E402
from gate.validators import (  # noqa: E402
    PIPELINE,
    validate_catalog_leftovers,
    validate_schema_version,
)
from lib.repo_policy import POLICY_LEAKS, POLICY_UNKNOWN, repo_policy_state  # noqa: E402

_PR_BODY_LEAK_REMINDER = (
    "🚫 このリポジトリは PR body を commit message にコピーする設定です\n"
    "\n"
    "検出: squash / merge commit message が `PR_BODY` のリポジトリに、mojiemoji\n"
    "stamp を含む PR body を投稿しようとしています。GitHub が PR body を squash /\n"
    "merge commit に転記するため、`<img src=\"https://mojiemoji.jozo.beer/...\">`\n"
    "の HTML が commit 履歴に恒久的に残ってしまいます (issue #138)。\n"
    "\n"
    "## 対処\n"
    "1. PR body から mojiemoji stamp を外して投稿する (推奨。本文の装飾は不要)\n"
    "2. どうしても装飾したいなら、投稿経路に応じて FORCE を明示する:\n"
    "   - Bash: command 先頭に `MOJIEMOJI_FORCE_PR_BODY=1` を付ける\n"
    "   - MCP: body 内に `MOJIEMOJI_FORCE_PR_BODY=1` を含める\n"
    "\n"
    "issue / review / comment など他の surface は通常どおり装飾して構いません。\n"
    "詳細: ${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/SKILL.md\n"
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    inspect_texts = extract_inspect_text(data)
    if inspect_texts is None:
        return 0
    jp_texts = [text for text in inspect_texts if JP_RE.search(text)]
    en_texts = [text for text in inspect_texts if LATIN_RE.search(text)]

    # English/Latin opt-in support (#148). Pure English bodies are NOT gated
    # by default (to avoid forcing stamps on English-first users).
    # Opt in for a submission by including the marker:
    #   MOJIEMOJI_ENGLISH_GATE=1   (in Bash command or inside the body text)
    english_enabled = any(
        "MOJIEMOJI_ENGLISH_GATE=1" in (t or "")
        for t in (inspect_texts or [])
    ) or "MOJIEMOJI_ENGLISH_GATE=1" in (
        (data.get("tool_input", {}) or {}).get("command", "")
    )

    if not jp_texts and not (english_enabled and en_texts):
        return 0

    # Determine which bodies to enforce stamping rules on. Japanese and
    # opt-in English bodies are both active when a payload mixes them.
    active = [
        text
        for text in inspect_texts
        if JP_RE.search(text) or (english_enabled and LATIN_RE.search(text))
    ]
    cwd = data.get("cwd", "")
    if is_pr_body_submission(data) and not forces_pr_body(data):
        owner, repo = pr_body_target_repo(data) or (None, None)
        state = repo_policy_state(
            owner=owner,
            repo=repo,
            cwd=Path(cwd) if cwd else None,
        )
        has_stamp = any(MOJI_URL_RE.search(text) for text in active)
        if not has_stamp and state in (POLICY_LEAKS, POLICY_UNKNOWN):
            return 0
        if has_stamp and state == POLICY_LEAKS:
            sys.stderr.write(_PR_BODY_LEAK_REMINDER)
            return 2

    for inspect_text in active:
        urls = MOJI_URL_RE.findall(inspect_text)
        for stage in PIPELINE:
            rc = stage(urls)
            if rc != 0:
                return rc

        rc = validate_catalog_leftovers(inspect_text)
        if rc != 0:
            return rc

    rc = validate_schema_version("\n".join(active))
    if rc != 0:
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
