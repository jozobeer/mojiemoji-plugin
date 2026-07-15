#!/usr/bin/env python3
"""Read and update mojiemoji configuration from any working directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable


GITHUB_SCRIPTS = Path(__file__).resolve().parents[2] / "mojiemoji-github" / "scripts"
sys.path.insert(0, str(GITHUB_SCRIPTS))

from lib.config import (  # noqa: E402
    get_config_path,
    get_intensity,
    set_intensity,
    unset_intensity,
)


def config_printed(_: argparse.Namespace) -> int:
    print(f"config={get_config_path()}")
    print(f"intensity={get_intensity() or '(unset, default aggressive)'}")
    return 0


def intensity_set(args: argparse.Namespace) -> int:
    set_intensity(args.value)
    return 0


def intensity_unset(_: argparse.Namespace) -> int:
    unset_intensity()
    return 0


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("get").set_defaults(action=config_printed)
    set_parser = commands.add_parser("set")
    set_parser.add_argument("value", choices=("aggressive", "normal", "minimal"))
    set_parser.set_defaults(action=intensity_set)
    commands.add_parser("unset").set_defaults(action=intensity_unset)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = argument_parser().parse_args(argv)
    action: Callable[[argparse.Namespace], int] = args.action
    return action(args)


if __name__ == "__main__":
    raise SystemExit(main())
