#!/usr/bin/env bash
# Verify that the canonical font / animation allowlists in the hook
# match the lists documented in parameters.md.
#
# Drift between these two locations is the root cause of multiple
# silent failures (the hook rejects a value the docs say is valid, or
# accepts a value the docs say is wrong). The CI workflow runs this on
# every PR and weekly; humans can run it locally before bumping either
# list.
#
# Exits non-zero if any list differs. Diff is printed to stderr.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$REPO_ROOT/hooks/mojiemoji-japanese-gate.py"
PARAMS="$REPO_ROOT/skills/mojiemoji-github/references/parameters.md"
GENERATOR="$REPO_ROOT/skills/mojiemoji-github/scripts/generate_catalog.py"
LIB_CONSTANTS="$REPO_ROOT/skills/mojiemoji-github/scripts/lib/constants.py"

python3 - "$HOOK" "$PARAMS" "$GENERATOR" "$LIB_CONSTANTS" <<'PY'
import ast
import re
import sys

hook_path, params_path, generator_path, lib_path = sys.argv[1:5]

# --- AST helpers ---------------------------------------------------------
def find_set_literal(tree, name, source_path):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    # Plain `{...}` set literal.
                    if isinstance(node.value, ast.Set):
                        return {
                            elt.value for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        }
                    # `frozenset({...})` — first positional arg is the set.
                    if (
                        isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id == "frozenset"
                        and node.value.args
                        and isinstance(node.value.args[0], ast.Set)
                    ):
                        return {
                            elt.value for elt in node.value.args[0].elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        }
    raise SystemExit(f"missing {name} in {source_path}")


# --- Extract from hook (Python set literals) ------------------------------
hook_tree = ast.parse(open(hook_path, encoding="utf-8").read())
hook_fonts = find_set_literal(hook_tree, "CANONICAL_FONTS", hook_path)
hook_anims = find_set_literal(hook_tree, "CANONICAL_ANIMATIONS", hook_path)
hook_forbidden = find_set_literal(hook_tree, "FORBIDDEN_COLORS", hook_path)

# --- Extract from lib/constants.py (the copy generators actually use) -----
# The generator filters with `lib.constants.FORBIDDEN_COLORS`, not the
# hook's copy. If the two drift, the catalog can quietly include colors
# the hook rejects (or exclude safe ones) without this script noticing.
lib_tree = ast.parse(open(lib_path, encoding="utf-8").read())
lib_forbidden = find_set_literal(lib_tree, "FORBIDDEN_COLORS", lib_path)

# --- Extract from generate_catalog (Python tuple literal) -----------------
# `_RAW_TAILWIND_PALETTE` is the unfiltered Tailwind palette the
# generator picks from. We verify its intersection with the hook's
# `FORBIDDEN_COLORS` so the generator never emits values the hook
# would block.
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

# --- Extract from parameters.md (fenced code blocks under headers) --------
params_src = open(params_path, encoding="utf-8").read()

def extract_block(header):
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

# --- Diff -----------------------------------------------------------------
errors = []
for name, hook_set, doc_set in [
    ("CANONICAL_FONTS", hook_fonts, doc_fonts),
    ("CANONICAL_ANIMATIONS", hook_anims, doc_anims),
]:
    only_hook = hook_set - doc_set
    only_doc = doc_set - hook_set
    if only_hook or only_doc:
        msg = [f"[drift] {name}"]
        if only_hook:
            msg.append(f"  only in hook: {sorted(only_hook)}")
        if only_doc:
            msg.append(f"  only in docs: {sorted(only_doc)}")
        errors.append("\n".join(msg))

if errors:
    print("\n\n".join(errors), file=sys.stderr)
    print("\nFix: update either the hook's set literal or the parameters.md "
          "code block so the two agree, then re-run this script.", file=sys.stderr)
    sys.exit(1)

# --- hook FORBIDDEN_COLORS ↔ lib FORBIDDEN_COLORS drift -------------------
if hook_forbidden != lib_forbidden:
    only_hook = hook_forbidden - lib_forbidden
    only_lib = lib_forbidden - hook_forbidden
    msg = ["[drift] FORBIDDEN_COLORS (hook vs lib/constants.py)"]
    if only_hook:
        msg.append(f"  only in hook: {sorted(only_hook)}")
    if only_lib:
        msg.append(f"  only in lib:  {sorted(only_lib)}")
    msg.append(
        "  Fix: update either hook or lib so the two sets agree. "
        "The generator filters with the lib copy; drift means the "
        "catalog can quietly include colors the hook rejects."
    )
    print("\n".join(msg), file=sys.stderr)
    sys.exit(1)

# --- FORBIDDEN ∩ TAILWIND drift -------------------------------------------
overlap = raw_palette & hook_forbidden
if overlap:
    print(
        f"[drift] _RAW_TAILWIND_PALETTE ∩ FORBIDDEN_COLORS = "
        f"{sorted(overlap)}\n"
        f"  These colors are in generate_catalog's raw palette but the "
        f"hook rejects them; runtime filter currently strips them, but "
        f"the source pool should be the single provenance.",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"OK: CANONICAL_FONTS ({len(hook_fonts)}) and CANONICAL_ANIMATIONS "
      f"({len(hook_anims)}) match between hook and parameters.md; "
      f"FORBIDDEN_COLORS ({len(hook_forbidden)}) match between hook and lib; "
      f"FORBIDDEN_COLORS ∩ TAILWIND palette = ∅")
PY
