#!/usr/bin/env bash
# Verify that the canonical font / animation allowlists in
# `lib/constants.py` match the lists documented in `parameters.md`,
# plus the generator's raw Tailwind palette has no overlap with
# FORBIDDEN_COLORS.
#
# Until #101, the hook kept its own copies of these sets and this
# script also diffed hook-vs-lib. Decomposition collapsed those copies
# into a single source (`scripts/lib/constants.py`), so hook-vs-lib
# drift is structurally impossible now — the only drift that remains
# is constants-vs-docs and constants-vs-generator-palette.
#
# Drift between these locations is the root cause of multiple silent
# failures (the hook rejects a value the docs say is valid, accepts a
# value the docs say is wrong, or the catalog gets generated with
# colors the hook would reject at post time). The CI workflow runs
# this on every PR and weekly; humans can run it locally before
# bumping any list.
#
# Renamed from verify-canonical-lists.sh in #54 item 7 — sibling
# `skills/mojiemoji-github/scripts/verify-lists-vs-service.sh` checks
# `lib/constants.py` against the live mojiemoji service HTML; this one
# checks against in-repo sources only.
#
# Exits non-zero if any list differs. Diff is printed to stderr.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONSTANTS="$REPO_ROOT/skills/mojiemoji-github/scripts/lib/constants.py"
PARAMS="$REPO_ROOT/skills/mojiemoji-github/references/parameters.md"
EXTRACT="$REPO_ROOT/scripts/extract_hook_set.py"
GENERATOR="$REPO_ROOT/skills/mojiemoji-github/scripts/generate_catalog.py"

python3 - "$CONSTANTS" "$PARAMS" "$EXTRACT" "$GENERATOR" <<'PY'
import ast
import re
import subprocess
import sys

constants_path, params_path, extract_path, generator_path = sys.argv[1:5]


def constants_set(name: str) -> set[str]:
    """Run scripts/extract_hook_set.py against lib/constants.py and return
    the named container as a Python set of strings."""
    out = subprocess.check_output(
        [sys.executable, extract_path, name, constants_path],
        text=True,
    )
    return {line for line in out.splitlines() if line}


lib_fonts = constants_set("CANONICAL_FONTS")
lib_anims = constants_set("CANONICAL_ANIMATIONS")
lib_forbidden = constants_set("FORBIDDEN_COLORS")
lib_color_shifting = constants_set("COLOR_SHIFTING_ANIMATIONS")
lib_rotational = constants_set("ROTATIONAL_ANIMATIONS")

# --- Extract from generate_catalog (Python tuple literal) -----------------
# `_RAW_TAILWIND_PALETTE` is the unfiltered Tailwind palette the
# generator picks from. We verify its intersection with
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

# --- Diff lib/constants.py vs docs ---------------------------------------
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
            msg.append(f"  only in docs:             {sorted(only_doc)}")
        errors.append("\n".join(msg))

if errors:
    print("\n\n".join(errors), file=sys.stderr)
    print(
        "\nFix: update either lib/constants.py or the parameters.md "
        "code block so the two agree, then re-run this script.",
        file=sys.stderr,
    )
    sys.exit(1)

# --- FORBIDDEN ∩ TAILWIND drift -------------------------------------------
overlap = raw_palette & lib_forbidden
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

print(
    f"OK: CANONICAL_FONTS ({len(lib_fonts)}) and CANONICAL_ANIMATIONS "
    f"({len(lib_anims)}) match between lib/constants.py and parameters.md; "
    f"FORBIDDEN_COLORS ({len(lib_forbidden)}), "
    f"COLOR_SHIFTING_ANIMATIONS ({len(lib_color_shifting)}), "
    f"ROTATIONAL_ANIMATIONS ({len(lib_rotational)}) extracted; "
    f"FORBIDDEN_COLORS ∩ TAILWIND palette = ∅"
)
PY
