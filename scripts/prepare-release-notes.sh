#!/usr/bin/env bash
# Prepare GitHub Release notes from a component's version file.
#
# The repository ships two independently versioned things — the plugin
# (`.claude-plugin/plugin.json`) and the `mojiemoji` core distribution
# (`packages/mojiemoji-core/pyproject.toml`) — so both the version source
# and the tag prefix are parameters rather than constants.

set -euo pipefail

mode="${RELEASE_MODE:-dry-run}"
output_file="${OUTPUT_FILE:-release-notes.md}"
version_file="${VERSION_FILE:-${PLUGIN_JSON:-.claude-plugin/plugin.json}}"
tag_prefix="${TAG_PREFIX:-plugin-v}"
component="${COMPONENT:-}"
repo="${GITHUB_REPOSITORY:-}"
target_ref="${GITHUB_SHA:-HEAD}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --mode)
            mode="${2:?missing value for --mode}"
            shift 2
            ;;
        --output)
            output_file="${2:?missing value for --output}"
            shift 2
            ;;
        --version-file | --plugin-json)
            version_file="${2:?missing value for $1}"
            shift 2
            ;;
        --tag-prefix)
            tag_prefix="${2:?missing value for --tag-prefix}"
            shift 2
            ;;
        --component)
            component="${2:?missing value for --component}"
            shift 2
            ;;
        --repo)
            repo="${2:?missing value for --repo}"
            shift 2
            ;;
        --target)
            target_ref="${2:?missing value for --target}"
            shift 2
            ;;
        *)
            echo "prepare-release-notes: unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

case "$mode" in
    dry-run | publish) ;;
    *)
        echo "prepare-release-notes: mode must be dry-run or publish, got: $mode" >&2
        exit 2
        ;;
esac

if ! command -v gh >/dev/null 2>&1; then
    echo "prepare-release-notes: gh CLI is required" >&2
    exit 1
fi

if [ -z "$repo" ]; then
    repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
fi

version="$(
    python3 - "$version_file" <<'PY'
import json
import sys

path = sys.argv[1]
if path.endswith(".toml"):
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib

    with open(path, "rb") as f:
        print(tomllib.load(f)["project"]["version"])
else:
    with open(path, encoding="utf-8") as f:
        print(json.load(f)["version"])
PY
)"
tag="${tag_prefix}${version}"
# Default the label off the tag prefix so a new component gets a sensible
# name without having to remember a second flag.
: "${component:=${tag_prefix%%-v}}"
target_sha="$(git rev-parse "$target_ref")"
# Prefer this component's own tags; fall back to the legacy un-prefixed
# `vX.Y.Z` series so the first release after the prefix change still gets a
# diff base instead of silently regenerating notes from the whole history.
previous_tag="$(
    git tag --merged "$target_sha" --list "${tag_prefix}[0-9]*" --sort=-v:refname |
        awk -v current="$tag" '$0 != current { print; exit }'
)"
if [ -z "$previous_tag" ] && [ "$tag_prefix" != "v" ]; then
    previous_tag="$(
        git tag --merged "$target_sha" --list 'v[0-9]*' --sort=-v:refname |
            awk 'NR == 1 { print }'
    )"
fi

tag_exists=0
if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
    tag_exists=1
    tag_sha="$(git rev-list -n 1 "$tag")"
    if [ "$tag_sha" != "$target_sha" ]; then
        echo "prepare-release-notes: tag $tag already points to $tag_sha, expected $target_sha" >&2
        exit 1
    fi
fi

release_lookup_error="$(mktemp)"
notes_json="$(mktemp)"
trap 'rm -f "$release_lookup_error" "$notes_json"' EXIT

release_exists=0
if gh api "repos/$repo/releases/tags/$tag" >/dev/null 2>"$release_lookup_error"; then
    release_exists=1
elif grep -q "HTTP 404" "$release_lookup_error" || grep -qi "not found" "$release_lookup_error"; then
    release_exists=0
else
    cat "$release_lookup_error" >&2
    exit 1
fi

generate_args=(
    "repos/$repo/releases/generate-notes"
    -f "tag_name=$tag"
    -f "target_commitish=$target_sha"
)
if [ -n "$previous_tag" ]; then
    generate_args+=(-f "previous_tag_name=$previous_tag")
fi

gh api "${generate_args[@]}" > "$notes_json"
generated_body="$(
    python3 - "$notes_json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    print(json.load(f).get("body", "").strip())
PY
)"

mkdir -p "$(dirname "$output_file")"
{
    printf '![release](https://img.shields.io/badge/release-%s-a855f7) ' "$tag"
    printf '![source](https://img.shields.io/badge/source-%s-60a5fa) ' "$(basename "$version_file" | tr '.-' '__')"
    printf '![mode](https://img.shields.io/badge/mode-%s-22c55e)\n\n' "$mode"
    printf '## 概要\n\n'
    printf 'この release は %s version %s の変更を ' "$component" "\`$tag\`"
    printf '<img src="https://mojiemoji.jozo.beer/emoji/%%E8%%87%%AA%%E5%%8B%%95?font=maru-bold&color=a78bfa&animation=bane&background=transparent&outline=darker&outline_width=2" alt="自動" height="24" align="absmiddle"> '
    printf 'でまとめたものです。'
    if [ -n "$previous_tag" ]; then
        printf '%s 以降の PR / issue / commit から ' "\`$previous_tag\`"
    else
        printf '既存 tag が無いため、repository history から '
    fi
    printf '<img src="https://mojiemoji.jozo.beer/emoji/%%E7%%94%%9F%%E6%%88%%90?font=maru-bold&color=38bdf8&animation=kirari&background=transparent&outline=darker&outline_width=2" alt="生成" height="24" align="absmiddle"> '
    printf 'した notes を下に並べます。\n\n'
    printf '## 変更内容\n\n'
    if [ -n "$generated_body" ]; then
        printf '%s\n' "$generated_body"
    else
        printf '_GitHub generated notes returned an empty body._\n'
    fi
} > "$output_file"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
        printf 'tag=%s\n' "$tag"
        printf 'version=%s\n' "$version"
        printf 'previous_tag=%s\n' "$previous_tag"
        printf 'target_sha=%s\n' "$target_sha"
        printf 'tag_exists=%s\n' "$tag_exists"
        printf 'release_exists=%s\n' "$release_exists"
        printf 'notes_file=%s\n' "$output_file"
    } >> "$GITHUB_OUTPUT"
fi

echo "release tag: $tag"
echo "target sha: $target_sha"
echo "previous tag: ${previous_tag:-<none>}"
echo "tag exists: $tag_exists"
echo "release exists: $release_exists"
echo "notes file: $output_file"

if [ "$mode" = "dry-run" ]; then
    echo "dry-run: release was not created"
    exit 0
fi

if [ "$release_exists" -eq 1 ]; then
    echo "publish: release $tag already exists; skipping"
    exit 0
fi

release_args=(
    "$tag"
    --repo "$repo"
    --title "$tag"
    --notes-file "$output_file"
)
if [ "$tag_exists" -eq 0 ]; then
    release_args+=(--target "$target_sha")
fi

release_url="$(gh release create "${release_args[@]}")"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf 'release_url=%s\n' "$release_url" >> "$GITHUB_OUTPUT"
fi

echo "$release_url"
