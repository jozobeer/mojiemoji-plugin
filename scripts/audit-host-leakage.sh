#!/usr/bin/env bash
#
# audit-host-leakage.sh — surface real "mojiemoji" references in host config.
#
# The plugin should be fully self-contained: installing via `/plugin install`
# is enough, no manual edits to ~/.config/claude. This script greps the host
# config for `mojiemoji` references, then filters out:
#   - the plugin clone itself (plugins/marketplaces/ and plugins/cache/)
#   - auto-generated artifacts (history, sessions, jobs, paste-cache, etc.)
#   - settings.json (plugin enable + marketplace registration — required for
#     the plugin to be active; can't be removed without disabling the plugin)
#   - plugins/installed_plugins.json and plugins/known_marketplaces.json
#     (auto-managed by Claude Code's plugin system; required for activation)
#
# What's left is "true leakage": host-side files that reference mojiemoji
# beyond what the plugin install requires. Ideally this list is empty.
#
# Usage:
#   scripts/audit-host-leakage.sh                       # default ~/.config/claude
#   scripts/audit-host-leakage.sh /custom/config/path   # override config dir
#
# Exit codes:
#   0 — no leakage detected
#   1 — leakage found (paths printed to stdout)
#   2 — invalid argument / config dir doesn't exist

set -euo pipefail

config_dir="${1:-${XDG_CONFIG_HOME:-$HOME/.config}/claude}"

if [[ ! -d "$config_dir" ]]; then
  printf 'audit: config dir not found: %s\n' "$config_dir" >&2
  exit 2
fi

# Filter pattern matches paths we expect to find mojiemoji in: plugin clone,
# auto-generated state, and the irreducible settings.json entries.
exclude_re='plugins/(cache|marketplaces)/|/projects/|/file-history/|/backups/|/todos/|/shell-snapshots/|/jobs/|/paste-cache/|/sessions/|/tasks/|\.jsonl$|/\.claude\.json$|/settings\.json$|/plugins/(installed_plugins|known_marketplaces)\.json$'

leakage=$(grep -ril mojiemoji "$config_dir" 2>/dev/null | grep -vE "$exclude_re" || true)

if [[ -z "$leakage" ]]; then
  printf 'audit: no mojiemoji leakage in %s\n' "$config_dir"
  exit 0
fi

printf 'audit: mojiemoji leakage detected in %s:\n' "$config_dir"
printf '%s\n' "$leakage" | while read -r path; do
  count=$(grep -c mojiemoji "$path" 2>/dev/null || echo 0)
  printf '  %s (%d ref(s))\n' "$path" "$count"
done
exit 1
