---
trigger: model_decision
description: Decorate Japanese GitHub Markdown with mojiemoji before posting.
---

# mojiemoji-github (Windsurf Rule)

When Windsurf prepares Japanese GitHub prose, run the body through the
shared mojiemoji core before posting to GitHub.

Preferred command:

```bash
uvx mojiemoji < body.md > decorated.md
```

Repository fallback:

```bash
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  < body.md > decorated.md
```

Use this before `gh issue`, `gh pr`, `gh release`, `gh api`, or a GitHub MCP
write call that includes Japanese Markdown.

Stamp URLs must use `/emoji/<encoded-text>`. Required parameters are `font`,
`color`, `animation`, `background`, `outline`, and `outline_width`. Inline
stamps should set `background=transparent` and `outline_width=2`.

Good color examples: `a855f7`, `22c55e`, `f59e0b`, `06b6d4`, `f472b6`.
Good animation examples: `bane`, `bure`, `kirari`, `yoko_scroll`, `zairu`.

Opt out only with explicit `<!-- mojiemoji:off -->` /
`<!-- mojiemoji:on -->` markers around the plain region.
