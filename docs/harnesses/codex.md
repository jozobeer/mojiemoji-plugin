# Codex CLI support

This repository exposes the mojiemoji plugin to Codex through:

- `.agents/plugins/marketplace.json`
- `.codex-plugin/plugin.json`
- `skills/`
- `plugins/mojiemoji-plugin/`

Codex support is currently skills-only. The Claude Code PreToolUse gate in
`hooks/` is intentionally not declared in the Codex manifest because Codex
plugin ingestion rejects unsupported `hooks` fields.

The marketplace entry points at `plugins/mojiemoji-plugin/`, which contains a
real copy of `.codex-plugin/` and `skills/`. Codex recognizes that layout and
copies the skill files into its plugin cache during install. Keep the package
copy synchronized with:

```bash
scripts/sync-codex-plugin-package.sh
scripts/sync-codex-plugin-package.sh --check
```

## Install from GitHub

```bash
codex plugin marketplace add jozobeer/mojiemoji-plugin
codex plugin list --marketplace mojiemoji-plugin --available
codex plugin add mojiemoji-plugin@mojiemoji-plugin
```

## Install from a local checkout

```bash
git clone https://github.com/jozobeer/mojiemoji-plugin.git ~/mojiemoji-plugin
codex plugin marketplace add ~/mojiemoji-plugin
codex plugin list --marketplace mojiemoji-plugin --available
codex plugin add mojiemoji-plugin@mojiemoji-plugin
```

## Verify

```bash
codex plugin list --available --json
```

The output should include the `mojiemoji-plugin` plugin from the
`mojiemoji-plugin` marketplace. Start a new Codex thread after installation so
the `mojiemoji-github` skill is loaded into the session.

## Current limits

- Codex sees the skill bundle.
- Codex does not run the Claude Code hook gate.
- Hook parity is a separate phase because each harness exposes command/tool
  interception differently.
