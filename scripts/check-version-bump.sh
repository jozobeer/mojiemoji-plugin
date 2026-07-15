#!/usr/bin/env bash
# Fail the CI if a PR modifies plugin source paths
# (.agents/, .claude-plugin/, plugins/, skills/, hooks/, agents/, commands/) without bumping
# `.claude-plugin/plugin.json` version. Claude Code's marketplace caches
# plugin contents by `<plugin>/<version>/...`, so changes shipped without
# a version bump never reach users via `/plugin update`.
#
# Usage (CI): set BASE_SHA and HEAD_SHA env vars; uses git ranges between
# them. Usage (local): runs with defaults `origin/main` and `HEAD`.

set -euo pipefail

BASE_SHA="${BASE_SHA:-origin/main}"
HEAD_SHA="${HEAD_SHA:-HEAD}"

SOURCE_PATHS=(
    ".agents/"
    ".claude-plugin/"
    "plugins/"
    "skills/"
    "hooks/"
    "agents/"
    "commands/"
)

# Diff from the merge-base so we only see changes introduced by this branch,
# not changes that landed on `main` after the branch diverged. Without this,
# a branch behind main can falsely be flagged for source changes that
# happened only on the base.
merge_base=$(git merge-base "$BASE_SHA" "$HEAD_SHA")
changed_files=$(git diff --name-only "$merge_base" "$HEAD_SHA")

# Prefix match via shell glob, NOT regex — `.claude-plugin/` as a regex
# would also match `Xclaude-plugin/` because `.` matches any character.
source_changed=0
while IFS= read -r file; do
    [ -z "$file" ] && continue
    for path in "${SOURCE_PATHS[@]}"; do
        if [[ "$file" == "$path"* ]]; then
            source_changed=1
            break 2
        fi
    done
done <<< "$changed_files"

if [ "$source_changed" -eq 0 ]; then
    echo "✓ No plugin source paths changed; version bump not required."
    exit 0
fi

base_version=$(git show "$merge_base:.claude-plugin/plugin.json" | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])")
head_version=$(git show "$HEAD_SHA:.claude-plugin/plugin.json" | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])")

if [ "$base_version" = "$head_version" ]; then
    echo "::error::Plugin source changed but .claude-plugin/plugin.json version not bumped (base=$base_version, head=$head_version)."
    echo "Bump the version field before merging — Claude Code caches by version, so unbumped releases never reach users via /plugin update."
    exit 1
fi

# Strict SemVer 2.0.0 validation — rejects leading zeros (`01.2.3`) and
# malformed prerelease identifiers (`-..`) that a loose regex would let through.
if ! python3 -c "
import re, sys
v = sys.argv[1]
pat = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?\$'
sys.exit(0 if re.match(pat, v) else 1)
" "$head_version"; then
    echo "::error::head version '$head_version' is not valid SemVer 2.0.0 (X.Y.Z[-prerelease][+build], no leading zeros)."
    exit 1
fi

echo "✓ Plugin version bumped: $base_version → $head_version"
