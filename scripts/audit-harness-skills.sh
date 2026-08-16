#!/usr/bin/env bash
# Audit non-Claude AI harness skill files for mojiemoji URL/animation/color
# drift from the canonical lists in this repo.
#
# Scans known harness skill paths under $HOME/.config and reports
# violations of any of these 5 contracts (see issue #79):
#
#   1. URL endpoint pattern must be `/emoji/<encoded-text>` (NOT `/stamp/text?`)
#   2. All 6 mandatory query parameters must be documented
#      (font / color / animation / background / outline / outline_width)
#   3. Animation names must match the canonical 34 (no `spring`,
#      `buruburu`, `strobe`, `kanpai`, `scroll`, `blink`)
#   4. Color examples must be Tailwind 300-500 only
#      (no `dc2626`, `2563eb`, `ca8a04`, etc. — the hook rejects them)
#   5. `prestamp.py` (the 下処理 first principle) must be referenced
#
# Exit codes:
#   0 — all harness skill files audited are clean
#   1 — at least one violation found
#   2 — invocation error (e.g., no harness skill files found)
#
# This script is local-only — it reads $HOME and does not commit to or
# read from any remote. Add to CI only if the runner has the relevant
# AI harness installations mounted (unusual).
#
# Renames history (these silently fall back to defaults on the renderer):
#   spring → bane          (springy bounce)
#   buruburu → bure        (vibration)
#   strobe → tenmetsu      (blink)
#   blink → tenmetsu
#   kanpai → yatta         (celebratory)
#   scroll → tate_scroll / yoko_scroll

set -euo pipefail

HARNESSES=(
  "claude"
  "codex"
  "opencode"
  "copilot-cli"
  "gemini"
  "agy"
  "cursor"
  "windsurf"
)

BAD_ANIMATIONS=(
  "spring"
  "buruburu"
  "bururu"
  "strobe"
  "blink"
  "kanpai"
)

# Tailwind 600+ palette that the host hook rejects. Keep in sync with
# `lib/constants.py`'s FORBIDDEN_COLORS. Drift here is harmless (this
# script only audits docs) but stale entries can become false negatives.
FORBIDDEN_COLORS=(
  "dc2626" "b91c1c" "991b1b"
  "c2410c"
  "ca8a04"
  "15803d" "16a34a"
  "0e7490"
  "1d4ed8" "2563eb"
  "4338ca"
  "7e22ce"
  "be185d"
  "111827" "1f2937"
)

MANDATORY_PARAMS=(
  "font"
  "color"
  "animation"
  "background"
  "outline"
  "outline_width"
)

# Lines containing any of these markers are "do-not-use" prose and
# are excluded from bad-pattern detection. e.g.
#   "❌ /stamp/text?text=... silently 404"
#   "renames: `spring` → `bane`"
#   "NOT a query parameter (no `/stamp/text?text=`)"
#   "issue #166 (monotone failure)... animation=spring"
# We do not want to flag these mentions; they are *correct
# documentation* of what to avoid, or anti-pattern post-mortems.
DO_NOT_USE_MARKERS='(❌|NOT exist|NOT a |silently|→|renames|⚠|do NOT|誤|存在しない|silent 404|failure mode|past failures|monotone|monotonic|issue #166|Hard ban|anti-pattern|下手|失敗)'

audit_skill_file() {
  local path="$1"
  local harness="$2"
  local violations=()

  # Pre-filter: drop do-not-use prose lines, AND drop the line
  # immediately after a marker line. This handles cases where the
  # marker (`monotone`, `Hard ban`, `NOT a`) sits on the previous
  # line and the bad pattern wraps to the next line (e.g. backtick
  # spans, post-mortem bullets like "issue #166 (monotone):\n  all
  # with `animation=spring speed=normal`,").
  local filtered
  filtered=$(awk -v marker="$DO_NOT_USE_MARKERS" '
    {
      has = match($0, marker)
      if (!has && !skip) print
      skip = has ? 1 : 0
    }
  ' "$path")

  # 1. URL endpoint pattern — flag `/stamp/text?` outside do-not-use prose
  if printf '%s\n' "$filtered" | grep -qE '/stamp/text\?text='; then
    violations+=("URL pattern: uses '/stamp/text?text=' (correct: '/emoji/<encoded-text>')")
  fi

  # Positive check: `/emoji/` endpoint should be documented somewhere
  if ! grep -qE '/emoji/' "$path"; then
    violations+=("Missing reference to canonical '/emoji/<encoded-text>' endpoint")
  fi

  # 2. Mandatory params — heuristic: each must appear at least once in the file
  for param in "${MANDATORY_PARAMS[@]}"; do
    if ! grep -qE "(^|[^a-zA-Z_])$param(=|[^a-zA-Z_])" "$path"; then
      violations+=("Missing mandatory param documentation: $param")
    fi
  done

  # 3. Bad animations as recommended values (skipping do-not-use lines)
  for anim in "${BAD_ANIMATIONS[@]}"; do
    if printf '%s\n' "$filtered" | grep -qE "(--animation $anim\b|animation=$anim\b|--animation '$anim'\b)"; then
      violations+=("Animation '$anim' used as recommended value (should be a canonical name)")
    fi
  done

  # 4. Forbidden colors as recommended values (skipping do-not-use lines)
  for color in "${FORBIDDEN_COLORS[@]}"; do
    if printf '%s\n' "$filtered" | grep -qE "(--color $color\b|color=$color\b|\"$color\")"; then
      violations+=("Forbidden Tailwind 600+ color '$color' used as recommended value")
    fi
  done

  # 5. prestamp.py reference (the 下処理 first principle)
  if ! grep -qE 'prestamp\.py|prestamp first|下処理 first' "$path"; then
    violations+=("Missing reference to prestamp.py / 下処理 first principle")
  fi

  if [ ${#violations[@]} -eq 0 ]; then
    printf '[ok]   %-12s %s\n' "$harness" "$path"
    return 0
  fi

  printf '[FAIL] %-12s %s\n' "$harness" "$path"
  for v in "${violations[@]}"; do
    printf '         - %s\n' "$v"
  done
  return 1
}

main() {
  local checked=0
  local failed=0

  for harness in "${HARNESSES[@]}"; do
    local skill_path="$HOME/.config/$harness/skills/mojiemoji-github/SKILL.md"
    local rule_path="$HOME/.config/$harness/rules/mojiemoji-github.md"

    # SKILL.md (most harnesses)
    if [ -f "$skill_path" ]; then
      checked=$((checked + 1))
      if ! audit_skill_file "$skill_path" "$harness"; then
        failed=$((failed + 1))
      fi
    fi

    # rules/mojiemoji-github.md (Gemini/agy uses this in addition to / instead of skill)
    if [ -f "$rule_path" ]; then
      checked=$((checked + 1))
      if ! audit_skill_file "$rule_path" "$harness (rule)"; then
        failed=$((failed + 1))
      fi
    fi
  done

  # agy ~/.gemini skill and rule paths
  local agy_extra_paths=(
    "$HOME/.gemini/config/skills/mojiemoji-github/SKILL.md:agy (global skill)"
    "$HOME/.gemini/skills/mojiemoji-github/SKILL.md:agy (skill)"
    "$HOME/.gemini/config/rules/mojiemoji-github.md:agy (rule)"
  )
  for entry in "${agy_extra_paths[@]}"; do
    local path="${entry%%:*}"
    local label="${entry#*:}"
    if [ -f "$path" ]; then
      checked=$((checked + 1))
      if ! audit_skill_file "$path" "$label"; then
        failed=$((failed + 1))
      fi
    fi
  done

  if [ "$checked" -eq 0 ]; then
    echo "No harness skill files found under \$HOME/.config/{${HARNESSES[*]}}/{skills,rules}/mojiemoji-github/ or \$HOME/.gemini/" >&2
    exit 2
  fi

  echo
  if [ "$failed" -eq 0 ]; then
    echo "OK: $checked harness skill files audited, no violations."
    exit 0
  fi
  echo "FAIL: $failed of $checked harness skill files have violations." >&2
  echo "Run scripts/audit-harness-skills.sh after fixing to re-verify." >&2
  exit 1
}

main "$@"
