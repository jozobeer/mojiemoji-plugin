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
  --surface issue-body < body.md > decorated.md
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
