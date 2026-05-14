#!/usr/bin/env bash
# verify-canonical-lists.sh — diff hook canonical lists against the live
# mojiemoji service. If the service adds a new font/animation or
# renames one, the hook's allowlist will silently reject it, so we
# need a way to detect drift.
#
# Exit 0 if both lists match the service exactly.
# Exit 1 if any drift is found (missing or unknown values).
# Prints unified diffs for whichever list drifted.

set -euo pipefail

SERVICE_URL="${MOJIEMOJI_BASE_URL:-https://mojiemoji.jozo.beer/}"
HOOK_PATH="${HOOK_PATH:-${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/../../..}/hooks/mojiemoji-japanese-gate.py}"

if [[ ! -f "$HOOK_PATH" ]]; then
    printf 'hook not found: %s\n' "$HOOK_PATH" >&2
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

# Extract the Python set literal `NAME = { ... }` from the hook by
# AST-walking string constants inside the matching Assign node, then
# printing one identifier per line, sorted unique.
extract_set() {
    local set_name="$1" file="$2"
    python3 - "$set_name" "$file" <<'PYEOF'
import ast, sys
name, path = sys.argv[1], sys.argv[2]
tree = ast.parse(open(path).read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == name:
                vals = sorted({
                    e.value for e in node.value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)
                })
                print("\n".join(vals))
                sys.exit(0)
sys.exit(1)
PYEOF
}

service_fonts="$tmpdir/service-fonts.txt"
service_anims="$tmpdir/service-anims.txt"
hook_fonts="$tmpdir/hook-fonts.txt"
hook_anims="$tmpdir/hook-anims.txt"

extract_options font-select      "$tmpdir/form.html" > "$service_fonts"
extract_options animation-select "$tmpdir/form.html" > "$service_anims"
extract_set CANONICAL_FONTS      "$HOOK_PATH" | sort -u > "$hook_fonts"
extract_set CANONICAL_ANIMATIONS "$HOOK_PATH" | sort -u > "$hook_anims"

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
        printf '    + %s\n' $only_service
    fi
    if [[ -n "$only_hook" ]]; then
        printf '  unknown to service (hook stale):\n'
        printf '    - %s\n' $only_hook
    fi
}

compare fonts      "$service_fonts" "$hook_fonts"
compare animations "$service_anims" "$hook_anims"

exit $drift
