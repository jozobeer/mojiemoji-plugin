#!/usr/bin/env bash
# verify-lists-vs-service.sh — diff `lib/constants.py` canonical lists
# against the live mojiemoji service HTML. If the service adds a new
# font/animation or renames one, the allowlist will silently reject it,
# so we need a way to detect drift.
#
# Pre-#101 the script extracted from `hooks/mojiemoji_japanese_gate.py`.
# #101 made `lib/constants.py` the SSOT and the hook validators import
# from it directly, so the lib copy is now the single source to compare
# against the service.
#
# Renamed from verify-canonical-lists.sh in #54 item 7 — sibling
# `scripts/verify-lists-vs-docs.sh` checks lib against in-repo
# parameters.md; this one checks against the live service.
#
# Exit 0 if both lists match the service exactly.
# Exit 1 if any drift is found (missing or unknown values).
# Prints unified diffs for whichever list drifted.

set -euo pipefail

SERVICE_URL="${MOJIEMOJI_BASE_URL:-https://mojiemoji.jozo.beer/}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CLAUDE_PLUGIN_ROOT:-$SCRIPT_DIR/../../..}"
# `LIB_CONSTANTS_PATH` is the SSOT for canonical sets after #101.
# `HOOK_PATH` is kept as a fallback for callers that still set it.
LIB_CONSTANTS_PATH="${LIB_CONSTANTS_PATH:-${HOOK_PATH:-$REPO_ROOT/skills/mojiemoji-github/scripts/lib/constants.py}}"
EXTRACT="${EXTRACT_HOOK_SET:-$REPO_ROOT/scripts/extract_hook_set.py}"

if [[ ! -f "$LIB_CONSTANTS_PATH" ]]; then
    printf 'lib/constants.py not found: %s\n' "$LIB_CONSTANTS_PATH" >&2
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
lib_fonts="$tmpdir/lib-fonts.txt"
lib_anims="$tmpdir/lib-anims.txt"

extract_options font-select      "$tmpdir/form.html" > "$service_fonts"
extract_options animation-select "$tmpdir/form.html" > "$service_anims"
python3 "$EXTRACT" CANONICAL_FONTS      "$LIB_CONSTANTS_PATH" | sort -u > "$lib_fonts"
python3 "$EXTRACT" CANONICAL_ANIMATIONS "$LIB_CONSTANTS_PATH" | sort -u > "$lib_anims"

drift=0

compare() {
    local label="$1" service="$2" lib="$3"
    local sc lc only_service only_lib
    sc=$(wc -l < "$service" | tr -d ' ')
    lc=$(wc -l < "$lib" | tr -d ' ')
    only_service=$(comm -23 "$service" "$lib")
    only_lib=$(comm -13 "$service" "$lib")

    if [[ -z "$only_service" && -z "$only_lib" ]]; then
        printf '[ok] %s — %s entries match\n' "$label" "$sc"
        return 0
    fi

    drift=1
    printf '[drift] %s — service=%s lib=%s\n' "$label" "$sc" "$lc"
    if [[ -n "$only_service" ]]; then
        printf '  missing from lib (service adds):\n'
        while IFS= read -r entry; do
            printf '    + %s\n' "$entry"
        done <<< "$only_service"
    fi
    if [[ -n "$only_lib" ]]; then
        printf '  unknown to service (lib stale):\n'
        while IFS= read -r entry; do
            printf '    - %s\n' "$entry"
        done <<< "$only_lib"
    fi
}

compare fonts      "$service_fonts" "$lib_fonts"
compare animations "$service_anims" "$lib_anims"

exit $drift
