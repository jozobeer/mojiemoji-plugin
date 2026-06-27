#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/plugins/mojiemoji-plugin"

assert_no_symlinks() {
  local found
  found=$(find "$PACKAGE_DIR/.codex-plugin" "$PACKAGE_DIR/skills" -type l -print)
  if [ -n "$found" ]; then
    printf 'Codex package must contain real files, not symlinks:\n%s\n' "$found" >&2
    return 1
  fi
}

if [ "${1:-}" = "--check" ]; then
  diff -ru "$ROOT_DIR/.codex-plugin" "$PACKAGE_DIR/.codex-plugin"
  diff -ru "$ROOT_DIR/skills" "$PACKAGE_DIR/skills"
  assert_no_symlinks
  exit 0
fi

mkdir -p "$PACKAGE_DIR"
rm -rf "$PACKAGE_DIR/.codex-plugin" "$PACKAGE_DIR/skills"
cp -R "$ROOT_DIR/.codex-plugin" "$PACKAGE_DIR/.codex-plugin"
cp -R "$ROOT_DIR/skills" "$PACKAGE_DIR/skills"
assert_no_symlinks
