#!/usr/bin/env python3
"""Print one string per line from a named set/frozenset/tuple/list literal.

Used by `scripts/verify-lists-vs-docs.sh` (canonical lists vs
parameters.md) and `skills/mojiemoji-github/scripts/verify-lists-vs-service.sh`
(canonical lists vs live service HTML). Centralizing the AST walk
here prevents the two shell scripts from drifting in how they extract
canonical lists.

Both set-shaped (`FORBIDDEN_COLORS`, `COLOR_SHIFTING_ANIMATIONS`) and
tuple-shaped (`CANONICAL_FONTS`, `CANONICAL_ANIMATIONS` — kept as
tuples so catalog generation order is deterministic) declarations are
supported. After #101 these all live in `scripts/lib/constants.py`.

Usage:
    python3 scripts/extract_hook_set.py <set_name> <python_file>

Exits 1 if the named binding is missing or is not a string-literal
container. Stdout is sorted unique.
"""

from __future__ import annotations

import ast
import sys


def extract(name: str, path: str) -> set[str]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        # Handle both plain assignments (`FOO = {...}`) and annotated
        # assignments (`FOO: tuple[str, ...] = (...)`). lib/constants.py
        # uses the annotated form for CANONICAL_FONTS / CANONICAL_ANIMATIONS
        # to document the value shape.
        if isinstance(node, ast.AnnAssign):
            targets = [node.target] if node.value is not None else []
        elif isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            continue
        for target in targets:
            if not (isinstance(target, ast.Name) and target.id == name):
                continue
            value = node.value
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
                    f"{name} in {path} is not a set/tuple/list literal "
                    f"(got {type(value).__name__}); supported: "
                    f"`{{...}}`, `(...)`, `[...]`, `frozenset({{...}})`"
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
