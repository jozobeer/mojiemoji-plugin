---
name: mojiemoji-github
description: Gemini CLI adapter for decorating Japanese GitHub Markdown with the shared mojiemoji core.
---

<!-- mojiemoji-schema-version: 2.1.0 -->

# mojiemoji-github (Gemini CLI)

When Gemini prepares Japanese GitHub Markdown for an issue, PR, review,
comment, or release note, run the text through the shared mojiemoji core
before posting.

Preferred:

```bash
uvx mojiemoji < body.md > decorated.md
```

Fallback from this repository:

```bash
# --surface MUST match the posting target:
#   issue-body | pr-body | review-body | comment-body | release-note
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  --surface issue-body < body.md > decorated.md
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

## Canonical Policies

These policies mirror the canonical skill and are not automated in this
harness, so apply them by hand:

- Pass the surface that matches the posting target: `--surface issue-body`,
  `pr-body`, `review-body`, `comment-body`, or `release-note`. With
  `--surface pr-body`, prestamp intentionally outputs the input unchanged
  when the target repository copies PR body HTML into merge commit
  messages; when that skip fires, do not decorate the PR body manually
  either.
- Color-shifting animations (`kira` / `disco` / `psycho`) must omit
  `outline` and `outline_width`; a fixed-color outline fights the hue
  cycle. All other animations keep the full six-parameter set.
- Skip decoration entirely for English-only bodies and for apology,
  security, legal, compliance, and acceptance-criteria text.
- Keep shields.io badge rows as the first line of the body; stamps start
  below them.
- prestamp output is the mechanical first pass (catalog hits only). Add
  inline decoration for the remaining phrases afterwards, then show the
  decorated body to the user and get confirmation before posting.

When this adapter and the canonical skill disagree, the canonical
`skills/mojiemoji-github/SKILL.md` in the plugin repository wins.
