---
name: mojiemoji-github
description: Copilot CLI adapter for decorating Japanese GitHub Markdown with the shared mojiemoji core.
---

<!-- mojiemoji-schema-version: 2.1.0 -->

# mojiemoji-github (Copilot CLI)

Use this skill when Copilot CLI prepares Japanese GitHub Markdown for issues,
pull requests, comments, reviews, or release notes.

## Core First

Preferred command:

```bash
uvx mojiemoji < body.md > decorated.md
```

Repository fallback:

```bash
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  < body.md > decorated.md
```

The decorated output should be passed to `gh` with `--body-file`, stdin, or
the equivalent GitHub API body field.

## Required Stamp Shape

Stamps must use `/emoji/<encoded-text>` and document these required
parameters: `font`, `color`, `animation`, `background`, `outline`, and
`outline_width`.

Inline defaults:

- `background=transparent`
- `outline_width=2`
- color examples: `a855f7`, `22c55e`, `f59e0b`, `06b6d4`, `f472b6`
- animation examples: `bane`, `bure`, `kirari`, `yoko_scroll`, `zairu`

## Pre-Submit Rule

Before a GitHub write command posts Japanese prose, check whether the text
already includes mojiemoji output. If not, run the core. Skip decoration for
explicit opt-out regions wrapped with `<!-- mojiemoji:off -->` and
`<!-- mojiemoji:on -->`.
