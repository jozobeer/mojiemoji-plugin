#!/usr/bin/env bash
# Fail the CI if a PR modifies plugin source paths (see SOURCE_PATHS) without
# bumping
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
semver() { "$script_dir/semver.py" "$@"; }

CORE_VERSION_FILE="packages/mojiemoji-core/pyproject.toml"
# Everything the wheel carries. Tests live in the same directory but ship
# only in the sdist's test payload, so editing them is not a release.
CORE_PUBLISHABLE_PREFIX="packages/mojiemoji-core/"
CORE_EXEMPT_PREFIX="packages/mojiemoji-core/tests/"

SOURCE_PATHS=(
    ".agents/"
    ".claude-plugin/"
    # Only the core's `src` is vendored into the Codex payload, so only it
    # reaches users through the plugin the way `skills/` does. The core's
    # tests, README and pyproject are versioned independently — matching the
    # whole `packages/` tree here forced a fake plugin release for changes
    # the plugin never ships.
    "packages/mojiemoji-core/src/"
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

assert_semver() {
    local version="$1" label="$2"
    if ! semver validate "$version"; then
        echo "::error::$label version '$version' is not valid SemVer 2.0.0 (X.Y.Z[-prerelease][+build], no leading zeros)."
        return 1
    fi
}

# "Different from the base" is not the same as "released after it": a
# downgrade also differs. A lower version either re-uses an existing tag —
# so the release gate reads the merge as already published and the code
# never ships — or lands out of order on PyPI, where an upgrade will not
# select it over the higher release already there.
assert_version_increased() {
    local base="$1" head="$2" label="$3" hint="$4"
    if [ "$(semver compare "$head" "$base")" != "1" ]; then
        echo "::error::$label version did not increase (base=$base, head=$head)."
        echo "$hint"
        return 1
    fi
}

base_version=$(read_version .claude-plugin/plugin.json --ref "$merge_base")
head_version=$(read_version .claude-plugin/plugin.json --ref "$HEAD_SHA")

assert_semver "$head_version" "head" || exit 1

if [ "$base_version" = "$head_version" ]; then
    echo "::error::Plugin source changed but .claude-plugin/plugin.json version not bumped (base=$base_version, head=$head_version)."
    echo "Bump the version field before merging — Claude Code caches by version, so unbumped releases never reach users via /plugin update."
    exit 1
fi

assert_version_increased "$base_version" "$head_version" "Plugin" \
    "Set .claude-plugin/plugin.json to a version above the base — Claude Code caches by version, so a lower one re-serves a release users already have." || exit 1

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

assert_semver "$core_head_version" "core head" || exit 1

if [ "$core_base_version" = "$core_head_version" ]; then
    echo "::error::Publishable core files changed but $CORE_VERSION_FILE version not bumped (base=$core_base_version, head=$core_head_version)."
    echo "Bump [project].version before merging — the core publish workflow triggers on that value, so an unbumped core is never released to PyPI."
    exit 1
fi

assert_version_increased "$core_base_version" "$core_head_version" "Core" \
    "Set [project].version above the base — a lower one either re-uses an existing core tag (so this code never publishes) or lands out of order on PyPI." || exit 1

echo "✓ Core version bumped: $core_base_version → $core_head_version"
