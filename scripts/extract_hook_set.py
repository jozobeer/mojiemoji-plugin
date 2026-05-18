#!/usr/bin/env python3
"""Print one identifier per line from a named set/frozenset in a Python file.

Used by `scripts/verify-lists-vs-docs.sh` (hook vs parameters.md) and
`skills/mojiemoji-github/scripts/verify-lists-vs-service.sh` (hook vs
live service HTML). Centralizing the AST walk here prevents the two
shell scripts from drifting in how they extract canonical lists.

Usage:
    python3 scripts/extract_hook_set.py <set_name> <python_file>

Exits 1 if the named binding is missing or is not a set/frozenset
literal of string constants. Stdout is sorted unique.
"""

from __future__ import annotations

import ast
import sys


def extract(name: str, path: str) -> set[str]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        # `Assign` is `X = ...`; `AnnAssign` is `X: T = ...`. The post-#101
        # `lib/constants.py` declares CANONICAL_FONTS / CANONICAL_ANIMATIONS
        # as annotated tuples (`X: tuple[str, ...] = (...)`), which appear
        # as `AnnAssign` in the AST. Without this branch the extractor
        # walks past them and raises "missing <name> in <path>".
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        for target in targets:
            if not (isinstance(target, ast.Name) and target.id == name):
                continue
            # Accept `{...}` (set), `frozenset({...})`, or `(...)` / `[...]`
            # (ordered tuple / list literals — used for canonical font /
                # animation lists in lib/constants.py).
            if isinstance(value, (ast.Set, ast.Tuple, ast.List)):
                elts = value.elts
            elif (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "frozenset"
                and value.args
                and isinstance(value.args[0], (ast.Set, ast.Tuple, ast.List))
            ):
                elts = value.args[0].elts
            else:
                raise SystemExit(
                    f"{name} in {path} is not a set/frozenset/tuple/list "
                    f"literal (got {type(value).__name__}); supported "
                    f"shapes are `{{...}}`, `frozenset({{...}})`, "
                    f"`(...)`, and `[...]`"
                )
            result: set[str] = set()
            for elt in elts:
                if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                    raise SystemExit(
                        f"{name} in {path} contains non-string element "
                        f"at line {getattr(elt, 'lineno', '?')}: "
                        f"{ast.unparse(elt) if hasattr(ast, 'unparse') else elt!r}"
                    )
                result.add(elt.value)
            return result
    raise SystemExit(f"missing {name} in {path}")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: extract_hook_set.py <set_name> <python_file>", file=sys.stderr)
        return 2
    name, path = sys.argv[1], sys.argv[2]
    for v in sorted(extract(name, path)):
        print(v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
