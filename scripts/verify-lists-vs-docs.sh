#!/usr/bin/env bash
# Verify that the canonical font / animation allowlists in
# `lib/constants.py` (the SSOT consumed by both the hook and skill
# scripts) match the lists documented in parameters.md, plus the
# generator's raw Tailwind palette has no overlap with rejected or
# cleanup-replacement forbidden colors.
#
# Drift between these locations is the root cause of multiple silent
# failures (the hook rejects a value the docs say is valid, accepts a
# value the docs say is wrong, or the catalog gets generated with
# colors the hook would reject at post time). The CI workflow runs
# this on every PR and weekly; humans can run it locally before
# bumping any list.
#
# Pre-#101 this script also diffed hook-local copies of FORBIDDEN_COLORS
# / COLOR_SHIFTING_ANIMATIONS / ROTATIONAL_ANIMATIONS against the lib
# copies. #101 made `lib/constants.py` the sole provenance and the hook
# validators import from it directly, so the hook↔lib drift check was
# removed — there is now only one source to drift from.
#
# Renamed from verify-canonical-lists.sh in #54 item 7 — sibling
# `skills/mojiemoji-github/scripts/verify-lists-vs-service.sh` checks
# the canonical allowlist against the live mojiemoji service HTML;
# this one checks against in-repo sources only.
#
# Exits non-zero if any list differs. Diff is printed to stderr.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARAMS="$REPO_ROOT/skills/mojiemoji-github/references/parameters.md"
EXTRACT="$REPO_ROOT/scripts/extract_hook_set.py"
GENERATOR="$REPO_ROOT/skills/mojiemoji-github/scripts/generate_catalog.py"
LIB_CONSTANTS="$REPO_ROOT/packages/mojiemoji-core/src/mojiemoji/lib/constants.py"
LIB_FORBIDDEN_COLORS="$REPO_ROOT/packages/mojiemoji-core/src/mojiemoji/lib/forbidden_colors.py"

python3 - "$PARAMS" "$EXTRACT" "$GENERATOR" "$LIB_CONSTANTS" "$LIB_FORBIDDEN_COLORS" <<'PY'
import ast
import re
import subprocess
import sys

params_path, extract_path, generator_path, lib_path, forbidden_path = sys.argv[1:6]


def lib_set(name: str) -> set[str]:
    """Run scripts/extract_hook_set.py against `lib/constants.py` and
    return the named set/frozenset as a Python set of strings."""
    out = subprocess.check_output(
        [sys.executable, extract_path, name, lib_path],
        text=True,
    )
    return {line for line in out.splitlines() if line}


lib_fonts = lib_set("CANONICAL_FONTS")
lib_anims = lib_set("CANONICAL_ANIMATIONS")
lib_forbidden = lib_set("FORBIDDEN_COLORS")
lib_color_shifting = lib_set("COLOR_SHIFTING_ANIMATIONS")
lib_rotational = lib_set("ROTATIONAL_ANIMATIONS")

# --- Extract from generate_catalog (Python tuple literal) -----------------
# `_RAW_TAILWIND_PALETTE` is the unfiltered Tailwind palette the
# generator picks from. We verify its intersection with `FORBIDDEN_COLORS`
# so the generator never emits values the hook would block.
gen_tree = ast.parse(open(generator_path, encoding="utf-8").read())


def find_tuple_literal(tree, name, source_path):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Tuple):
                        return {
                            elt.value for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        }
    raise SystemExit(f"missing {name} in {source_path}")


raw_palette = find_tuple_literal(gen_tree, "_RAW_TAILWIND_PALETTE", generator_path)


def find_dict_keys(tree, name, source_path):
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        elif isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            if isinstance(value, ast.Dict):
                return {
                    key.value for key in value.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
    raise SystemExit(f"missing {name} in {source_path}")


forbidden_tree = ast.parse(open(forbidden_path, encoding="utf-8").read())
replacement_forbidden = find_dict_keys(
    forbidden_tree,
    "FORBIDDEN_COLOR_REPLACEMENTS",
    forbidden_path,
)

# --- Extract from parameters.md (fenced code blocks under headers) --------
params_src = open(params_path, encoding="utf-8").read()


def extract_block(header: str) -> set[str]:
    pattern = re.compile(
        rf"^##\s+有効な\s+{header}\s+値.*?\n\n```\n(.*?)\n```",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(params_src)
    if not m:
        raise SystemExit(f"could not find '{header}' code block in {params_path}")
    return {token.strip() for token in m.group(1).replace("\n", " ").split(",") if token.strip()}


doc_anims = extract_block("animation")
doc_fonts = extract_block("font")

# --- Diff lib (SSOT) vs docs ----------------------------------------------
errors: list[str] = []
for name, lib_s, doc_s in [
    ("CANONICAL_FONTS", lib_fonts, doc_fonts),
    ("CANONICAL_ANIMATIONS", lib_anims, doc_anims),
]:
    only_lib = lib_s - doc_s
    only_doc = doc_s - lib_s
    if only_lib or only_doc:
        msg = [f"[drift] {name}"]
        if only_lib:
            msg.append(f"  only in lib/constants.py: {sorted(only_lib)}")
        if only_doc:
            msg.append(f"  only in parameters.md:    {sorted(only_doc)}")
        errors.append("\n".join(msg))

if errors:
    print("\n\n".join(errors), file=sys.stderr)
    print(
        "\nFix: update either the lib/constants.py set literal or the "
        "parameters.md code block so the two agree, then re-run this "
        "script.",
        file=sys.stderr,
    )
    sys.exit(1)

# --- FORBIDDEN ∩ TAILWIND drift -------------------------------------------
palette_forbidden = lib_forbidden | replacement_forbidden
overlap = raw_palette & palette_forbidden
if overlap:
    print(
        f"[drift] _RAW_TAILWIND_PALETTE ∩ generator-forbidden colors = "
        f"{sorted(overlap)}\n"
        f"  These colors are in generate_catalog's raw palette but the "
        f"hook or cleanup normalizer rejects them; runtime filter "
        f"currently strips them, but the source pool should be the "
        f"single provenance.",
        file=sys.stderr,
    )
    sys.exit(1)

print(
    f"OK: CANONICAL_FONTS ({len(lib_fonts)}) and CANONICAL_ANIMATIONS "
    f"({len(lib_anims)}) match between lib/constants.py and parameters.md; "
    f"FORBIDDEN_COLORS ({len(lib_forbidden)}), "
    f"COLOR_SHIFTING_ANIMATIONS ({len(lib_color_shifting)}), "
    f"ROTATIONAL_ANIMATIONS ({len(lib_rotational)}) "
    f"present in lib (single source); "
    f"generator-forbidden colors ∩ TAILWIND palette = ∅"
)
PY
