# mojiemoji-github (Gemini Rule)

When Gemini prepares Japanese GitHub Markdown for an issue, PR, review,
comment, or release note, run the text through the shared mojiemoji core
before posting.

Preferred:

```bash
uvx mojiemoji < body.md > decorated.md
```

Fallback from this repository:

```bash
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  < body.md > decorated.md
```

Rendered stamps must use `/emoji/<encoded-text>` and include the required
parameters `font`, `color`, `animation`, `background`, `outline`, and
`outline_width`. Inline stamps should use `background=transparent` and
`outline_width=2`.

Use readable colors such as `a855f7`, `22c55e`, `f59e0b`, `06b6d4`, and
`f472b6`. Use canonical animations such as `bane`, `bure`, `kirari`,
`yoko_scroll`, and `zairu`.

Before any `gh` or GitHub MCP write call, verify that Japanese prose has
already been decorated or is intentionally inside `<!-- mojiemoji:off -->` /
`<!-- mojiemoji:on -->`.
