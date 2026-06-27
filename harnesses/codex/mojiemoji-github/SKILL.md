---
name: mojiemoji-github
description: GitHub issue / PR / review / release bodies for Codex should run through the shared mojiemoji core before posting Japanese Markdown.
---

<!-- mojiemoji-schema-version: 2.1.0 -->

# mojiemoji-github (Codex)

Use this skill when Codex is preparing Japanese GitHub Markdown for an
issue, PR, review, review reply, issue comment, or release note.

## Core First

Run the shared core before posting:

```bash
uvx mojiemoji < body.md > decorated.md
```

Until the core package is published, use the repository fallback:

```bash
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  < body.md > decorated.md
```

Paste or pipe the decorated output into the GitHub command. Do not hand-build
stamp URLs when the core can render them.

## Required URL Contract

Rendered stamps must use `/emoji/<encoded-text>` and include:

- `font`
- `color`
- `animation`
- `background=transparent`
- `outline`
- `outline_width=2`

Good inline colors include `a855f7`, `22c55e`, `f59e0b`, `06b6d4`, and
`f472b6`. Good animations include `bane`, `bure`, `kirari`, `yoko_scroll`,
and `zairu`.

## Gate Behavior

Before any `gh issue`, `gh pr`, `gh release`, `gh api`, or GitHub MCP call
that posts a Japanese body, verify that the body has either already been
decorated or intentionally opts out with `<!-- mojiemoji:off -->` /
`<!-- mojiemoji:on -->`.

For PR bodies, follow the repository policy before decorating. If the repo
copies PR body HTML into commit messages, leave the body plain unless the
user explicitly requests decorated PR body output.
