"""Bash + MCP routing, body file / script reading, JSON body collection.

This module decides *what text the gate validates*. Two entry paths
exist:

- `_route_bash` — for `gh` CLI invocations (high-level subcommands or
  raw REST POSTs via `gh api`). Inspects the command, then reads any
  referenced `--body-file` / `--input` / `-F body=@path` files and any
  interpreter-invoked script source.
- `_route_mcp` — for MCP GitHub tools whose `tool_input` carries
  structured body fields (top-level `body`, nested `comments[].body`).

`extract_inspect_text` dispatches to one of the two and returns the
list of inspectable surfaces, or `None` to skip the gate.
"""
from __future__ import annotations

import json
import os
import re

JP_RE = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")
# High-level `gh` commands that publish bodies.
GH_HIGH_RE = re.compile(r"gh\s+(issue|pr|release)\s+(create|comment|review|edit)")
# Raw REST POSTs that skills like cross-repo-review use to publish reviews,
# comments, issues, or releases. We match the resource segment so we don't
# fire on GET / read-only calls.
GH_API_RE = re.compile(
    r"gh\s+api\b[^\n]*?/(?:reviews|comments|issues|pulls/\d+/(?:reviews|comments)|releases)\b"
)
STAMP_MARKER = "mojiemoji.jozo.beer"
BYPASS_MARKER = "MOJIEMOJI_HOOK_DISABLED=1"
# Match every mojiemoji URL up to the first URL/HTML delimiter so we can
# verify per-URL query parameters. Delimiters: whitespace, `"`, `<`, `>`, `)`.
MOJI_URL_RE = re.compile(r"https?://mojiemoji\.jozo\.beer/[^\s\"<>)]+")
# File-based body sources: `gh ... --body-file PATH`, `gh api ... --input
# PATH`, `gh api ... -F body=@PATH`. Capture the path so we can also inspect
# the file's contents — otherwise file-routed posts trivially bypass the URL
# check.
BODY_FILE_RE = re.compile(
    r"(?:--body-file|--input)(?:\s+|=)(['\"]?)([^'\"\s|;&)]+)\1"
)
F_BODY_RE = re.compile(r"-F\s+body=@(['\"]?)([^'\"\s|;&)]+)\1")
# Non-body flag/value pairs to strip from the command before treating
# it as an inspect surface. Title / label / reviewer / assignee /
# milestone / head / base values are metadata, not posting prose — they
# may legitimately carry Japanese (`--title "日本語…"`, `--label "バグ"`)
# without needing mojiemoji decoration, mirroring the MCP path's
# `BODY_FIELDS = {"body"}` policy. Without this strip, the per-surface
# validation rolled out in the inline-review-comments change would
# block valid posts like `gh pr create --title "<JP>" --body-file decorated.md`.
#
# Short forms (`-t`, `-l`, `-r`, `-a`, `-m`, `-H`, `-B`) follow gh CLI
# defaults. `-H` overlaps with `gh api -H "HTTP-Header: ..."`, but HTTP
# headers are not body prose either, so collapsing both into the same
# strip rule is safe. Value forms covered: `--flag "v"`, `--flag 'v'`,
# `--flag=v`, `--flag v`. Lookbehind on the short-form alternative
# prevents `--flag-with-t` from being mis-stripped as `-t`.
NON_BODY_FLAGS_RE = re.compile(
    r"(?:--(?:title|label|reviewer|assignee|milestone|head|base)|"
    r"(?<!\S)-[tlramHB])"
    r"(?:\s+|=)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s\"']+)"
)
# Script files referenced via interpreter invocation. The 2026-05-12
# triage-review incident bypassed file-body inspection by building the JSON
# body via `python3 approve-1756.py` and posting via `gh api --input` in the
# SAME bash call — the JSON didn't exist at hook fire time, so file-body
# inspection silently skipped it. Inspecting the script source catches the
# hand-crafted URL templates at their definition site (inside f-strings,
# concatenations, mj() helpers) regardless of whether the output file has
# been written yet.
SCRIPT_RE = re.compile(
    r"(?:python3?|ruby|node|bash|sh|zsh|fish)\s+(['\"]?)"
    r"([^'\"\s|;&)<>]+\.(?:py|rb|js|mjs|cjs|ts|sh|bash|zsh|fish))\1"
)
# MCP GitHub tool names. The 2026-05-12 series of incidents exposed
# that the Bash matcher misses entirely when skills/agents post via
# the MCP `github_*` tools (REST-equivalent, structured tool_input).
#
# Match strategy is two-pronged because the MCP namespace is
# `mcp__<server-alias>__<tool-name>` and the alias is user-configurable.
# Matching only on `github` in the *alias* (e.g., `mcp__github__*` or
# `mcp__mcpm_profile_base__github_*`) misses installations that aliased
# the GitHub server to something else (`mcp__gh__*`, `mcp__octo__*`,
# etc.). To stay robust regardless of alias, also match on known
# GitHub-specific *tool* name patterns — terms like `pull_request`,
# `issue_write`, `add_issue_comment`, `release` are GitHub-specific
# enough that a tool with that name is overwhelmingly likely to be a
# GitHub write path. Read-only tools (get_*, list_*, search_*) match
# the regex too but carry no body field, so body extraction returns
# empty and the gate exits 0 — broader matching costs nothing.
MCP_GH_RE = re.compile(
    r"^mcp__.*?(?:"
    r"github|"
    r"create_pull_request|update_pull_request|merge_pull_request|"
    r"pull_request_review|pull_request_read|pull_request_write|"
    r"add_comment_to_pending_review|add_reply_to_pull_request_comment|"
    r"add_issue_comment|"
    r"issue_read|issue_write|sub_issue_write|"
    r"create_release|update_release"
    r")",
    re.IGNORECASE,
)
# Body-class fields across the MCP GitHub tool family. Title /
# commit_message / file content are excluded — they are conventionally
# undecorated per SKILL.md (titles short, commit messages plain).
#
# `description` was previously included but is too broad: `description`
# is also the metadata field for repository / label / pending-review
# objects, where the value is plain-text metadata rather than a posted
# prose body. Including it would force mojiemoji decoration on Japanese
# repo descriptions and label descriptions — surfaces that the skill
# explicitly does not target. `body` is the canonical posting-prose
# field across `add_issue_comment`, `pull_request_review_write`,
# `add_comment_to_pending_review`, `add_reply_to_pull_request_comment`,
# `issue_write`, `create_pull_request`, `update_pull_request`,
# `create_release`, etc., so `body` alone covers the actual targets.
BODY_FIELDS = frozenset({"body"})


def _has_bypass(text: str) -> bool:
    """Return True if the bypass marker is present in `text`."""
    return BYPASS_MARKER in text


def expand_body_path(raw, cwd):
    """Resolve `~`, env vars, and relative paths against the tool-call cwd."""
    path = os.path.expanduser(os.path.expandvars(raw))
    if not os.path.isabs(path) and cwd:
        path = os.path.join(cwd, path)
    return path


def _body_texts_from_source(text):
    """Return inspectable body pieces from raw markdown or JSON payload text.

    `gh api --input file.json` review payloads can carry a top-level
    `body` plus nested `comments[].body` fields. Treat those as
    separate surfaces so a decorated summary cannot mask undecorated
    inline findings.
    """
    try:
        parsed = json.loads(text)
    except Exception:
        return [text]
    pieces = collect_body_text(parsed, BODY_FIELDS)
    return pieces or [text]


def read_body_files(command, cwd):
    """Return (body_pieces, missing_paths) for every body file
    referenced by the command.

    `body_pieces` is `list[str]` — one entry per inspectable surface —
    so callers can extend a pieces list directly. Previously this
    helper joined pieces into a single string, which made
    `pieces.extend(file_bodies)` split Japanese into per-character
    surfaces and falsely block decorated review payloads.

    `-` (stdin) and missing files are tracked separately so callers
    can decide whether to react. Most callers should ignore
    `missing_paths` — referencing the same paths in heredoc-quoted
    documentation (e.g., commit messages mentioning `--input out.json`)
    would otherwise produce false positives. Body files that DO exist
    at hook time are still inspected.
    """
    pieces = []
    missing = []
    for regex in (BODY_FILE_RE, F_BODY_RE):
        for match in regex.finditer(command):
            raw = match.group(2)
            if raw == "-":
                missing.append(raw)
                continue
            path = expand_body_path(raw, cwd)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    pieces.extend(_body_texts_from_source(fh.read()))
            except (OSError, ValueError):
                missing.append(raw)
                continue
    return pieces, missing


def read_script_files(command, cwd):
    """Return concatenated source of every script invoked via interpreter.

    Catches the `python3 build_body.py && gh api --input out.json` bypass
    where the body file is built in the same shell call. We can't inspect
    the not-yet-written output file, but we CAN inspect the script that
    will produce it — hand-crafted URL templates show up in the source.
    """
    pieces = []
    for match in SCRIPT_RE.finditer(command):
        raw = match.group(2)
        path = expand_body_path(raw, cwd)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                pieces.append(fh.read())
        except (OSError, ValueError):
            continue
    return "\n".join(pieces)


def collect_body_text(obj, target_keys):
    """Walk a nested dict/list and concatenate string values whose key
    is in `target_keys`. Used to extract body-class fields from MCP
    `tool_input` regardless of nesting depth.
    """
    pieces = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in target_keys and isinstance(value, str):
                pieces.append(value)
            else:
                pieces.extend(collect_body_text(value, target_keys))
    elif isinstance(obj, list):
        for item in obj:
            pieces.extend(collect_body_text(item, target_keys))
    return pieces


def _route_bash(data: dict):
    """Return inspectable body pieces for a Bash tool call, or `None` to skip the gate.

    Bypass marker is scoped to the command line, not the merged body/
    script text — the original idiom (matching the git pre-commit
    `MOJIEMOJI_HOOK_DISABLED=1 git commit ...` style) is an opt-in by
    the *invocation*, not by something happening to appear inside a
    referenced file. Once file/script bodies are merged into
    `inspect_text`, documentation prose or test fixtures that mention
    the literal marker would silently disable the gate — accidental
    bypass via benign mention. Keep the bypass check on `command` only.

    File-routed posts (`--body-file PATH` / `--input PATH` /
    `-F body=@PATH`) are inspected as individual body surfaces when
    they contain JSON review payloads. Interpreter-invoked scripts
    (`python3 X.py` etc.) are kept as one source-text surface so
    dynamically-built bodies cannot bypass the regex inspection. See
    `read_body_files` / `read_script_files` for the file-side cwd
    resolution.
    """
    command = (data.get("tool_input", {}) or {}).get("command", "")
    if not command:
        return None
    if _has_bypass(command):
        return None
    if not (GH_HIGH_RE.search(command) or GH_API_RE.search(command)):
        return None
    cwd = data.get("cwd", "")
    file_bodies, _ = read_body_files(command, cwd)
    script_body = read_script_files(command, cwd)
    # Strip non-body flag values (title / label / reviewer / assignee /
    # milestone / head / base) from the command before treating it as
    # an inspect surface. Without this, Japanese in `--title` etc.
    # would be required to carry mojiemoji decoration — contradicting
    # the documented policy that titles / labels are out of scope.
    inspected_command = NON_BODY_FLAGS_RE.sub("", command)
    pieces = [inspected_command]
    pieces.extend(file_bodies)
    if script_body:
        pieces.append(script_body)
    return pieces


def _route_mcp(tool_input: dict):
    """Return inspectable body pieces for an MCP GitHub tool call, or `None` to skip.

    Multiple body pieces (e.g., `pull_request_review_write` with a
    top-level `body` summary plus `comments[].body` inline findings)
    remain separate on purpose: review summaries and inline comments
    are both GitHub prose surfaces, and each Japanese body value must
    carry its own mojiemoji decoration.

    Bypass marker check happens AFTER body assembly because MCP path
    has no shell prefix; the only place a caller can legitimately opt
    out is inside the body text itself. The rule still parallels Bash
    (bypass on the surface the caller directly controls), just adapted
    to structured input.
    """
    pieces = collect_body_text(tool_input, BODY_FIELDS)
    if not pieces:
        return None
    if _has_bypass("\n".join(pieces)):
        return None
    return pieces


def extract_inspect_text(data: dict):
    """Dispatch to Bash / MCP routing. Returns body pieces or `None`.

    Read-only MCP tools (get_*, list_*, search_*) match `MCP_GH_RE`
    too but carry no body field — `_route_mcp` returns `None` for
    them, which exits the gate cleanly without further inspection.
    """
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}
    if tool_name == "Bash":
        return _route_bash(data)
    if MCP_GH_RE.match(tool_name):
        return _route_mcp(tool_input)
    return None
