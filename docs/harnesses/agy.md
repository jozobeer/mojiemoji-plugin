# Antigravity CLI (agy) Support

agy support is copy-based: a thin adapter skill or rule file placed in the
user's agy / Gemini configuration tree tells the harness to run the shared
mojiemoji core before posting Japanese GitHub Markdown. Unlike Codex, there
is no installable marketplace package yet — agy loads plain skill and rule
files from its config directories.

## Deployment Paths

The drift tooling (`scripts/audit-harness-skills.sh` and the host gate's
`hooks/gate/validators/schema_version.py`) watches these locations:

| Path | Kind |
|---|---|
| `~/.config/agy/skills/mojiemoji-github/SKILL.md` | skill |
| `~/.config/agy/rules/mojiemoji-github.md` | rule |
| `~/.gemini/skills/mojiemoji-github/SKILL.md` | skill |
| `~/.gemini/config/skills/mojiemoji-github/SKILL.md` | global skill |
| `~/.gemini/config/rules/mojiemoji-github.md` | rule |

Place the adapter at whichever path your agy installation discovers —
`~/.config/agy/` for a standalone agy setup, `~/.gemini/` when agy shares
the Gemini CLI configuration tree. One copy is enough; every existing copy
is audited, so stale duplicates only create drift noise.

## Adapter Skeleton

The adapter must stay thin: describe when to run mojiemoji and how to call
the core. It must not fork the catalog, animation list, color list, or <img src="https://mojiemoji.jozo.beer/emoji/URL?font=pixel&amp;color=f87171&amp;animation=ekken&amp;background=transparent&amp;outline=26dc26&amp;outline_width=2" alt="URL" height="20" align="absmiddle">
rules — those stay canonical in this repository.

```markdown
---
name: mojiemoji-github
description: agy adapter for decorating Japanese GitHub Markdown with the shared mojiemoji core.
---

<!-- mojiemoji-schema-version: 2.1.0 -->

# mojiemoji-github (agy)

When preparing Japanese GitHub Markdown for an issue, PR, review, comment,
or release note, run the text through the shared mojiemoji core before
posting:

    uvx mojiemoji < body.md > decorated.md

`uvx` resolves the `mojiemoji` distribution from PyPI on first use, so no
repository checkout and no manual install are involved.

PR bodies need one check the core does not perform: GitHub can copy the PR
body into squash / merge commit messages, and stamps must not leak into
commit history. Before decorating a PR body, run

    gh api 'repos/{owner}/{repo}' --jq '(.allow_squash_merge and .squash_merge_commit_message == "PR_BODY") or (.allow_merge_commit and .merge_commit_message == "PR_BODY")'

from inside the target repository, and when it prints `true`, post the PR
body undecorated — only an explicit user request overrides this. Every
other surface (issue body, review body, comment, release note) is
decorated unconditionally.

`prestamp.py` replaces catalog hits only and leaves every other phrase
unchanged. After running it, decorate the important Japanese phrases the
catalog missed yourself, following the canonical parameter rules, and
verify the assembled body before treating it as decorated — prestamp
output alone is not a finished decoration for prose the catalog does not
cover. Exception: when the repository-policy check above prints `true`,
leave the PR body unchanged — do not decorate it manually either. The
undecorated PR body is the intended final state there, and it passes the
pre-write check below as a skip.

The same preprocessing applies to local Markdown edits: after editing
Japanese prose in `README.md`, `CHANGELOG.md`, `docs/**/*.md`,
`agents/**/*.md`, or `skills/**/SKILL.md`, run the file through
`prestamp.py` too — repository CI fails a PR whose changed documentation
is not prestamp-clean. Wrap intentional raw regions in
`<!-- mojiemoji:off -->` / `<!-- mojiemoji:on -->`.

Rendered stamps must use `/emoji/<encoded-text>` and include the required
parameters `font`, `color`, `animation`, `background`, `outline`, and
`outline_width`. Inline stamps should use `background=transparent` and
`outline_width=2`. Exception: the color-shifting animations `disco`,
`psycho`, and `kira` omit `outline` and `outline_width` — a fixed halo
conflicts with their changing colors, and the core strips those parameters
for them.

Skip decoration entirely when the body is English-only, the surface is not
GitHub, or the content is an apology, a security advisory, legal or
compliance text, or standalone acceptance criteria — `prestamp.py` cannot
detect these semantic categories, so apply this exception before running
it. When unsure, decorate.

On body-class surfaces (issue body, PR body, release note), a shields.io
badge row must be the first element of the body. `prestamp.py` preserves
existing badges but never creates one — add the badge row to the draft
yourself before decorating.

Show the decorated draft to the user once and wait for an explicit yes/no
before posting; on a change request, re-decorate and show again. Never
post GitHub content that the user has not approved in this form.

Before any GitHub write call, verify that Japanese prose has already been
decorated, falls under a skip category above, or is intentionally inside
`<!-- mojiemoji:off -->` / `<!-- mojiemoji:on -->`.

For anything this adapter does not cover, the canonical
`skills/mojiemoji-github/SKILL.md` in the mojiemoji-plugin repository is
the authoritative workflow reference.
```

Keep the `mojiemoji-schema-version` marker in sync with the canonical
`skills/mojiemoji-github/SKILL.md` — it is how the drift tooling knows
whether the copy is current.

## Drift Detection

Two mechanisms keep agy copies from silently going stale:

- `scripts/audit-harness-skills.sh` audits every deployed copy against six
  contracts (endpoint shape, required parameters, forbidden animations,
  forbidden colors, a `uvx mojiemoji` reference, and a
  `mojiemoji-schema-version` marker matching the canonical skill's). Run it
  after updating the canonical skill. A copy without the marker now fails
  the audit, so deploy the adapter with its marker line intact.
- Schema-version drift is additionally caught by the host gate: on the
  Claude Code side, its validator reads the marker in each agy copy and
  warns when it is behind the canonical `skills/mojiemoji-github/SKILL.md`.

## Current Limits

- agy sees only the adapter file; there is no equivalent of the Claude Code
  PreToolUse hook gate, so enforcement relies on the adapter's instructions.
- No installable package or marketplace entry yet for the adapter itself —
  deploy the adapter file by hand at one of the paths above.
- Hook parity is a separate phase because each harness exposes command/tool
  interception differently.
