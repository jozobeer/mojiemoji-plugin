---
name: mojiemoji-github
description: OpenCode adapter for routing Japanese GitHub Markdown through the shared mojiemoji core.
---

<!-- mojiemoji-schema-version: 2.1.0 -->

# mojiemoji-github (OpenCode)

Use this skill for Japanese GitHub issue bodies, PR bodies, review text,
review replies, comments, and release notes.

## Core First

Run the published core before posting:

```bash
uvx mojiemoji < body.md > decorated.md
```

`uvx` resolves the `mojiemoji` distribution from PyPI on first use, so no
repository checkout and no manual install are involved. Paste or pipe the
decorated output into the GitHub command. Do not hand-build stamp URLs when the
core can render them.

PR bodies need one check the core does not perform: GitHub can copy the PR body
into squash / merge commit messages, and stamps must not leak into commit
history. Before decorating a PR body, run

```bash
gh api 'repos/{owner}/{repo}' --jq '(.allow_squash_merge and .squash_merge_commit_message == "PR_BODY") or (.allow_merge_commit and .merge_commit_message == "PR_BODY")'
```

from inside the target repository, and when it prints `true`, post the PR body
undecorated — only an explicit user request overrides this. Every other surface
(issue body, review body, comment, release note) is decorated unconditionally.

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
`uvx mojiemoji` before `gh` submission and before GitHub MCP write calls that
include Japanese prose.

## Canonical Policies

These policies mirror the canonical skill and are not automated in this
harness, so apply them by hand:

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
