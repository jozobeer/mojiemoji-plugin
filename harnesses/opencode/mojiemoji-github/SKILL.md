---
name: mojiemoji-github
description: OpenCode adapter for routing Japanese GitHub Markdown through the shared mojiemoji core.
---

<!-- mojiemoji-schema-version: 2.1.0 -->

# mojiemoji-github (OpenCode)

Use this skill for Japanese GitHub issue bodies, PR bodies, review text,
review replies, comments, and release notes.

## Core First

Preferred:

```bash
uvx mojiemoji < body.md > decorated.md
```

Fallback from a checked-out plugin repo:

```bash
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  < body.md > decorated.md
```

Submit only the decorated Markdown unless the user intentionally asks for a
plain body.

## URL Contract

Use the canonical `/emoji/<encoded-text>` endpoint. Every stamp URL should
carry `font`, `color`, `animation`, `background`, `outline`, and
`outline_width`. For inline stamps, use `background=transparent` and
`outline_width=2`.

Recommended examples:

- colors: `a855f7`, `22c55e`, `f59e0b`, `06b6d4`, `f472b6`
- animations: `bane`, `bure`, `kirari`, `yoko_scroll`, `zairu`

## Harness Wiring

OpenCode should treat the core as a command-line preprocessor. Run
`prestamp.py` or `uvx mojiemoji` before `gh` submission and before GitHub MCP
write calls that include Japanese prose.
