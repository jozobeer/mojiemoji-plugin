#!/usr/bin/env python3
"""prestamp — GitHub-surface entry point over the ``mojiemoji`` core.

The transform itself lives in the standalone ``mojiemoji`` distribution;
what stays here is the part that is specific to *this* plugin's host:
``--surface``. A GitHub surface is a policy input, not a rendering
input — ``pr-body`` may have to skip decoration entirely, because GitHub
can copy a PR body into the squash/merge commit message, and stamps
leaking into commit history is not something a general-purpose markdown
transformer should know or care about.

So the split is: the shim owns the surface flag and evaluates
``should_skip_pr_body()``; the core owns the transform and exposes
``suppress_markdown`` as a plain output control. Every other flag is
passed straight through, which keeps this file's documented invocation
path (``python3 prestamp.py < input.md > output.md``) stable for the CI
drift check, the ``mojiemoji_md_edit_warn`` hook, and the ``coverage`` /
``generate_catalog`` scripts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.core_path import ensure_core_importable  # noqa: E402

ensure_core_importable()

from lib.repo_policy import should_skip_pr_body  # noqa: E402
from mojiemoji.prestamp.cli import main as _core_main  # noqa: E402

SURFACES = ["issue-body", "pr-body", "review-body", "comment-body", "release-note"]
_SURFACE_HELP = (
    "GitHub surface policy gate. pr-body may skip decoration based on repo settings."
)


def surface_parser() -> argparse.ArgumentParser:
    """Parse only ``--surface``; everything else belongs to the core CLI."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--surface", default="issue-body", choices=SURFACES, help=_SURFACE_HELP)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if any(arg in ("-h", "--help") for arg in args):
        return _help_printed()

    surface_args, rest = surface_parser().parse_known_args(args)
    suppress = surface_args.surface == "pr-body" and should_skip_pr_body()
    return _core_main(rest, suppress_markdown=suppress)


def _help_printed() -> int:
    """Show the core's help, then the flag only this shim understands."""
    try:
        _core_main(["--help"])
    except SystemExit:
        pass
    print(f"\nsurface options:\n  --surface {{{','.join(SURFACES)}}}\n{' ' * 24}{_SURFACE_HELP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
