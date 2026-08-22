"""Stage 4 — non-canonical font / animation / color and related composite rules.

The mojiemoji service silently falls back to defaults (or static
rendering) when an unknown font/animation is passed — no error, no
visible signal. Substring presence checks pass these through; only
value allowlisting catches them. This module also enforces composite
rules:

- color-shifting animation paired with outline (visual conflict)
- rotational animation without `speed=step|slow` (unreadable streak)
- 3-kanji single-stamp text (must split as 2+1 per SKILL.md)
- Tailwind 600+ color (invisible on dark mode)
"""
from __future__ import annotations

import re
import sys
import urllib.parse

from lib.constants import (
    CANONICAL_ANIMATIONS,
    CANONICAL_FONTS,
    COLOR_SHIFTING_ANIMATIONS,
    FORBIDDEN_COLORS,
    ROTATIONAL_ANIMATIONS,
)

from lib.plugin_root import plugin_root

# Rotational animations spin the letterform around its center. At the
# service default speed (effectively `fast`), and at explicit `normal`
# / `fast`, the spin completes faster than the eye can resolve the
# glyph — it reads as a streak of pixels, not text. Only `step`
# (frame-by-frame) and `slow` keep the rotation readable.
ROTATIONAL_OK_SPEEDS = frozenset({"step", "slow"})
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
    root = plugin_root()
    sys.stderr.write(
        "🚧 mojiemoji URL に存在しない font/animation/color 値が指定されています\n"
        "\n"
        f"検出: 計 {len(urls)} 件のうち {len(invalid)} 件で canonical 外の値。\n"
        "未知の font / animation はサービス側で silent fallback (デフォルト font /\n"
        "static rendering) されるため、エラーは出ませんが意図したスタイルで\n"
        "render されません。color の不整合挙動は下記 # Color 形式 セクション参照。\n"
        "\n"
        f"## Canonical font 一覧 ({len(CANONICAL_FONTS)}種)\n"
        f"  {', '.join(sorted(CANONICAL_FONTS))}\n"
        "\n"
        f"## Canonical animation 一覧 ({len(CANONICAL_ANIMATIONS)}種)\n"
        f"  {', '.join(sorted(CANONICAL_ANIMATIONS))}\n"
        "\n"
        "## Color 形式\n"
        "  6-digit hex (省略可な `#` prefix付き)、Tailwind 300-500 range 推奨。\n"
        "  named palette (`red` / `teal` / `vivid-purple` 等) は使用禁止 — サービス側の\n"
        "  受理が不整合 (一部は 200、一部は 400) で、たまたま 200 を引いても\n"
        "  Tailwind 帯から外れダークモードで黒不可視になる (#110)。\n"
        "\n"
        "## 違反URL (最初の5件)\n"
        f"{preview}{more}\n"
        "\n"
        "## 対応\n"
        "1. skill access があるなら `Skill(mojiemoji-github)` を引数なしで起動して render し直す\n"
        "2. subagent に任せるなら `Agent` ツールで `subagent_type: \"mojiemoji-github:mojiemoji-selector\"` を指定\n"
        "   (※ 環境により bare `mojiemoji-selector` のみ解決する場合がある — エラー時はもう一方の形を試す。どちらも Skill ツールには渡せない)\n"
        f"3. tool 隔離時は `{root}/skills/mojiemoji-github/scripts/mojiemoji_markdown.py` ヘルパー経由で render し直す\n"
        "4. URL を手で書き換える場合は上記 allowlist から選ぶ\n"
        "5. typo の典型: `poyon` → `poyoon`, `funwari` (存在しない) →\n"
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
        f"6. 詳細: `{root}/skills/mojiemoji-github/references/parameters.md`\n"
        "\n"
        "緊急bypass: Bash command先頭 / MCP body 内に `MOJIEMOJI_HOOK_DISABLED=1` を含める\n"
    )
    return 2
