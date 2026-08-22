---
description: Decorate Japanese GitHub Markdown with mojiemoji before posting.
globs:
  - "**/*.md"
alwaysApply: false
---

<!-- mojiemoji-schema-version: 2.1.0 -->

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
  --surface issue-body < body.md > decorated.md
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
