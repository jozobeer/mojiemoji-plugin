#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/plugins/mojiemoji-plugin"

if [ "${1:-}" = "--check" ]; then
  diff -ru "$ROOT_DIR/.codex-plugin" "$PACKAGE_DIR/.codex-plugin"
  diff -ru "$ROOT_DIR/skills" "$PACKAGE_DIR/skills"
  exit 0
fi

mkdir -p "$PACKAGE_DIR"
rm -rf "$PACKAGE_DIR/.codex-plugin" "$PACKAGE_DIR/skills"
cp -a "$ROOT_DIR/.codex-plugin" "$PACKAGE_DIR/.codex-plugin"
cp -a "$ROOT_DIR/skills" "$PACKAGE_DIR/skills"
