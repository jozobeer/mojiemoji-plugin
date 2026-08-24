#!/usr/bin/env python3
"""SemVer 2.0.0 validation and precedence, for the release guards.

Kept as a module rather than another regex embedded in a shell heredoc:
the version guard has to answer two questions — "is this well-formed?"
and "did it actually move forward?" — and the second one is precedence
logic that no amount of pattern matching gets right on its own.

CLI:
  semver.py validate <version>      exit 0 when well-formed, 1 otherwise
  semver.py compare  <a> <b>        print -1 / 0 / 1 for a vs b
"""

from __future__ import annotations

import re
import sys

# Rejects leading zeros (`01.2.3`) and malformed prerelease identifiers
# (`-..`) that a loose pattern would let through.
PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def parse(version: str) -> tuple[int, int, int, str | None] | None:
    """Return (major, minor, patch, prerelease) or None when malformed."""
    match = PATTERN.match(version)
    if match is None:
        return None
    major, minor, patch, prerelease, _build = match.groups()
    return int(major), int(minor), int(patch), prerelease


def precedence_key(version: str):
    """Sort key implementing SemVer §11 precedence.

    Build metadata is ignored, a prerelease sorts *below* the release it
    precedes, and prerelease identifiers compare field by field with
    numeric ones ordering below alphanumeric ones.
    """
    parsed = parse(version)
    if parsed is None:
        raise ValueError(f"not valid SemVer 2.0.0: {version}")
    major, minor, patch, prerelease = parsed
    if prerelease is None:
        return (major, minor, patch, 1, ())
    fields = tuple(
        (0, int(field), "") if field.isdigit() else (1, 0, field)
        for field in prerelease.split(".")
    )
    return (major, minor, patch, 0, fields)


def compare(left: str, right: str) -> int:
    a, b = precedence_key(left), precedence_key(right)
    return (a > b) - (a < b)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) == 2 and args[0] == "validate":
        return 0 if parse(args[1]) is not None else 1
    if len(args) == 3 and args[0] == "compare":
        try:
            print(compare(args[1], args[2]))
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        return 0
    print(__doc__.split("CLI:")[1].strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
