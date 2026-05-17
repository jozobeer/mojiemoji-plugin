"""Stage 3 — outline value must be `darker` / `lighter` / 6-hex."""

from __future__ import annotations

import re
import sys

from ..patterns import OUTLINE_VALUE_RE


def validate_outline_values(urls) -> int:
    """Uppercase hex / non-hex garbage is rejected to keep URLs
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
