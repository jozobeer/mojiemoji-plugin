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

    python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
      < body.md > decorated.md

Rendered stamps must use `/emoji/<encoded-text>` and include the required
parameters `font`, `color`, `animation`, `background`, `outline`, and
`outline_width`. Inline stamps should use `background=transparent` and
`outline_width=2`.

Before any GitHub write call, verify that Japanese prose has already been
decorated or is intentionally inside `<!-- mojiemoji:off -->` /
`<!-- mojiemoji:on -->`.
```

Keep the `mojiemoji-schema-version` marker in sync with the canonical
`skills/mojiemoji-github/SKILL.md` — it is how the drift tooling knows
whether the copy is current.

Once the core package is published (#141), the preferred invocation becomes
`uvx mojiemoji < body.md > decorated.md` and the adapter no longer needs a
repository checkout.

## Python Runtime

The prestamp scripts read YAML catalogs, so the Python environment that
runs them needs PyYAML:

```bash
python3 -m pip install --user "pyyaml>=6.0"
```

From this repository, `uv run ...` already provides the dependency from
`pyproject.toml`.

## Drift Detection

Two mechanisms keep agy copies from silently going stale:

- `scripts/audit-harness-skills.sh` audits every deployed copy against five
  contracts (endpoint shape, required parameters, forbidden animations,
  forbidden colors, schema-version marker). Run it after updating the
  canonical skill.
- On the Claude Code side, the host gate's schema-version validator reads
  the marker in each agy copy and warns when it is behind the canonical
  `skills/mojiemoji-github/SKILL.md`.

## Current Limits

- agy sees only the adapter file; there is no equivalent of the Claude Code
  PreToolUse hook gate, so enforcement relies on the adapter's instructions.
- No installable package or marketplace entry yet — the adapter references
  scripts from a local checkout of this repository until the core carve-out
  (#141) publishes a standalone `mojiemoji` package.
- Hook parity is a separate phase because each harness exposes command/tool
  interception differently.
