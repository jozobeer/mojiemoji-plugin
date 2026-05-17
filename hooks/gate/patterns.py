"""Hook-specific regex patterns and constant definitions.

Hook-internal-only constants live here. Cross-script constants
(CANONICAL_FONTS / CANONICAL_ANIMATIONS / COLOR_SHIFTING_ANIMATIONS /
ROTATIONAL_ANIMATIONS / FORBIDDEN_COLORS) live in
`skills/mojiemoji-github/scripts/lib/constants.py` and are re-exported
here so consumer modules import them via a single path.
"""

from __future__ import annotations

import re

from . import _scripts_path  # noqa: F401 — side-effect: sys.path injection
from lib.constants import (  # type: ignore[import-not-found]
    CANONICAL_ANIMATIONS,
    CANONICAL_FONTS,
    COLOR_SHIFTING_ANIMATIONS,
    FORBIDDEN_COLORS,
    ROTATIONAL_ANIMATIONS,
)


__all__ = [
    "JP_RE", "GH_HIGH_RE", "GH_API_RE", "STAMP_MARKER", "BYPASS_MARKER",
    "MOJI_URL_RE", "BODY_FILE_RE", "F_BODY_RE", "SCRIPT_RE", "MCP_GH_RE",
    "BODY_FIELDS", "REQUIRED_PARAMS_ALWAYS", "REQUIRED_PARAMS_OUTLINE",
    "ROTATIONAL_OK_SPEEDS", "OUTLINE_VALUE_RE", "COLOR_VALUE_RE",
    "KANJI_ONLY_RE", "EMOJI_PATH_RE", "PARAM_VALUE_RE",
    "CANONICAL_FONTS", "CANONICAL_ANIMATIONS",
    "COLOR_SHIFTING_ANIMATIONS", "ROTATIONAL_ANIMATIONS",
    "FORBIDDEN_COLORS",
]


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
ROTATIONAL_OK_SPEEDS = {"step", "slow"}
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
