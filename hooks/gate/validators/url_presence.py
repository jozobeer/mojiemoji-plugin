"""Stage 1 — every Japanese body must include at least one mojiemoji URL.

The error message walks the agent through the canonical recovery path
(skill / subagent / helper script) and the legitimate skip cases so
the failure is self-documenting rather than just a refusal.
"""
from __future__ import annotations

import sys


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
        "1. skill: 引数なしで `Skill(mojiemoji-github)` を明示的に呼び出す\n"
        "2. body全体に inline-saturated でrender (1〜2 stamps/段落, grammatically natural)\n"
        "3. animation 12+ distinct values, 同一値≤2×, color 4+ distinct, dark-mode-safe (Tailwind 300–500 — 600+ は禁止)\n"
        "4. API名 / 英識別子 / file path / version string / コードシンボル はstamp化しない\n"
        "5. shields.io badges を line 1 に置く (stampはその下)\n"
        "6. 再render後に同じ投稿経路 (gh / MCP) を再実行\n"
        "\n"
        "## subagent 経路 (複数フレーズ / skill 未登録時)\n"
        "subagent: `Agent` ツールで `subagent_type: \"mojiemoji-selector\"` を指定する。\n"
        "注意: `mojiemoji-github:mojiemoji-selector` は agent list の表示形で、Skill ツールには渡せない。\n"
        "\n"
        "## helper script 経路 (Skill / Agent ツール非サポート時)\n"
        "tool 隔離で `Skill` / `Agent` が使えないなら、helper script を直接叩いて URL を生成し本文に embed:\n"
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
