#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/plugins/mojiemoji-plugin"
# Relative to a package root, so the same list works for the real package
# and for the temporary tree `--check` diffs against it.
PAYLOAD_PATHS=(
  "skills"
  "packages/mojiemoji-core/src"
)
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

# The Codex package is a plain source drop with no install step, so the
# `mojiemoji` core has to travel with it — the skill scripts resolve it
# from `packages/mojiemoji-core/src` relative to the package root when no
# distribution is installed. Shipping only `skills/` would leave every
# script raising ModuleNotFoundError on a Codex-only machine.
copy_package_payload() {
  local target="$1"
  local path

  mkdir -p "$target"
  for path in "${PAYLOAD_PATHS[@]}"; do
    rm -rf "${target:?}/$path"
    mkdir -p "$(dirname "$target/$path")"
    cp -R "$ROOT_DIR/$path" "$target/$path"
  done
  remove_codex_excluded_skills "$target/skills"
  remove_ignored_payload "$target"
}

assert_no_symlinks() {
  local found path
  local -a targets=("$PACKAGE_DIR/.codex-plugin")

  for path in "${PAYLOAD_PATHS[@]}"; do
    targets+=("$PACKAGE_DIR/$path")
  done

  found=$(find "${targets[@]}" -type l -print)
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
  for path in "${PAYLOAD_PATHS[@]}"; do
    mkdir -p "$(dirname "$actual/$path")"
    cp -R "$PACKAGE_DIR/$path" "$actual/$path"
  done
  remove_ignored_payload "$actual"
  for path in "${PAYLOAD_PATHS[@]}"; do
    diff -ru "$expected/$path" "$actual/$path"
  done
  assert_no_symlinks
  exit 0
fi

copy_package_payload "$PACKAGE_DIR"
assert_no_symlinks
