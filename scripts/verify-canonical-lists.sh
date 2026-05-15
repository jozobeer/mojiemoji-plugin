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

python3 - "$HOOK" "$PARAMS" <<'PY'
import ast
import re
import sys

hook_path, params_path = sys.argv[1], sys.argv[2]

# --- Extract from hook (Python set literals) ------------------------------
hook_src = open(hook_path, encoding="utf-8").read()
tree = ast.parse(hook_src)

def find_set_literal(name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Set):
                        return {
                            elt.value for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        }
    raise SystemExit(f"missing {name} in {hook_path}")

hook_fonts = find_set_literal("CANONICAL_FONTS")
hook_anims = find_set_literal("CANONICAL_ANIMATIONS")

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

print(f"OK: CANONICAL_FONTS ({len(hook_fonts)}) and CANONICAL_ANIMATIONS "
      f"({len(hook_anims)}) match between hook and parameters.md")
PY
