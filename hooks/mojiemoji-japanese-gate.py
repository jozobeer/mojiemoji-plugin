#!/usr/bin/env python3
"""PreToolUse hook: gate Japanese GitHub body submissions without properly-styled mojiemoji stamps.

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
for MCP that's the body itself. The legacy name `HOOK_DISABLE=1` is
still honored for now but emits a deprecation notice; it will be
removed in a future minor release.
"""
import json
import os
import re
import sys
import urllib.parse

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
# Legacy bypass marker. Honored for now but emits a deprecation notice
# on use; will be removed in a future minor release (target: 1.0).
LEGACY_BYPASS_MARKER = "HOOK_DISABLE=1"


def _has_bypass(text: str) -> bool:
    """Return True if any bypass marker is present in `text`. Prints a
    deprecation notice to stderr when only the legacy marker is found,
    so callers can migrate before legacy support is dropped."""
    if BYPASS_MARKER in text:
        return True
    if LEGACY_BYPASS_MARKER in text:
        sys.stderr.write(
            "mojiemoji-japanese-gate: `HOOK_DISABLE=1` is deprecated. "
            "Use `MOJIEMOJI_HOOK_DISABLED=1` instead — the legacy name "
            "will be removed in a future release.\n"
        )
        return True
    return False
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
# Required style parameters on every URL. Missing any of these = unreadable
# stamp on dark-mode GitHub (default mojiemoji is black-on-white).
#
# `outline=` / `outline_width=` are conditionally required: skipped when
# the animation cycles colors (disco / psycho) because a fixed-color
# outline fights the rainbow effect and looks dirty. The outline value
# itself is also more permissive than the original hard `outline=darker`
# — `darker`, `lighter`, and arbitrary hex (used by --outline triadic /
# complement in the helper script) all count as "outline specified".
REQUIRED_PARAMS_ALWAYS = [
    ("background=transparent", "白背景ブロックを防ぐ (服務必須)"),
    ("font=", "文字が読みやすい canonical font の指定 (gothic-bold / maru-bold / noto / dela / akzk 等)"),
    ("color=", "ダークモードで見える色 (Tailwind 300–500 range の hex)"),
    ("animation=", "canonical な animation (bane / bure / kira / gatagata / yurayura 等 — 詳細は parameters.md)"),
]
REQUIRED_PARAMS_OUTLINE = [
    ("outline=", "letterform を縁取り (darker / lighter / 6-hex — triadic outline は補色から自動算出)"),
    ("outline_width=", "outline 幅 (推奨 2px、`mojiemoji_markdown.py --outline-width 2`)"),
]
COLOR_SHIFTING_ANIMATIONS = {"disco", "psycho", "kira"}
# Rotational animations spin the letterform around its center. At the
# service default speed (effectively `fast`), and at explicit `normal`
# / `fast`, the spin completes faster than the eye can resolve the
# glyph — it reads as a streak of pixels, not text. Only `step`
# (frame-by-frame) and `slow` keep the rotation readable.
#
# Scope is intentionally conservative: `kaiten` (rotation) and
# `kage_kaiten` (its shadow variant — same rotation, different render
# layer). The translational group (`tate_scroll` / `yoko_scroll` /
# `nami` / `tatemoya` / `yokomoya`) moves the glyph but doesn't spin
# it; their fast-speed readability is borderline rather than clearly
# broken, so they're excluded until visually verified (see issue #12
# review notes).
ROTATIONAL_ANIMATIONS = {"kaiten", "kage_kaiten"}
ROTATIONAL_OK_SPEEDS = {"step", "slow"}
# Canonical value allowlists. The mojiemoji service silently falls back to
# defaults (or static rendering) when an unknown font/animation is passed
# — no error, no visible signal. The 2026-05-12 PR #1768 incident shipped
# `font=fude` (invented), `animation=poyon` (typo for poyoon), and
# `animation=funwari` (invented) — all rendered as the service default
# (plain font, no animation), defeating the styling intent. Substring
# presence checks (`font=`/`animation=`) pass these through; only value
# allowlisting catches them.
#
# Source of truth: `${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/references/parameters.md`
# § "Valid font values" / § "Valid animation values".
CANONICAL_FONTS = {
    "gothic", "gothic-bold", "maru", "maru-bold", "mincho", "dela", "akzk",
    "zero", "kurobara", "hachimaru", "chikara", "tamanegi", "pixel", "toge",
    "rampart", "noto",
}
CANONICAL_ANIMATIONS = {
    "tate_scroll", "yoko_scroll", "ekken", "tate_ekken", "bane", "gatagata",
    "bure", "chuuou_zoom", "kirari", "kira", "tenmetsu", "shuchusen",
    "kaiten", "neruneru", "patapata", "yurayura", "mabataki", "bakusan",
    "norinori", "mochimochi", "mozaiku", "poyoon", "yatta", "tatemoya",
    "nami", "yokomoya", "zairu", "zanzo", "chirichiri", "disco", "psycho",
    "kage_kaiten", "kage_bokashi", "kage_neon",
}
# Outline can be the keyword `darker` / `lighter` (service-side auto)
# or any 6-digit hex (when derived from --outline triadic / complement
# in the helper). Lowercase enforced; uppercase hex rejected so URLs
# remain canonicalized.
OUTLINE_VALUE_RE = re.compile(r"\A(?:darker|lighter|[0-9a-f]{6})\Z")
# Color must be a 6-digit hex value with optional leading `#`. Named
# palettes (`vivid-purple`, `red`, etc.) silently fall back to default
# black on the service side, producing invisible stamps on dark mode.
# Lowercase enforced for URL canonicalization, matching OUTLINE_VALUE_RE.
# The hue-rotation logic in `mojiemoji_markdown.py` also requires hex —
# named colors break `--outline triadic` / `complement` derivation too.
COLOR_VALUE_RE = re.compile(r"\A#?[0-9a-f]{6}\Z")
# Tailwind 600+ palette values that go black-on-dark in GitHub's dark
# theme. PR #33 shipped 6 stamps with `dc2626` (red-600) and ate the
# fill into the dark background; selector / verification.md spotcheck
# #4 enumerate these as forbidden, but the hook accepted them until
# this gate was added (issue #41 — 3-layer alignment).
#
# Lowercase, no `#` prefix — match what comes out of PARAM_VALUE_RE
# after normalization.
FORBIDDEN_COLORS = frozenset({
    "dc2626", "b91c1c", "991b1b",        # red-600/700/800
    "c2410c",                            # orange-700
    "ca8a04",                            # yellow-600
    "15803d", "16a34a",                  # green-700/600
    "0e7490",                            # cyan-700
    "1d4ed8", "2563eb",                  # blue-700/600
    "4338ca",                            # indigo-700
    "7e22ce",                            # purple-700
    "be185d",                            # pink-700
    "000000", "111827", "1f2937",        # black / gray-900/800
})
# Single-stamp text decoded from `/emoji/<encoded>` consisting of
# **3+ contiguous CJK kanji**. SKILL.md § Stamp target selection caps
# single stamps at 2 kanji because 3+ chars get visually crushed at
# inline height (h=24). Selector contract + verification spotcheck
# #16 already require `2+1` split (e.g., `致命傷` → `致命` + `傷`),
# but hand-crafted URLs and selector slip-throughs reach the hook
# untouched. CJK Unified Ideographs U+4E00–U+9FFF only — hiragana /
# katakana / latin / digits all skip this check (the kanji crush is
# specifically a high-stroke-count problem).
KANJI_ONLY_RE = re.compile(r"\A[一-鿿]+\Z")
EMOJI_PATH_RE = re.compile(r"/emoji/([^?\s\"<>)]+)")
# Extract param values from a URL fragment. Handles both `&` and `&amp;`
# separators (the latter when URLs sit inside HTML attribute strings),
# trailing quotes/whitespace, and URL fragments. Stops at the next param
# delimiter or value-ending char. The value charset includes `%` so
# URL-encoded prefixes (`%23` for `#`) are captured rather than skipped
# silently — those should be rejected, not invisible to the validator.
PARAM_VALUE_RE = re.compile(
    r"(?:&amp;|&|\?)(font|animation|color)=([a-z0-9_#%-]+)",
    re.IGNORECASE,
)


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


def validate_url_presence(urls) -> int:
    """Stage 1 — body must contain ≥1 mojiemoji URL."""
    if urls:
        return 0
    sys.stderr.write(
        "🚧 mojiemoji-github skill未適用のまま日本語GitHub bodyを送ろうとしています\n"
        "\n"
        "検出: 日本語 GitHub body に `mojiemoji.jozo.beer` の stamp が 0 個。\n"
        "autonomous実行 / subagent内 / skill chain漏れの典型パターン。\n"
        "\n"
        "## 推奨経路 (skill access があるなら)\n"
        "1. `mojiemoji-github` スキルを `Skill` ツールで明示的に呼び出す\n"
        "2. body全体に inline-saturated でrender (1〜2 stamps/段落, grammatically natural)\n"
        "3. animation 12+ distinct values, 同一値≤2×, color 4+ distinct, dark-mode-safe (Tailwind 300–500 — 600+ は禁止)\n"
        "4. API名 / 英識別子 / file path / version string / コードシンボル はstamp化しない\n"
        "5. shields.io badges を line 1 に置く (stampはその下)\n"
        "6. 再render後に同じ投稿経路 (gh / MCP) を再実行\n"
        "\n"
        "## subagent 経路 (Skill ツール非サポート時 / skill 未登録時)\n"
        "subagent 隔離で `Skill` ツールが使えないなら、helper script を直接叩いて URL を生成し本文に embed:\n"
        "\n"
        "```bash\n"
        "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/scripts/mojiemoji_markdown.py\" \\\n"
        "  --text 修正 --inline \\\n"
        "  --font gothic-bold --color 22c55e --animation bane \\\n"
        "  --outline triadic --outline-width 2\n"
        "```\n"
        "\n"
        "(`--inline` で `<img ... height=\"24\" align=\"absmiddle\">` 形式を出力。background はデフォルトで `transparent`、outline は明示指定が必要。font / color / animation の正準値は\n"
        "`${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/references/parameters.md` 参照。)\n"
        "\n"
        "## skip 正当ケース\n"
        "English-only / apology / security / legal / compliance / acceptance criteria\n"
        "緊急bypass: Bash なら command 先頭、MCP なら body 内に `MOJIEMOJI_HOOK_DISABLED=1` を含める\n"
        "\n"
        "詳細: ${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/SKILL.md\n"
    )
    return 2


def _required_params_for(url) -> list:
    """Pick the per-URL required-param set based on animation kind.

    Outline params are exempt when the animation cycles colors
    (`disco` / `psycho` / `kira`) because a fixed-color outline
    fights the rainbow effect; the helper script
    `--outline triadic|complement` auto-drops outline + outline_width
    on those animations.
    """
    anim_match = re.search(r"(?:&amp;|&|\?)animation=([a-z0-9_-]+)", url, re.IGNORECASE)
    anim = anim_match.group(1).lower() if anim_match else ""
    if anim in COLOR_SHIFTING_ANIMATIONS:
        return REQUIRED_PARAMS_ALWAYS
    return REQUIRED_PARAMS_ALWAYS + REQUIRED_PARAMS_OUTLINE


def validate_required_params(urls) -> int:
    """Stage 2 — every mojiemoji URL MUST carry the full styling param set.

    `scripts/mojiemoji_markdown.py` is the only sanctioned construction
    path — hand-crafted URLs systematically miss color / font /
    animation / outline and ship as invisible black-on-dark stamps.
    Block here so the agent learns the lesson at submission time, not
    when the user opens the rendered PR.
    """
    violations = []  # list of (url, [missing_param_label, ...])
    for u in urls:
        required = _required_params_for(u)
        missing = [label for label, _ in required if label not in u]
        if missing:
            violations.append((u, missing))

    if not violations:
        return 0

    preview_lines = []
    for u, missing in violations[:5]:
        short = u[:140] + ("…" if len(u) > 140 else "")
        preview_lines.append(f"  - {short}\n    missing: {', '.join(missing)}")
    preview = "\n".join(preview_lines)
    more = f"\n  …他 {len(violations) - 5} 件" if len(violations) > 5 else ""
    param_reference = "\n".join(
        f"  - `{label}` — {why}"
        for label, why in (REQUIRED_PARAMS_ALWAYS + REQUIRED_PARAMS_OUTLINE)
    )
    sys.stderr.write(
        "🚧 mojiemoji URL に必須スタイルパラメータが欠落しています\n"
        "\n"
        f"検出: 計 {len(urls)} 件のうち {len(violations)} 件で必須パラメータ欠落。\n"
        "ダークモード GitHub では文字色が黒のまま表示されて読めません。\n"
        "\n"
        "## 必須パラメータ一覧\n"
        f"{param_reference}\n"
        "  (※ animation=disco/psycho/kira は色循環するため outline 系を省略可)\n"
        "\n"
        "## 欠落URL (最初の5件)\n"
        f"{preview}{more}\n"
        "\n"
        "## 対応\n"
        "1. **絶対にURLを手書きしない** — `mojiemoji-github` スキル経由か\n"
        "   `mojiemoji-selector` subagent に投げて、ヘルパースクリプト\n"
        "   `scripts/mojiemoji_markdown.py` 経由で全パラメータ付きでレンダー\n"
        "2. 既存 URL を直すなら参考形 (triadic outline 自動算出):\n"
        "   https://mojiemoji.jozo.beer/emoji/<text>?font=gothic-bold\n"
        "     &color=3b82f6&animation=bane&speed=normal\n"
        "     &background=transparent&outline=triadic&outline_width=2\n"
        "3. font / color / animation のリストは\n"
        "   `${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/references/parameters.md`\n"
        "4. 再投稿前に `references/verification.md` の grep #2〜#5 で全件確認\n"
        "\n"
        "緊急bypass: Bash command先頭 / MCP body 内に `MOJIEMOJI_HOOK_DISABLED=1` を含める (推奨しない、ダーク不可視のまま投稿される)\n"
    )
    return 2


def validate_outline_values(urls) -> int:
    """Stage 3 — outline value must be `darker` / `lighter` / 6-hex.

    Uppercase hex / non-hex garbage is rejected to keep URLs
    canonicalized. `triadic` / `complement` aren't valid runtime
    values — those are helper-script directives that get resolved to
    a literal hex before URL emission.
    """
    outline_invalid = []
    for u in urls:
        m = re.search(r"(?:&amp;|&|\?)outline=([^&\"\s]+)", u)
        if not m:
            continue
        val = m.group(1)
        if not OUTLINE_VALUE_RE.match(val):
            outline_invalid.append((u, val))
    if not outline_invalid:
        return 0

    preview_lines = []
    for u, val in outline_invalid[:5]:
        short = u[:140] + ("…" if len(u) > 140 else "")
        preview_lines.append(f"  - {short}\n    outline={val!r} (allowed: darker | lighter | 6-hex)")
    preview = "\n".join(preview_lines)
    sys.stderr.write(
        "🚧 mojiemoji URL の outline 値が不正です\n"
        "\n"
        "outline は `darker` / `lighter` (service auto) または 6-digit hex のみ\n"
        "(triadic / complement モードは helper script が hex に変換)\n"
        "\n"
        "## 違反URL\n"
        f"{preview}\n"
        "\n"
        "緊急bypass: Bash command先頭 / MCP body 内に `MOJIEMOJI_HOOK_DISABLED=1` を含める\n"
    )
    return 2


def _scan_canonical_violations(url) -> list:
    """Return list of (label, value) tuples describing per-URL bad values.

    Walks `PARAM_VALUE_RE` matches and adds violations for:
    - non-canonical font / animation
    - non-hex / Tailwind-600+ color
    - 3-kanji single stamp (split required as 2+1)
    - color-shifting animation paired with explicit outline
    - rotational animation without `speed=step|slow`
    """
    bads = []
    anim_value = ""
    for param, value in PARAM_VALUE_RE.findall(url):
        param_l = param.lower()
        value_l = value.lower()
        if param_l == "animation":
            anim_value = value_l
        if param_l == "font" and value_l not in CANONICAL_FONTS:
            bads.append((param_l, value))
        elif param_l == "animation" and value_l not in CANONICAL_ANIMATIONS:
            bads.append((param_l, value))
        elif param_l == "color" and not COLOR_VALUE_RE.match(value_l):
            bads.append((param_l, value))
        elif param_l == "color" and value_l.lstrip("#") in FORBIDDEN_COLORS:
            bads.append((
                "color-tailwind-600+",
                f"{value} (Tailwind 600+ — invisible on dark mode; swap to 300–500)",
            ))
    # 3-kanji single stamp — selector contract + verification.md
    # spotcheck #16 require `2+1` split because 3+ kanji at inline
    # height (h=24) get visually crushed. `urllib.parse.unquote`
    # handles `%E…` UTF-8 byte sequences cleanly. `%0A` (newline)
    # inside the path = 2-line stamp for hiragana; split on it and
    # check the first segment only — kanji words don't use `%0A`
    # per SKILL.md, so a 3+ kanji string in any segment is the
    # single-stamp violation.
    emoji_match = EMOJI_PATH_RE.search(url)
    if emoji_match:
        decoded = urllib.parse.unquote(emoji_match.group(1))
        first_segment = decoded.split("\n", 1)[0]
        if KANJI_ONLY_RE.match(first_segment) and len(first_segment) >= 3:
            bads.append((
                "3-kanji-single",
                f"'{first_segment}' (split as 2+1 — e.g., 致命傷 → 致命 + 傷)",
            ))
    # Color-shifting animations cycle the fill through rainbow / strobe
    # colors. A fixed-color outline halo fights the cycle and produces
    # a dirty composite. The helper script auto-drops outline +
    # outline_width for these; hand-crafted URLs keep them and look
    # wrong. Flag the combination as invalid.
    if anim_value in COLOR_SHIFTING_ANIMATIONS and "outline=" in url:
        bads.append(("animation+outline", f"{anim_value} with outline"))
    # Rotational animations are only readable at speed=step|slow.
    # Capture the full value up to the next URL/HTML delimiter — not
    # just the leading alphabetic prefix — otherwise typos like
    # `speed=step2` or partially-encoded `speed=slow%20` would slice
    # down to `step` / `slow` and pass the check while the actual
    # service receives a non-canonical value that falls back to the
    # unreadable default. Same delimiter set as MOJI_URL_RE so the
    # capture stops at the URL boundary inside HTML attributes.
    if anim_value in ROTATIONAL_ANIMATIONS:
        speed_match = re.search(
            r"(?:&amp;|&|\?)speed=([^&\s\"<>)]+)", url, re.IGNORECASE
        )
        speed = speed_match.group(1).lower() if speed_match else ""
        if speed not in ROTATIONAL_OK_SPEEDS:
            got = speed if speed else "(missing — defaults to fast)"
            bads.append((
                "animation+speed",
                f"{anim_value} requires speed=step|slow, got {got}",
            ))
    return bads


def validate_canonical_values(urls) -> int:
    """Stage 4 — non-canonical fonts / animations / colors and related
    composite-rule violations.

    The mojiemoji service silently falls back to defaults (or static
    rendering) when an unknown font/animation is passed — no error, no
    visible signal. Substring presence checks pass these through; only
    value allowlisting catches them. See `_scan_canonical_violations`
    for the per-URL rule set.
    """
    invalid = []  # list of (url, [(param, bad_value), ...])
    for u in urls:
        bads = _scan_canonical_violations(u)
        if bads:
            invalid.append((u, bads))

    if not invalid:
        return 0

    preview_lines = []
    for u, bads in invalid[:5]:
        short = u[:140] + ("…" if len(u) > 140 else "")
        bad_str = ", ".join(f"{p}={v!r}" for p, v in bads)
        preview_lines.append(f"  - {short}\n    invalid: {bad_str}")
    preview = "\n".join(preview_lines)
    more = f"\n  …他 {len(invalid) - 5} 件" if len(invalid) > 5 else ""
    sys.stderr.write(
        "🚧 mojiemoji URL に存在しない font/animation/color 値が指定されています\n"
        "\n"
        f"検出: 計 {len(urls)} 件のうち {len(invalid)} 件で canonical 外の値。\n"
        "mojiemoji サービスは未知の値を silent fallback (デフォルト font /\n"
        "static rendering / black color) するため、エラーは出ませんが意図した\n"
        "スタイルで render されません。\n"
        "\n"
        f"## Canonical font 一覧 ({len(CANONICAL_FONTS)}種)\n"
        f"  {', '.join(sorted(CANONICAL_FONTS))}\n"
        "\n"
        f"## Canonical animation 一覧 ({len(CANONICAL_ANIMATIONS)}種)\n"
        f"  {', '.join(sorted(CANONICAL_ANIMATIONS))}\n"
        "\n"
        "## Color 形式\n"
        "  6-digit hex (省略可な `#` prefix付き)、Tailwind 300-500 range 推奨。\n"
        "  named palette (`vivid-purple`, `red` 等) はサービス側で silent\n"
        "  fallback されダークモードで黒不可視になる。\n"
        "\n"
        "## 違反URL (最初の5件)\n"
        f"{preview}{more}\n"
        "\n"
        "## 対応\n"
        "1. `mojiemoji-selector` subagent または `mojiemoji_markdown.py`\n"
        "   ヘルパー経由で render し直す (推奨)\n"
        "2. URL を手で書き換える場合は上記 allowlist から選ぶ\n"
        "3. typo の典型: `poyon` → `poyoon`, `funwari` (存在しない) →\n"
        "   `yurayura` / `mochimochi`, `fude` (存在しない) → `mincho`\n"
        "   / `noto`; `vivid-purple` (named) → `c084fc` (hex);\n"
        "   `animation=kira`/`disco`/`psycho` は色循環するので outline\n"
        "   と outline_width は付けない (rainbow vs fixed halo の競合);\n"
        "   `animation=kaiten`/`kage_kaiten` は **必ず `speed=slow` か\n"
        "   `speed=step` を付ける** (省略 / `normal` / `fast` は回転が\n"
        "   速すぎて読めない streak になる — helper script は速度未指定時\n"
        "   に自動で `slow` を注入する);\n"
        "   color は **Tailwind 300–500 帯のみ** — `dc2626` (red-600) /\n"
        "   `1d4ed8` (blue-700) / `000000` (黒) 等の 600+ や near-black は\n"
        "   ダークモードで背景に溶けて読めなくなるため hook で reject;\n"
        "   `/emoji/<text>` の text 部分は **漢字 2 字以下の単独 stamp** —\n"
        "   `致命傷` のような 3 漢字単独は `致命` + `傷` の 2 stamp に分割\n"
        "   (selector subagent と verification.md spotcheck #16 と同じ規約)\n"
        "4. 詳細: `${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/references/parameters.md`\n"
        "\n"
        "緊急bypass: Bash command先頭 / MCP body 内に `MOJIEMOJI_HOOK_DISABLED=1` を含める\n"
    )
    return 2


# Validation stage pipeline. Each stage returns 2 + writes stderr on
# violation, 0 otherwise. First failure short-circuits.
VALIDATION_PIPELINE = (
    validate_url_presence,
    validate_required_params,
    validate_outline_values,
    validate_canonical_values,
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
