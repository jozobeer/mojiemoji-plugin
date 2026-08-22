# Cross-Harness mojiemoji Adapters

This directory contains thin, harness-specific adapters for using the
shared mojiemoji core from non-Claude AI harnesses.

## Architecture

```text
AI harness plugin / skill / rule
  -> mojiemoji core CLI or library
  -> decorated GitHub Markdown body
  -> harness-native posting path
```

The adapter layer must stay thin. It may describe when to run mojiemoji,
where to place a skill or rule file, and how to call the core. It must not
fork the catalog, animation list, color list, or URL rules.

## Core Invocation

Preferred path after the core package is published:

```bash
uvx mojiemoji < body.md > decorated.md
```

Repository fallback while the core package is still being carved out:

```bash
python3 /path/to/mojiemoji-plugin/skills/mojiemoji-github/scripts/prestamp.py \
  --surface issue-body < body.md > decorated.md
```

Pass the surface that matches the posting target (`issue-body`, `pr-body`,
`review-body`, `comment-body`, `release-note`). Every harness adapter should
apply the same rule: run this preprocessing step before posting Japanese
GitHub bodies.

## Update Strategy

The transformation rules and catalog are expected to change frequently. For
interactive harness use, adapters should prefer `uvx mojiemoji` so the latest
published core is used without copying files into each harness.

Pin versions only when reproducibility matters, such as CI snapshots or
historical re-renders:

```bash
uvx mojiemoji@X.Y.Z < body.md > decorated.md
```

Do not vendor the catalog into harness-specific plugins. If a harness needs a
long-lived local install, update it as part of the harness plugin update flow.

## Adapter Contract

Each adapter must preserve these contracts:

- Use the canonical `/emoji/<encoded-text>` endpoint.
- Document the required URL parameters: `font`, `color`, `animation`,
  `background`, `outline`, and `outline_width`.
- Prefer Tailwind 300-500 style colors such as `a855f7`, `22c55e`,
  `f59e0b`, `06b6d4`, and `f472b6`.
- Use canonical animation names such as `bane`, `bure`, `kirari`,
  `yoko_scroll`, and `zairu`.
- Run `prestamp.py` or `uvx mojiemoji` before GitHub submission, with the
  `--surface` flag matching the posting target.
- Keep gate behavior harness-local: Claude PreToolUse hooks do not exist
  in every harness, so Codex/Gemini/Cursor/Windsurf/etc. should reproduce
  the safety rule through their own skill, rule, terminal hook, MCP wrapper,
  or pre-submit workflow.
- Carry the non-automatable canonical policies (pr-body policy skip,
  color-shifting outline exception, sensitive-content skips, badge-first
  layout, show-and-confirm approval, decoration after prestamp) in the
  adapter text, and state that the canonical
  `skills/mojiemoji-github/SKILL.md` wins on disagreement.

## Harness Map

- Grok skill: `harnesses/grok/mojiemoji-github/SKILL.md`
- Codex skill: `harnesses/codex/mojiemoji-github/SKILL.md`
  (reference copy — Codex users should normally install the packaged
  plugin instead; see `docs/harnesses/codex.md`)
- OpenCode skill: `harnesses/opencode/mojiemoji-github/SKILL.md`
- Copilot CLI skill: `harnesses/copilot-cli/mojiemoji-github/SKILL.md`
- Gemini CLI skill:
  `harnesses/gemini/.gemini/skills/mojiemoji-github/SKILL.md`
- Cursor project rule:
  `harnesses/cursor/.cursor/rules/mojiemoji-github/RULE.md`
- Windsurf workspace rule:
  `harnesses/windsurf/.windsurf/rules/mojiemoji-github.md`
- agy: no checked-in adapter yet — deploy per the setup guide in
  `docs/harnesses/agy.md`

Per-harness setup guides with more context live in `docs/harnesses/`.

Run the repo reference audit after editing checked-in adapters:

```bash
MOJIEMOJI_AUDIT_SCOPE=repo scripts/audit-harness-skills.sh
```

To scan both checked-in adapters and local installed copies:

```bash
scripts/audit-harness-skills.sh
```

To inspect only local installed copies:

```bash
MOJIEMOJI_AUDIT_SCOPE=local scripts/audit-harness-skills.sh
```
