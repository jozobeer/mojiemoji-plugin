#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/plugins/mojiemoji-plugin"
CODEX_EXCLUDED_SKILLS=(
  "bump-catalog"
  "mojiemoji-propose"
)

remove_codex_excluded_skills() {
  local skills_dir="$1"
  local skill

  for skill in "${CODEX_EXCLUDED_SKILLS[@]}"; do
    rm -rf "${skills_dir:?}/$skill"
  done
}

remove_ignored_payload() {
  local target="$1"

  find "$target" -type d -name __pycache__ -prune -exec rm -rf {} +
  find "$target" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
}

copy_package_payload() {
  local target="$1"

  mkdir -p "$target"
  rm -rf "$target/skills"
  cp -R "$ROOT_DIR/skills" "$target/skills"
  remove_codex_excluded_skills "$target/skills"
  remove_ignored_payload "$target"
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
  actual="$(mktemp -d)"
  trap 'rm -rf "$expected" "$actual"' EXIT
  copy_package_payload "$expected"
  cp -R "$PACKAGE_DIR/skills" "$actual/skills"
  remove_ignored_payload "$actual"
  diff -ru "$expected/skills" "$actual/skills"
  assert_no_symlinks
  exit 0
fi

copy_package_payload "$PACKAGE_DIR"
assert_no_symlinks
