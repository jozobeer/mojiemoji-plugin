#!/usr/bin/env python3
"""Print a component's declared version, from the tree or from a git ref.

The repository versions two things in two formats — the plugin manifest
(JSON) and the core distribution's pyproject (TOML) — and three callers
need to read them: the release-notes generator, the PR bump guard, and
the core publish workflow. One reader keeps them from drifting apart on
what counts as "the version", and on what an absent file means.

Exit codes:
  0 — version printed
  2 — usage error
  3 — the file does not exist at that ref (a newly added component)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def parse_version(path: str, data: bytes) -> str:
    if path.endswith(".toml"):
        try:
            import tomllib
        except ModuleNotFoundError:  # Python 3.10
            import tomli as tomllib

        return tomllib.loads(data.decode("utf-8"))["project"]["version"]
    return json.loads(data.decode("utf-8"))["version"]


def read_bytes(path: str, ref: str | None) -> bytes | None:
    if ref is None:
        try:
            with open(path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
    )
    # A non-zero exit here is almost always "path did not exist at that
    # ref", which callers treat as "no previous version" rather than as
    # an error — the alternative is every new component tripping the guard.
    return proc.stdout if proc.returncode == 0 else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="Repository-relative path to a plugin.json or pyproject.toml")
    parser.add_argument("--ref", default=None, help="Read the file at this git ref instead of the tree")
    args = parser.parse_args(argv)

    data = read_bytes(args.path, args.ref)
    if data is None:
        return 3
    print(parse_version(args.path, data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
