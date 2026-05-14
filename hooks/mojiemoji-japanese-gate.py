#!/usr/bin/env python3
"""PreToolUse hook: gate Japanese GitHub body submissions without properly-styled mojiemoji stamps.

Fires on two posting paths:
  1. Bash tool with `gh` posting the body:
     - `gh (issue|pr|release) (create|comment|review)` (high-level), OR
     - `gh api .../reviews|comments|issues|releases ...` (raw REST POST,
       used by skills like cross-repo-review that batch-publish reviews).
  2. MCP GitHub tools (`mcp__*__github_*`) whose `tool_input` carries
     a Japanese `body` / `description` field — covers
     `github_create_pull_request`, `github_add_issue_comment`,
     `github_pull_request_review_write`, `github_issue_write`,
     `github_update_pull_request`, `github_add_comment_to_pending_review`,
     `github_add_reply_to_pull_request_comment`, and any future MCP
     surface that uses the same field names. Title / commit_message /
     file content are intentionally NOT inspected — only body-class
     prose, matching the SKILL.md decoration policy.

And EITHER:
  1. inspected text has zero `mojiemoji.jozo.beer` URLs, OR
  2. at least one mojiemoji URL is missing any of the required style
     parameters (`background=transparent`, `font=*`, `color=*`,
     `animation=*`, `outline=darker`, `outline_width=2`), OR
  3. a URL uses a non-canonical font/animation, an invalid outline
     value, or pairs a color-shifting animation with an outline.

The Bash path also reads referenced body files (`--body-file PATH` /
`--input PATH` / `-F body=@PATH`) and interpreter-invoked scripts so
file-routed / dynamically-built bodies are covered too.

When triggered, blocks the tool call (exit 2) and prints reminder to
stderr so Claude sees it before submission. Bypass: include
`HOOK_DISABLE=1` anywhere in the inspected text — for Bash that's the
command line (prefix idiom matches the git pre-commit hook), for MCP
that's the body itself.
"""
import json
import os
import re
import sys

JP_RE = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")
# High-level `gh` commands that publish bodies.
GH_HIGH_RE = re.compile(r"gh\s+(issue|pr|release)\s+(create|comment|review)")
# Raw REST POSTs that skills like cross-repo-review use to publish reviews,
# comments, issues, or releases. We match the resource segment so we don't
# fire on GET / read-only calls.
GH_API_RE = re.compile(
    r"gh\s+api\b[^\n]*?/(?:reviews|comments|issues|pulls/\d+/(?:reviews|comments)|releases)\b"
)
STAMP_MARKER = "mojiemoji.jozo.beer"
BYPASS_MARKER = "HOOK_DISABLE=1"
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
# Match any MCP tool with `github` in the name — read-only tools
# (`github_get_*`, `github_list_*`, `github_search_*`) carry no body
# field, so body extraction returns empty and the gate exits 0.
MCP_GH_RE = re.compile(r"^mcp__.*github", re.IGNORECASE)
# Body-class fields across the MCP GitHub tool family. Title /
# commit_message / file content are excluded — they are conventionally
# undecorated per SKILL.md (titles short, commit messages plain).
BODY_FIELDS = frozenset({"body", "description"})
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
    ("outline_width=", "outline 幅 (推奨 2px、`mojiemoji_markdown.rb --outline-width 2`)"),
]
COLOR_SHIFTING_ANIMATIONS = {"disco", "psycho", "kira"}
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
# The hue-rotation logic in `mojiemoji_markdown.rb` also requires hex —
# named colors break `--outline triadic` / `complement` derivation too.
COLOR_VALUE_RE = re.compile(r"\A#?[0-9a-f]{6}\Z")
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


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not command:
            return 0
        if not (GH_HIGH_RE.search(command) or GH_API_RE.search(command)):
            return 0
        # Combine the command line with any referenced body files so
        # file-routed posting paths (`--body-file PATH` / `--input
        # PATH` / `-F body=@PATH`) are subject to the same regex
        # inspection as inline `--body` heredocs. Also inspect script
        # files invoked by interpreter (`python3 X.py` etc.) — the
        # 2026-05-12 triage-review bypass embedded hand-crafted URLs
        # in a Python helper that wrote the JSON body in the same
        # bash call as the `gh api --input` POST.
        cwd = data.get("cwd", "")
        file_body, _ = read_body_files(command, cwd)
        script_body = read_script_files(command, cwd)
        extras = "\n".join(p for p in (file_body, script_body) if p)
        inspect_text = command + ("\n" + extras if extras else "")
    elif MCP_GH_RE.match(tool_name):
        # MCP GitHub tools deliver structured input — extract body /
        # description fields directly. Title / commit_message / file
        # content are intentionally not inspected (see BODY_FIELDS
        # docstring). Read-only MCP tools (get_*, list_*, search_*)
        # match the regex but carry no body field, so this returns
        # empty and the gate exits.
        pieces = collect_body_text(tool_input, BODY_FIELDS)
        if not pieces:
            return 0
        inspect_text = "\n".join(pieces)
    else:
        return 0

    if BYPASS_MARKER in inspect_text:
        return 0

    if not JP_RE.search(inspect_text):
        return 0

    urls = MOJI_URL_RE.findall(inspect_text)
    if not urls:
        sys.stderr.write(
            "🚧 mojiemoji-github skill未適用のまま日本語GitHub bodyを送ろうとしています\n"
            "\n"
            "検出: 日本語 GitHub body に `mojiemoji.jozo.beer` の stamp が 0 個。\n"
            "autonomous実行 / subagent内 / skill chain漏れの典型パターン。\n"
            "\n"
            "## 対応\n"
            "1. `mojiemoji-github` スキルを `Skill` ツールで明示的に呼び出す\n"
            "2. body全体に inline-saturated でrender (1〜2 stamps/段落, grammatically natural)\n"
            "3. animation 8+ distinct values, 同一値≤3×, color 4+ distinct, dark-mode-safe (Tailwind 300–500)\n"
            "4. API名 / 英識別子 / file path / version string / コードシンボル はstamp化しない\n"
            "5. shields.io badges を line 1 に置く (stampはその下)\n"
            "6. 再render後に同じ投稿経路 (gh / MCP) を再実行\n"
            "\n"
            "## skip 正当ケース\n"
            "English-only / apology / security / legal / compliance / acceptance criteria\n"
            "緊急bypass: Bash なら command 先頭、MCP なら body 内に `HOOK_DISABLE=1` を含める\n"
            "\n"
            "詳細: ${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/SKILL.md\n"
        )
        return 2

    # Every mojiemoji URL MUST carry the full styling param set.
    # `scripts/mojiemoji_markdown.rb` is the only sanctioned construction
    # path — hand-crafted URLs systematically miss color/font/animation/
    # outline and ship as invisible black-on-dark stamps. Block here so the
    # agent learns the lesson at submission time, not when the user opens
    # the rendered PR.
    #
    # Outline params are exempt when the animation cycles colors
    # (`disco` / `psycho` / `kira`) because a fixed-color outline fights
    # the rainbow effect. The helper script `--outline triadic|complement`
    # auto-drops outline + outline_width on those animations.
    def required_for(url):
        # Determine if this URL's animation is in the color-shifting set.
        anim_match = re.search(r"(?:&amp;|&|\?)animation=([a-z0-9_-]+)", url, re.IGNORECASE)
        anim = anim_match.group(1).lower() if anim_match else ""
        if anim in COLOR_SHIFTING_ANIMATIONS:
            return REQUIRED_PARAMS_ALWAYS
        return REQUIRED_PARAMS_ALWAYS + REQUIRED_PARAMS_OUTLINE

    violations = []  # list of (url, [missing_param_label, ...])
    for u in urls:
        required = required_for(u)
        missing = [label for label, _ in required if label not in u]
        if missing:
            violations.append((u, missing))

    if violations:
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
            "   `scripts/mojiemoji_markdown.rb` 経由で全パラメータ付きでレンダー\n"
            "2. 既存 URL を直すなら参考形 (triadic outline 自動算出):\n"
            "   https://mojiemoji.jozo.beer/emoji/<text>?font=gothic-bold\n"
            "     &color=3b82f6&animation=bane&speed=normal\n"
            "     &background=transparent&outline=triadic&outline_width=2\n"
            "3. font / color / animation のリストは\n"
            "   `${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/references/parameters.md`\n"
            "4. 再投稿前に `references/verification.md` の grep #2〜#5 で全件確認\n"
            "\n"
            "緊急bypass: Bash command先頭 / MCP body 内に `HOOK_DISABLE=1` を含める (推奨しない、ダーク不可視のまま投稿される)\n"
        )
        return 2

    # Outline value validity: when outline IS present, the value must be
    # `darker`, `lighter`, or a 6-hex value (the latter is what triadic /
    # complement modes in the helper script emit). Uppercase hex / non-hex
    # garbage is rejected to keep URLs canonicalized.
    outline_invalid = []
    for u in urls:
        m = re.search(r"(?:&amp;|&|\?)outline=([^&\"\s]+)", u)
        if not m:
            continue
        val = m.group(1)
        if not OUTLINE_VALUE_RE.match(val):
            outline_invalid.append((u, val))
    if outline_invalid:
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
            "緊急bypass: Bash command先頭 / MCP body 内に `HOOK_DISABLE=1` を含める\n"
        )
        return 2

    # Value canonicality: the service silently falls back to default
    # (or static rendering) when font/animation aren't recognized.
    # `font=fude`, `animation=poyon` (typo), `animation=funwari`
    # (invented) all PASS the substring presence check above but defeat
    # the styling intent. Catch them here against the canonical
    # allowlists.
    invalid = []  # list of (url, [(param, bad_value), ...])
    for u in urls:
        bads = []
        anim_value = ""
        for param, value in PARAM_VALUE_RE.findall(u):
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
        # Color-shifting animations (disco/psycho/kira) cycle the fill
        # through rainbow/strobe colors. A fixed-color outline halo fights
        # the cycle and produces a dirty composite. The helper script
        # auto-drops outline+outline_width for these; hand-crafted URLs
        # keep them and look wrong. Flag the combination as invalid.
        if anim_value in COLOR_SHIFTING_ANIMATIONS and "outline=" in u:
            bads.append(("animation+outline", f"{anim_value} with outline"))
        if bads:
            invalid.append((u, bads))

    if invalid:
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
            "1. `mojiemoji-selector` subagent または `mojiemoji_markdown.rb`\n"
            "   ヘルパー経由で render し直す (推奨)\n"
            "2. URL を手で書き換える場合は上記 allowlist から選ぶ\n"
            "3. typo の典型: `poyon` → `poyoon`, `funwari` (存在しない) →\n"
            "   `yurayura` / `mochimochi`, `fude` (存在しない) → `mincho`\n"
            "   / `noto`; `vivid-purple` (named) → `c084fc` (hex);\n"
            "   `animation=kira`/`disco`/`psycho` は色循環するので outline\n"
            "   と outline_width は付けない (rainbow vs fixed halo の競合)\n"
            "4. 詳細: `${CLAUDE_PLUGIN_ROOT}/skills/mojiemoji-github/references/parameters.md`\n"
            "\n"
            "緊急bypass: Bash command先頭 / MCP body 内に `HOOK_DISABLE=1` を含める\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
