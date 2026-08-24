#!/usr/bin/env bash
# Fail the CI if a PR modifies plugin source paths
# (.agents/, .claude-plugin/, packages/, plugins/, skills/, hooks/, agents/,
# commands/) without bumping
# `.claude-plugin/plugin.json` version. Claude Code's marketplace caches
# plugin contents by `<plugin>/<version>/...`, so changes shipped without
# a version bump never reach users via `/plugin update`.
#
# The published `mojiemoji` core needs the same guarantee for a different
# reason: its release workflow triggers on its own version changing, so a
# core edit merged without one is never published at all — plugin users get
# the vendored copy while every PyPI user stays on the old release,
# indefinitely and silently. Hence a second, independent check below.
#
# Usage (CI): set BASE_SHA and HEAD_SHA env vars; uses git ranges between
# them. Usage (local): runs with defaults `origin/main` and `HEAD`.

set -euo pipefail

BASE_SHA="${BASE_SHA:-origin/main}"
HEAD_SHA="${HEAD_SHA:-HEAD}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
read_version() { "$script_dir/read-version.py" "$@"; }

CORE_VERSION_FILE="packages/mojiemoji-core/pyproject.toml"
# Everything the wheel carries. Tests live in the same directory but ship
# only in the sdist's test payload, so editing them is not a release.
CORE_PUBLISHABLE_PREFIX="packages/mojiemoji-core/"
CORE_EXEMPT_PREFIX="packages/mojiemoji-core/tests/"

SOURCE_PATHS=(
    ".agents/"
    ".claude-plugin/"
    # The core is vendored into the Codex payload, so its sources reach
    # users through the plugin just like `skills/` does.
    "packages/"
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

# Strict SemVer 2.0.0 validation — rejects leading zeros (`01.2.3`) and
# malformed prerelease identifiers (`-..`) that a loose regex would let through.
assert_semver() {
    local version="$1" label="$2"
    if ! python3 -c "
import re, sys
v = sys.argv[1]
pat = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?\$'
sys.exit(0 if re.match(pat, v) else 1)
" "$version"; then
        echo "::error::$label version '$version' is not valid SemVer 2.0.0 (X.Y.Z[-prerelease][+build], no leading zeros)."
        return 1
    fi
}

base_version=$(read_version .claude-plugin/plugin.json --ref "$merge_base")
head_version=$(read_version .claude-plugin/plugin.json --ref "$HEAD_SHA")

if [ "$base_version" = "$head_version" ]; then
    echo "::error::Plugin source changed but .claude-plugin/plugin.json version not bumped (base=$base_version, head=$head_version)."
    echo "Bump the version field before merging — Claude Code caches by version, so unbumped releases never reach users via /plugin update."
    exit 1
fi

assert_semver "$head_version" "head" || exit 1

echo "✓ Plugin version bumped: $base_version → $head_version"

# --- Core distribution -----------------------------------------------------
core_changed=0
while IFS= read -r file; do
    [ -z "$file" ] && continue
    if [[ "$file" == "$CORE_PUBLISHABLE_PREFIX"* && "$file" != "$CORE_EXEMPT_PREFIX"* ]]; then
        core_changed=1
        break
    fi
done <<< "$changed_files"

if [ "$core_changed" -eq 0 ]; then
    echo "✓ No publishable core files changed; core version bump not required."
    exit 0
fi

# Absent at the merge base means the core is new on this branch, so there is
# no previous version to compare against and nothing to demand.
if ! core_base_version=$(read_version "$CORE_VERSION_FILE" --ref "$merge_base"); then
    echo "✓ Core added on this branch; no previous version to compare."
    exit 0
fi
core_head_version=$(read_version "$CORE_VERSION_FILE" --ref "$HEAD_SHA")

if [ "$core_base_version" = "$core_head_version" ]; then
    echo "::error::Publishable core files changed but $CORE_VERSION_FILE version not bumped (base=$core_base_version, head=$core_head_version)."
    echo "Bump [project].version before merging — the core publish workflow triggers on that value, so an unbumped core is never released to PyPI."
    exit 1
fi

assert_semver "$core_head_version" "core head" || exit 1

echo "✓ Core version bumped: $core_base_version → $core_head_version"
