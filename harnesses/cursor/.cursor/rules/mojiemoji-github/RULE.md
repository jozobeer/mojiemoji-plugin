---
description: Decorate Japanese GitHub Markdown with mojiemoji before posting.
globs:
  - "**/*.md"
alwaysApply: false
---

# mojiemoji-github (Cursor Rule)

For Japanese GitHub Markdown, Cursor should call the shared mojiemoji core
before submitting an issue, PR, review, comment, or release note.

Preferred:

```bash
uvx mojiemoji < body.md > decorated.md
```

Fallback while working from this repository:

```bash
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  < body.md > decorated.md
```

The core is the source of truth. Do not copy catalogs or hand-build stamp
URLs unless the core is unavailable.

Every rendered stamp should use `/emoji/<encoded-text>` with `font`, `color`,
`animation`, `background`, `outline`, and `outline_width`. Inline output
should use `background=transparent` and `outline_width=2`.

Recommended values: colors `a855f7`, `22c55e`, `f59e0b`, `06b6d4`,
`f472b6`; animations `bane`, `bure`, `kirari`, `yoko_scroll`, `zairu`.

If a Japanese body is intentionally plain, wrap the plain region with
`<!-- mojiemoji:off -->` and `<!-- mojiemoji:on -->`.
