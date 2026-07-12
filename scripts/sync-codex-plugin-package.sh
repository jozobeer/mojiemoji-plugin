#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/plugins/mojiemoji-plugin"
CODEX_EXCLUDED_SKILLS=(
  "mojiemoji-propose"
)

remove_codex_excluded_skills() {
  local skills_dir="$1"
  local skill

  for skill in "${CODEX_EXCLUDED_SKILLS[@]}"; do
    rm -rf "${skills_dir:?}/$skill"
  done
}

copy_package_payload() {
  local target="$1"

  mkdir -p "$target"
  rm -rf "$target/.codex-plugin" "$target/skills"
  cp -R "$ROOT_DIR/.codex-plugin" "$target/.codex-plugin"
  cp -R "$ROOT_DIR/skills" "$target/skills"
  remove_codex_excluded_skills "$target/skills"
}

assert_no_symlinks() {
  local found
  found=$(find "$PACKAGE_DIR/.codex-plugin" "$PACKAGE_DIR/skills" -type l -print)
  if [ -n "$found" ]; then
    printf 'Codex package must contain real files, not symlinks:\n%s\n' "$found" >&2
    return 1
  fi
}

if [ "${1:-}" = "--check" ]; then
  expected="$(mktemp -d)"
  trap 'rm -rf "$expected"' EXIT
  copy_package_payload "$expected"
  diff -ru "$expected/.codex-plugin" "$PACKAGE_DIR/.codex-plugin"
  diff -ru "$expected/skills" "$PACKAGE_DIR/skills"
  assert_no_symlinks
  exit 0
fi

copy_package_payload "$PACKAGE_DIR"
assert_no_symlinks
