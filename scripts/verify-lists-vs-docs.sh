#!/usr/bin/env bash
# Verify that the canonical font / animation allowlists in the hook
# match the lists documented in parameters.md, plus FORBIDDEN_COLORS
# is consistent across hook and lib/constants.py, plus the generator's
# raw Tailwind palette has no overlap with FORBIDDEN_COLORS.
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
# the hook against the live mojiemoji service HTML; this one checks
# against in-repo sources only.
#
# Exits non-zero if any list differs. Diff is printed to stderr.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$REPO_ROOT/hooks/mojiemoji-japanese-gate.py"
PARAMS="$REPO_ROOT/skills/mojiemoji-github/references/parameters.md"
EXTRACT="$REPO_ROOT/scripts/extract_hook_set.py"
GENERATOR="$REPO_ROOT/skills/mojiemoji-github/scripts/generate_catalog.py"
LIB_CONSTANTS="$REPO_ROOT/skills/mojiemoji-github/scripts/lib/constants.py"

python3 - "$HOOK" "$PARAMS" "$EXTRACT" "$GENERATOR" "$LIB_CONSTANTS" <<'PY'
import ast
import re
import subprocess
import sys

hook_path, params_path, extract_path, generator_path, lib_path = sys.argv[1:6]


def hook_set(name: str, source_path: str) -> set[str]:
    """Run scripts/extract_hook_set.py against `source_path` and return the
    named set/frozenset as a Python set of strings."""
    out = subprocess.check_output(
        [sys.executable, extract_path, name, source_path],
        text=True,
    )
    return {line for line in out.splitlines() if line}


hook_fonts = hook_set("CANONICAL_FONTS", hook_path)
hook_anims = hook_set("CANONICAL_ANIMATIONS", hook_path)
hook_forbidden = hook_set("FORBIDDEN_COLORS", hook_path)
hook_color_shifting = hook_set("COLOR_SHIFTING_ANIMATIONS", hook_path)
hook_rotational = hook_set("ROTATIONAL_ANIMATIONS", hook_path)

# --- Extract from lib/constants.py (the copy generators actually use) -----
# The generator filters with `lib.constants.FORBIDDEN_COLORS`, not the
# hook's copy. If the two drift, the catalog can quietly include colors
# the hook rejects (or exclude safe ones). Same shape of risk applies to
# COLOR_SHIFTING_ANIMATIONS and ROTATIONAL_ANIMATIONS — the helper
# scripts strip outlines / require `speed=slow` based on the lib copy,
# but the hook enforces against its own copy.
lib_forbidden = hook_set("FORBIDDEN_COLORS", lib_path)
lib_color_shifting = hook_set("COLOR_SHIFTING_ANIMATIONS", lib_path)
lib_rotational = hook_set("ROTATIONAL_ANIMATIONS", lib_path)

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

# --- Diff hook vs docs ----------------------------------------------------
errors: list[str] = []
for name, hook_s, doc_s in [
    ("CANONICAL_FONTS", hook_fonts, doc_fonts),
    ("CANONICAL_ANIMATIONS", hook_anims, doc_anims),
]:
    only_hook = hook_s - doc_s
    only_doc = doc_s - hook_s
    if only_hook or only_doc:
        msg = [f"[drift] {name}"]
        if only_hook:
            msg.append(f"  only in hook: {sorted(only_hook)}")
        if only_doc:
            msg.append(f"  only in docs: {sorted(only_doc)}")
        errors.append("\n".join(msg))

if errors:
    print("\n\n".join(errors), file=sys.stderr)
    print(
        "\nFix: update either the hook's set literal or the parameters.md "
        "code block so the two agree, then re-run this script.",
        file=sys.stderr,
    )
    sys.exit(1)

# --- hook ↔ lib set drift (FORBIDDEN_COLORS / COLOR_SHIFTING / ROTATIONAL) --
for name, hook_s, lib_s, fix_hint in [
    (
        "FORBIDDEN_COLORS",
        hook_forbidden,
        lib_forbidden,
        "The generator filters with the lib copy; drift means the "
        "catalog can quietly include colors the hook rejects.",
    ),
    (
        "COLOR_SHIFTING_ANIMATIONS",
        hook_color_shifting,
        lib_color_shifting,
        "Helper scripts strip outline params for these animations "
        "based on the lib copy; if hook doesn't agree, the hook's "
        "outline-presence check can desync.",
    ),
    (
        "ROTATIONAL_ANIMATIONS",
        hook_rotational,
        lib_rotational,
        "Helper scripts auto-inject `speed=slow` for these based on "
        "the lib copy; if hook doesn't agree, the slow-speed "
        "requirement check can desync.",
    ),
]:
    if hook_s != lib_s:
        only_hook = hook_s - lib_s
        only_lib = lib_s - hook_s
        msg = [f"[drift] {name} (hook vs lib/constants.py)"]
        if only_hook:
            msg.append(f"  only in hook: {sorted(only_hook)}")
        if only_lib:
            msg.append(f"  only in lib:  {sorted(only_lib)}")
        msg.append(f"  Fix: update either hook or lib so the two sets agree. {fix_hint}")
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

print(
    f"OK: CANONICAL_FONTS ({len(hook_fonts)}) and CANONICAL_ANIMATIONS "
    f"({len(hook_anims)}) match between hook and parameters.md; "
    f"FORBIDDEN_COLORS ({len(hook_forbidden)}), "
    f"COLOR_SHIFTING_ANIMATIONS ({len(hook_color_shifting)}), "
    f"ROTATIONAL_ANIMATIONS ({len(hook_rotational)}) "
    f"match between hook and lib; "
    f"FORBIDDEN_COLORS ∩ TAILWIND palette = ∅"
)
PY
