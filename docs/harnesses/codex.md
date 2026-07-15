# Codex CLI Support

This repository keeps the Codex marketplace source and package in:

- `.agents/plugins/marketplace.json`
- `skills/` (canonical skill sources)
- `plugins/mojiemoji-plugin/.codex-plugin/plugin.json`
- `plugins/mojiemoji-plugin/skills/` (filtered package copy)

There is intentionally no root `.codex-plugin/plugin.json`. The legacy Claude
marketplace points at the repository root, and a root Codex manifest would make
that unfiltered source tree appear as a second Codex plugin.

Codex support is currently skills-only. The Claude Code PreToolUse gate in
`hooks/` is intentionally not declared in the Codex manifest because Codex
plugins do not share Claude's hook surface.

The marketplace entry points at `plugins/mojiemoji-plugin/`, which contains a
real copy of `.codex-plugin/` and `skills/`. Codex recognizes that layout and
copies the skill files into its plugin cache during install. Keep the package
copy synchronized with:

```bash
scripts/sync-codex-plugin-package.sh
scripts/sync-codex-plugin-package.sh --check
```

The Codex package includes only skills that work from the installed plugin
cache. Source-maintenance skills such as `bump-catalog`, and Claude-only
delegation skills such as `mojiemoji-propose`, stay in the source tree.

## Install From GitHub

In the Codex app, add this repository address as a marketplace source:

```text
https://github.com/jozobeer/mojiemoji-plugin
```

The equivalent CLI flow is:

```bash
codex plugin marketplace add jozobeer/mojiemoji-plugin
codex plugin list --marketplace mojiemoji-plugin --available --json
codex plugin add mojiemoji-plugin@mojiemoji-plugin
```

## Install From A Local Checkout

```bash
git clone https://github.com/jozobeer/mojiemoji-plugin.git ~/mojiemoji-plugin
cd ~/mojiemoji-plugin
codex plugin marketplace add ~/mojiemoji-plugin
codex plugin list --marketplace mojiemoji-plugin --available --json
codex plugin add mojiemoji-plugin@mojiemoji-plugin
```

## Python Runtime

The packaged prestamp scripts read YAML catalogs, so the Python environment
that runs them needs PyYAML. In a plain local Codex environment, install it
once:

```bash
python3 -m pip install --user "pyyaml>=6.0"
```

From this repository, `uv run ...` already provides the dependency from
`pyproject.toml`.

## Verify

```bash
codex plugin list --available --json
```

The output should include the `mojiemoji-plugin` plugin from the
`mojiemoji-plugin` marketplace. Start a new Codex thread after installation so
the `mojiemoji-github` skill is loaded into the session.

## Current Limits

- Codex sees the skill bundle.
- Codex does not run the Claude Code hook gate.
- Codex does not currently package the `mojiemoji-selector` subagent, so
  the packaged skill uses its direct-script fallback and `mojiemoji-propose`
  remains source-tree only.
- `bump-catalog` remains source-tree only because it intentionally edits the
  canonical repository and cannot operate on an installed cache.
- Hook parity is a separate phase because each harness exposes command/tool
  interception differently.
