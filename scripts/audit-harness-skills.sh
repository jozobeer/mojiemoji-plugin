#!/usr/bin/env bash
# Audit non-Claude AI harness skill/rule files for mojiemoji
# URL/animation/color drift from the canonical lists in this repo.
#
# Scans both the checked-in reference adapters under `harnesses/` and known
# project / personal harness-local paths. Set MOJIEMOJI_AUDIT_SCOPE to
# `repo`, `local`, or `all` (default) to restrict the scan. Reports violations
# of any of these 6 contracts (see issue #79 / #144):
#
#   1. URL endpoint pattern must be `/emoji/<encoded-text>` (NOT `/stamp/text?`)
#   2. All 6 mandatory query parameters must be documented
#      (font / color / animation / background / outline / outline_width)
#   3. Animation names must match the canonical 34 (no `spring`,
#      `buruburu`, `strobe`, `kanpai`, `scroll`, `blink`)
#   4. Color examples must be Tailwind 300-500 only
#      (no `dc2626`, `2563eb`, `ca8a04`, etc. — the hook rejects them)
#   5. `prestamp.py` (the 下処理 first principle) must be referenced
#   6. `mojiemoji-schema-version` marker must be present and match the
#      canonical marker in skills/mojiemoji-github/SKILL.md
#
# Exit codes:
#   0 — all harness skill/rule files audited are clean
#   1 — at least one violation found
#   2 — invocation error (e.g., no harness skill files found)
#
# The `local` scope reads $HOME and does not commit to or read from any
# remote. CI should use MOJIEMOJI_AUDIT_SCOPE=repo, which only audits the
# checked-in adapters under harnesses/.
#
# Renames history (these silently fall back to defaults on the renderer):
#   spring → bane          (springy bounce)
#   buruburu → bure        (vibration)
#   strobe → tenmetsu      (blink)
#   blink → tenmetsu
#   kanpai → yatta         (celebratory)
#   scroll → tate_scroll / yoko_scroll

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCOPE=${MOJIEMOJI_AUDIT_SCOPE:-all}

case "$SCOPE" in
  repo | local | all) ;;
  *)
    echo "MOJIEMOJI_AUDIT_SCOPE must be one of: repo, local, all" >&2
    exit 2
    ;;
esac

HARNESSES=(
  "claude"
  "codex"
  "opencode"
  "copilot-cli"
  "gemini"
  "agy"
  "cursor"
  "windsurf"
  "grok"
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

# Canonical schema version, read from the host SKILL.md marker. Empty when
# the marker is absent (contract 6 is then skipped — fail-soft, matching
# the Python validator's disabled-when-missing behavior).
CANONICAL_SCHEMA_VERSION=$(
  sed -nE 's/.*<!-- *mojiemoji-schema-version: *([0-9]+\.[0-9]+\.[0-9]+) *-->.*/\1/p' \
    "$REPO_ROOT/skills/mojiemoji-github/SKILL.md" 2>/dev/null | head -1
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

  # 3. Bad animations as recommended values (skipping do-not-use lines).
  #    Adapters list recommendations as bare backticked values too
  #    (e.g. "animations such as \`bane\`"), so match that form as well
  #    as flag / assignment syntax.
  for anim in "${BAD_ANIMATIONS[@]}"; do
    if printf '%s\n' "$filtered" | grep -qE "(--animation $anim\b|animation=$anim\b|--animation '$anim'\b|\`$anim\`)"; then
      violations+=("Animation '$anim' used as recommended value (should be a canonical name)")
    fi
  done

  # 4. Forbidden colors as recommended values (skipping do-not-use lines).
  #    Same backticked-list form as contract 3.
  for color in "${FORBIDDEN_COLORS[@]}"; do
    if printf '%s\n' "$filtered" | grep -qE "(--color $color\b|color=$color\b|\"$color\"|\`$color\`)"; then
      violations+=("Forbidden Tailwind 600+ color '$color' used as recommended value")
    fi
  done

  # 5. prestamp.py reference (the 下処理 first principle)
  if ! grep -qE 'prestamp\.py|prestamp first|下処理 first' "$path"; then
    violations+=("Missing reference to prestamp.py / 下処理 first principle")
  fi

  # 6. Schema-version marker must be present and match the canonical
  #    marker, so installed copies surface drift when the schema moves.
  if [ -n "$CANONICAL_SCHEMA_VERSION" ]; then
    local found_version
    found_version=$(
      sed -nE 's/.*<!-- *mojiemoji-schema-version: *([0-9]+\.[0-9]+\.[0-9]+) *-->.*/\1/p' \
        "$path" | head -1
    )
    if [ -z "$found_version" ]; then
      violations+=("Missing mojiemoji-schema-version marker (canonical: $CANONICAL_SCHEMA_VERSION)")
    elif [ "$found_version" != "$CANONICAL_SCHEMA_VERSION" ]; then
      violations+=("Schema version drift: $found_version (canonical: $CANONICAL_SCHEMA_VERSION)")
    fi
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
    local repo_candidates=(
      "$REPO_ROOT/harnesses/$harness/mojiemoji-github/SKILL.md"
      "$REPO_ROOT/harnesses/$harness/.gemini/skills/mojiemoji-github/SKILL.md"
      "$REPO_ROOT/harnesses/$harness/.cursor/rules/mojiemoji-github.mdc"
      "$REPO_ROOT/harnesses/$harness/.windsurf/rules/mojiemoji-github.md"
      "$REPO_ROOT/harnesses/$harness/rules/mojiemoji-github.md"
    )
    local local_candidates=(
      "$HOME/.config/$harness/skills/mojiemoji-github/SKILL.md"
      "$HOME/.config/$harness/rules/mojiemoji-github.md"
    )
    case "$harness" in
      copilot-cli)
        local_candidates+=(
          "$REPO_ROOT/.github/skills/mojiemoji-github/SKILL.md"
          "$REPO_ROOT/.claude/skills/mojiemoji-github/SKILL.md"
          "$REPO_ROOT/.agents/skills/mojiemoji-github/SKILL.md"
          "$HOME/.copilot/skills/mojiemoji-github/SKILL.md"
          "$HOME/.agents/skills/mojiemoji-github/SKILL.md"
        )
        ;;
      gemini)
        local_candidates+=(
          "$REPO_ROOT/.gemini/skills/mojiemoji-github/SKILL.md"
          "$HOME/.gemini/skills/mojiemoji-github/SKILL.md"
        )
        ;;
      agy)
        # agy-specific ~/.gemini/config deployment paths (see
        # docs/harnesses/agy.md); the shared ~/.gemini/skills path is
        # audited under the gemini harness to avoid double counting.
        local_candidates+=(
          "$HOME/.gemini/config/skills/mojiemoji-github/SKILL.md"
          "$HOME/.gemini/config/rules/mojiemoji-github.md"
        )
        ;;
      cursor)
        # Cursor project rules must be `.mdc` files under `.cursor/rules`
        # (plain `.md` / nested RULE.md files are ignored by Cursor).
        local_candidates+=(
          "$REPO_ROOT/.cursor/rules/mojiemoji-github.mdc"
          "$HOME/.cursor/rules/mojiemoji-github.mdc"
        )
        ;;
      windsurf)
        local_candidates+=(
          "$REPO_ROOT/.windsurf/rules/mojiemoji-github.md"
          "$REPO_ROOT/.devin/rules/mojiemoji-github.md"
          "$HOME/.windsurf/rules/mojiemoji-github.md"
          "$HOME/.devin/rules/mojiemoji-github.md"
        )
        ;;
    esac
    local candidates=()
    if [ "$SCOPE" = "repo" ] || [ "$SCOPE" = "all" ]; then
      candidates+=("${repo_candidates[@]}")
    fi
    if [ "$SCOPE" = "local" ] || [ "$SCOPE" = "all" ]; then
      candidates+=("${local_candidates[@]}")
    fi

    for path in "${candidates[@]}"; do
      if [ -f "$path" ]; then
        local label="$harness"
        case "$path" in
          "$REPO_ROOT"/harnesses/*) label="$harness (repo)" ;;
          "$REPO_ROOT"/*) label="$harness (project)" ;;
          "$HOME"/.config/*) label="$harness (local)" ;;
          "$HOME"/*) label="$harness (personal)" ;;
        esac
        checked=$((checked + 1))
        if ! audit_skill_file "$path" "$label"; then
          failed=$((failed + 1))
        fi
      fi
    done
  done

  if [ "$checked" -eq 0 ]; then
    echo "No harness skill/rule files found for scope '$SCOPE' under checked-in adapters or" >&2
    echo "known project / personal harness paths." >&2
    exit 2
  fi

  echo
  if [ "$failed" -eq 0 ]; then
    echo "OK: $checked harness skill/rule files audited, no violations."
    exit 0
  fi
  echo "FAIL: $failed of $checked harness skill/rule files have violations." >&2
  echo "Run scripts/audit-harness-skills.sh after fixing to re-verify." >&2
  exit 1
}

main "$@"
