#!/usr/bin/env bash
# verify-lists-vs-service.sh — diff hook canonical lists against the
# live mojiemoji service HTML. If the service adds a new font/animation
# or renames one, the hook's allowlist will silently reject it, so we
# need a way to detect drift.
#
# Renamed from verify-canonical-lists.sh in #54 item 7 — sibling
# `scripts/verify-lists-vs-docs.sh` checks the hook against the
# in-repo parameters.md; this one checks against the live service.
#
# Exit 0 if both lists match the service exactly.
# Exit 1 if any drift is found (missing or unknown values).
# Prints unified diffs for whichever list drifted.

set -euo pipefail

SERVICE_URL="${MOJIEMOJI_BASE_URL:-https://mojiemoji.jozo.beer/}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CLAUDE_PLUGIN_ROOT:-$SCRIPT_DIR/../../..}"
HOOK_PATH="${HOOK_PATH:-$REPO_ROOT/hooks/mojiemoji_japanese_gate.py}"
EXTRACT="${EXTRACT_HOOK_SET:-$REPO_ROOT/scripts/extract_hook_set.py}"

if [[ ! -f "$HOOK_PATH" ]]; then
    printf 'hook not found: %s\n' "$HOOK_PATH" >&2
    exit 2
fi
if [[ ! -f "$EXTRACT" ]]; then
    printf 'extract_hook_set.py not found: %s\n' "$EXTRACT" >&2
    exit 2
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

curl -sfL "$SERVICE_URL" -o "$tmpdir/form.html" || {
    printf 'failed to fetch %s\n' "$SERVICE_URL" >&2
    exit 2
}

# Extract option values for a given <select id="...">.
extract_options() {
    local select_id="$1" html="$2"
    awk -v id="$select_id" '
        BEGIN { RS = "<select" }
        $0 ~ "id=\"" id "\"" {
            sub(/<\/select>.*/, "")
            while (match($0, /value="[^"]*"/)) {
                v = substr($0, RSTART + 7, RLENGTH - 8)
                if (v != "") print v
                $0 = substr($0, RSTART + RLENGTH)
            }
            exit
        }
    ' "$html" | sort -u
}

service_fonts="$tmpdir/service-fonts.txt"
service_anims="$tmpdir/service-anims.txt"
hook_fonts="$tmpdir/hook-fonts.txt"
hook_anims="$tmpdir/hook-anims.txt"

extract_options font-select      "$tmpdir/form.html" > "$service_fonts"
extract_options animation-select "$tmpdir/form.html" > "$service_anims"
python3 "$EXTRACT" CANONICAL_FONTS      "$HOOK_PATH" | sort -u > "$hook_fonts"
python3 "$EXTRACT" CANONICAL_ANIMATIONS "$HOOK_PATH" | sort -u > "$hook_anims"

drift=0

compare() {
    local label="$1" service="$2" hook="$3"
    local sc hc only_service only_hook
    sc=$(wc -l < "$service" | tr -d ' ')
    hc=$(wc -l < "$hook" | tr -d ' ')
    only_service=$(comm -23 "$service" "$hook")
    only_hook=$(comm -13 "$service" "$hook")

    if [[ -z "$only_service" && -z "$only_hook" ]]; then
        printf '[ok] %s — %s entries match\n' "$label" "$sc"
        return 0
    fi

    drift=1
    printf '[drift] %s — service=%s hook=%s\n' "$label" "$sc" "$hc"
    if [[ -n "$only_service" ]]; then
        printf '  missing from hook (service adds):\n'
        while IFS= read -r entry; do
            printf '    + %s\n' "$entry"
        done <<< "$only_service"
    fi
    if [[ -n "$only_hook" ]]; then
        printf '  unknown to service (hook stale):\n'
        while IFS= read -r entry; do
            printf '    - %s\n' "$entry"
        done <<< "$only_hook"
    fi
}

compare fonts      "$service_fonts" "$hook_fonts"
compare animations "$service_anims" "$hook_anims"

exit $drift
