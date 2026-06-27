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
  < body.md > decorated.md
```

Every harness adapter should apply the same rule: run this preprocessing
step before posting Japanese GitHub bodies.

## Update Strategy

The transformation rules and catalog are expected to change frequently. For
interactive harness use, adapters should prefer `uvx mojiemoji` so the latest
published core is used without copying files into each harness.

Pin versions only when reproducibility matters, such as CI snapshots or
historical re-renders:

```bash
uvx mojiemoji==X.Y.Z < body.md > decorated.md
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
- Run `prestamp.py` or `uvx mojiemoji` before GitHub submission.
- Keep gate behavior harness-local: Claude PreToolUse hooks do not exist
  in every harness, so Codex/Gemini/Cursor/Windsurf/etc. should reproduce
  the safety rule through their own skill, rule, terminal hook, MCP wrapper,
  or pre-submit workflow.

## Harness Map

| Harness | Reference path | Primary shape |
| --- | --- | --- |
| Grok | `harnesses/grok/mojiemoji-github/SKILL.md` | Skill |
| Codex | `harnesses/codex/mojiemoji-github/SKILL.md` | Skill |
| OpenCode | `harnesses/opencode/mojiemoji-github/SKILL.md` | Skill |
| Copilot CLI | `harnesses/copilot-cli/mojiemoji-github/SKILL.md` | Skill |
| Gemini | `harnesses/gemini/rules/mojiemoji-github.md` | Rule |
| Cursor | `harnesses/cursor/rules/mojiemoji-github.md` | Rule |
| Windsurf | `harnesses/windsurf/rules/mojiemoji-github.md` | Rule |

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
