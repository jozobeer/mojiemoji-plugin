---
trigger: model_decision
description: Decorate Japanese GitHub Markdown with mojiemoji before posting.
---

<!-- mojiemoji-schema-version: 2.1.0 -->

# mojiemoji-github (Windsurf Rule)

When Windsurf prepares Japanese GitHub prose, run the body through the
shared mojiemoji core before posting to GitHub.

Preferred command:

```bash
uvx mojiemoji < body.md > decorated.md
```

Repository fallback:

```bash
# --surface MUST match the posting target:
#   issue-body | pr-body | review-body | comment-body | release-note
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  --surface issue-body < body.md > decorated.md
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
