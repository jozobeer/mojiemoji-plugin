"""Body / script extraction for the Japanese-gate hook.

Routes a Claude Code `tool_input` payload to a single string of text
that downstream validators will scan. Two paths:
  - Bash: command + referenced body files + referenced scripts
  - MCP : structured `body` fields collected recursively

Returning `None` signals "skip the gate" (read-only / non-body tool).
"""

from __future__ import annotations

import os

from .patterns import (
    BODY_FIELDS,
    BODY_FILE_RE,
    BYPASS_MARKER,
    F_BODY_RE,
    GH_API_RE,
    GH_HIGH_RE,
    MCP_GH_RE,
    SCRIPT_RE,
)


def _has_bypass(text: str) -> bool:
    """Return True if the bypass marker is present in `text`."""
    return BYPASS_MARKER in text


def expand_body_path(raw, cwd):
    """Resolve `~`, env vars, and relative paths against the tool-call cwd."""
    path = os.path.expanduser(os.path.expandvars(raw))
    if not os.path.isabs(path) and cwd:
        path = os.path.join(cwd, path)
    return path


def read_body_files(command, cwd):
    """Return (concatenated_text, missing_paths) for every body file
    referenced by the command.

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
                    pieces.append(fh.read())
            except (OSError, ValueError):
                missing.append(raw)
                continue
    return "\n".join(pieces), missing


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
    """Return `inspect_text` for a Bash tool call, or `None` to skip the gate.

    Bypass marker is scoped to the command line, not the merged body/
    script text — the original idiom (matching the git pre-commit
    `MOJIEMOJI_HOOK_DISABLED=1 git commit ...` style) is an opt-in by
    the *invocation*, not by something happening to appear inside a
    referenced file. Once file/script bodies are merged into
    `inspect_text`, documentation prose or test fixtures that mention
    the literal marker would silently disable the gate — accidental
    bypass via benign mention. Keep the bypass check on `command` only.

    File-routed posts (`--body-file PATH` / `--input PATH` /
    `-F body=@PATH`) and interpreter-invoked scripts (`python3 X.py`
    etc.) are merged into `inspect_text` so dynamically-built bodies
    cannot bypass the regex inspection. See `read_body_files` /
    `read_script_files` for the file-side cwd resolution.
    """
    command = (data.get("tool_input", {}) or {}).get("command", "")
    if not command:
        return None
    if _has_bypass(command):
        return None
    if not (GH_HIGH_RE.search(command) or GH_API_RE.search(command)):
        return None
    cwd = data.get("cwd", "")
    file_body, _ = read_body_files(command, cwd)
    script_body = read_script_files(command, cwd)
    extras = "\n".join(p for p in (file_body, script_body) if p)
    return command + ("\n" + extras if extras else "")


def _route_mcp(tool_input: dict):
    """Return `inspect_text` for an MCP GitHub tool call, or `None` to skip.

    Multiple body pieces (e.g., `pull_request_review_write` with a
    top-level `body` summary plus `comments[].body` inline findings)
    are joined into a single `inspect_text` *on purpose*: the SKILL.md
    surface policy is "summary body decorated, inline findings
    un-stamped". A per-piece zero-stamp check would force stamps on
    each finding, contradicting that policy. Aggregating means a
    stamped summary covers un-stamped findings (correct), and a fully
    un-stamped submission still trips the aggregate zero-stamp check
    (correct). Each URL is still validated individually for required
    params / canonical values, so the aggregation only relaxes the
    zero-stamp coarse gate, not the per-URL fine gates.

    Bypass marker check happens AFTER body assembly because MCP path
    has no shell prefix; the only place a caller can legitimately opt
    out is inside the body text itself. The rule still parallels Bash
    (bypass on the surface the caller directly controls), just adapted
    to structured input.
    """
    pieces = collect_body_text(tool_input, BODY_FIELDS)
    if not pieces:
        return None
    inspect_text = "\n".join(pieces)
    if _has_bypass(inspect_text):
        return None
    return inspect_text


def extract_inspect_text(data: dict):
    """Dispatch to Bash / MCP routing. Returns inspect_text or `None`.

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
