# Codex CLI Support

This repository exposes the mojiemoji plugin to Codex through:

- `.agents/plugins/marketplace.json`
- `.codex-plugin/plugin.json`
- `skills/`
- `plugins/mojiemoji-plugin/`

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

## Install From GitHub

Use `dev/multi-harness` while the cross-harness work is staged outside `main`:

```bash
codex plugin marketplace add jozobeer/mojiemoji-plugin --ref dev/multi-harness
codex plugin list --marketplace mojiemoji-plugin --available
codex plugin add mojiemoji-plugin@mojiemoji-plugin
```

After the integration branch is merged to `main`, the `--ref` flag can be
omitted.

## Install From A Local Checkout

```bash
git clone https://github.com/jozobeer/mojiemoji-plugin.git ~/mojiemoji-plugin
cd ~/mojiemoji-plugin
git switch dev/multi-harness
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

## Current Limits

- Codex sees the skill bundle.
- Codex does not run the Claude Code hook gate.
- Hook parity is a separate phase because each harness exposes command/tool
  interception differently.
