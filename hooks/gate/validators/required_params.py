"""Stage 2 — every mojiemoji URL must carry the full styling param set.

Color-shifting animations (`disco` / `psycho` / `kira`) are exempt
from outline / outline_width because a fixed-color outline fights the
hue cycle and looks dirty. All other URLs require the full 6-param
set; `mojiemoji_markdown.py` is the only sanctioned construction path.
"""
from __future__ import annotations

import re
import sys

from lib.constants import COLOR_SHIFTING_ANIMATIONS

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
