#!/usr/bin/env bash
# Prepare GitHub Release notes from the plugin version.

set -euo pipefail

mode="${RELEASE_MODE:-dry-run}"
output_file="${OUTPUT_FILE:-release-notes.md}"
plugin_json="${PLUGIN_JSON:-.claude-plugin/plugin.json}"
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
        --plugin-json)
            plugin_json="${2:?missing value for --plugin-json}"
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
    python3 - "$plugin_json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    print(json.load(f)["version"])
PY
)"
tag="v$version"
target_sha="$(git rev-parse "$target_ref")"
previous_tag="$(
    git tag --list 'v[0-9]*' --sort=-v:refname |
        awk -v current="$tag" '$0 != current { print; exit }'
)"

release_exists=0
if gh release view "$tag" --repo "$repo" >/dev/null 2>&1; then
    release_exists=1
fi

generate_args=(
    "repos/$repo/releases/generate-notes"
    -f "tag_name=$tag"
    -f "target_commitish=$target_sha"
)
if [ -n "$previous_tag" ]; then
    generate_args+=(-f "previous_tag_name=$previous_tag")
fi

notes_json="$(mktemp)"
trap 'rm -f "$notes_json"' EXIT
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
    printf '![source](https://img.shields.io/badge/source-plugin_json-60a5fa) '
    printf '![mode](https://img.shields.io/badge/mode-%s-22c55e)\n\n' "$mode"
    printf '## 概要\n\n'
    printf 'この release は plugin version `%s` の変更を ' "$tag"
    printf '<img src="https://mojiemoji.jozo.beer/emoji/%%E8%%87%%AA%%E5%%8B%%95?font=maru-bold&color=a78bfa&animation=bane&background=transparent&outline=darker&outline_width=2" alt="自動" height="24" align="absmiddle"> '
    printf 'でまとめたものです。'
    if [ -n "$previous_tag" ]; then
        printf '`%s` 以降の PR / issue / commit から ' "$previous_tag"
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
        printf 'release_exists=%s\n' "$release_exists"
        printf 'notes_file=%s\n' "$output_file"
    } >> "$GITHUB_OUTPUT"
fi

echo "release tag: $tag"
echo "target sha: $target_sha"
echo "previous tag: ${previous_tag:-<none>}"
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

release_url="$(
    gh release create "$tag" \
        --repo "$repo" \
        --target "$target_sha" \
        --title "$tag" \
        --notes-file "$output_file"
)"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf 'release_url=%s\n' "$release_url" >> "$GITHUB_OUTPUT"
fi

echo "$release_url"
