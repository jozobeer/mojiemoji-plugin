"""CLI entry + the two-pass ``transform`` orchestrator.

``transform`` is the only callable that runs both the text and emoji
passes; ``prestamp_text`` is a thin alias kept for callers that still
follow the issue-spec naming.

Pass 2 (emoji) is skipped silently when the emoji catalog is empty or
missing — callers may pass ``emoji_catalog_path=None`` (default
location) or set it to an explicit override path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from lib.constants import DEFAULT_BASE_URL
from lib.repo_policy import should_skip_pr_body

from prestamp.catalog import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_EMOJI_CATALOG_PATH,
    MAX_EMOJI_RUN,
    build_emoji_re,
    build_term_re,
    load_catalog,
    load_emoji_catalog,
)
from prestamp.emoji_pass import _emoji_transform_line
from prestamp.lines import _observe_summary_tags, _walk_lines_outside_fences_with_reason
from prestamp.text_pass import _transform_line
from prestamp.unstamped_report import report_unstamped


def transform(
    text: str,
    *,
    catalog_path: Optional[Path] = None,
    emoji_catalog_path: Optional[Path] = None,
    base_url: str = DEFAULT_BASE_URL,
    seed: str = "0",
    intensity: str = "aggressive",
) -> str:
    """Transform markdown text by replacing catalog hits with mojiemoji stamps.

    Runs two passes:

    1. **Text catalog pass** — replaces ``prestamp-catalog.yml`` term
       hits with rendered stamps. Existing safe-zones (code, links,
       URLs, `<img>` tags) are protected.
    2. **Emoji catalog pass** — replaces Unicode emoji that appear in
       ``emoji-catalog.yml`` with rendered stamps. The pass re-masks
       all safe zones including the `<img>` tags emitted by pass 1,
       and caps consecutive emoji at ``MAX_EMOJI_RUN`` to avoid the
       visually crowded ``🎉🎊🎁🎀`` case.

    Pass 2 is skipped silently when the emoji catalog is empty or
    missing — callers may pass ``emoji_catalog_path=None`` (default
    location) or set it to an explicit override path.
    """
    defaults, terms = load_catalog(catalog_path or DEFAULT_CATALOG_PATH)
    term_re = build_term_re(terms)
    base_url = base_url.rstrip("/")

    emoji_defaults: dict = {}
    emojis: dict = {}
    emoji_re = None
    emoji_path = emoji_catalog_path or DEFAULT_EMOJI_CATALOG_PATH
    if emoji_path.exists():
        emoji_defaults, emojis = load_emoji_catalog(emoji_path)
        emoji_re = build_emoji_re(emojis)

    state = {"occurrence": 0, "in_summary": False}
    max_emoji_run = 1 if intensity == "minimal" else MAX_EMOJI_RUN

    # Pass 1 — text catalog.
    pass1 = []
    for line, is_prose, reason in _walk_lines_outside_fences_with_reason(text):
        if is_prose:
            pass1.append(_transform_line(
                line,
                term_re=term_re, terms=terms, defaults=defaults,
                base_url=base_url, seed=seed, state=state,
                intensity=intensity,
            ))
        else:
            if reason == "disabled":
                _observe_summary_tags(line, state)
            pass1.append(line)

    if emoji_re is None:
        return "".join(pass1)

    # Pass 2 — emoji catalog. Walks the pass-1 output with the same
    # fence semantics so emoji inside ```fenced code``` is left alone.
    # state["in_summary"] is reset because pass 1 already consumed
    # its open/close pairs; for well-formed input it ends back at
    # False, but reset defensively so pass 2 starts clean.
    state["in_summary"] = False
    pass2 = []
    for line, is_prose, reason in _walk_lines_outside_fences_with_reason("".join(pass1)):
        if is_prose:
            pass2.append(_emoji_transform_line(
                line,
                emoji_re=emoji_re, emojis=emojis, defaults=emoji_defaults,
                base_url=base_url, seed=seed, state=state,
                max_emoji_run=max_emoji_run,
            ))
        else:
            if reason == "disabled":
                _observe_summary_tags(line, state)
            pass2.append(line)
    return "".join(pass2)


# Alias matching the name in the #102 spec's "import 経路は
# `from prestamp import prestamp_text`" wording. transform() is the
# in-code idiom; prestamp_text exists for callers that prefer the
# noun-named entry.
prestamp_text = transform


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replace catalog terms in markdown with mojiemoji stamps.",
        usage=(
            "prestamp.py [--seed SEED] [--base-url URL] "
            "[--catalog PATH] [--surface SURFACE] < input.md > output.md"
        ),
    )
    parser.add_argument("--seed", default="0", help="Seed for deterministic flavor selection")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for the mojiemoji service")
    parser.add_argument(
        "--catalog",
        default=None,
        type=Path,
        help="Override the catalog path (default: <skill>/data/prestamp-catalog.yml)",
    )
    parser.add_argument(
        "--emoji-catalog",
        default=None,
        type=Path,
        help="Override the emoji catalog path (default: <skill>/data/emoji-catalog.yml)",
    )
    parser.add_argument(
        "--report-unstamped",
        action="store_true",
        help=(
            "Emit a JSON report of 2-8 char Japanese (Kanji/Katakana) runs "
            "that survived the transform in prose. Suppresses the markdown "
            "output. Used by /mojiemoji-propose to seed selector input "
            "(#92 / #93)."
        ),
    )
    parser.add_argument(
        "--report-unstamped-to",
        default=None,
        type=Path,
        help=(
            "Write the unstamped JSON report to PATH and emit the "
            "transformed markdown to stdout as usual. Composable form of "
            "--report-unstamped for pipelines that need both outputs."
        ),
    )
    parser.add_argument(
        "--intensity",
        default=None,
        choices=["aggressive", "normal", "minimal"],
        help=(
            "Catalog substitution density: aggressive, normal, or minimal. "
            "Defaults to config value (~/.config/mojiemoji/config.json) or "
            "'aggressive' if unset."
        ),
    )
    parser.add_argument(
        "--surface",
        default="issue-body",
        choices=["issue-body", "pr-body", "review-body", "comment-body", "release-note"],
        help="GitHub surface policy gate. pr-body may skip decoration based on repo settings.",
    )
    args = parser.parse_args(argv)

    from lib.config import get_intensity as _get_config_intensity

    resolved_intensity = args.intensity or _get_config_intensity() or "aggressive"

    text = sys.stdin.read()
    skip = args.surface == "pr-body" and should_skip_pr_body()

    # Always transform — the unstamped report is a catalog-gap analysis of
    # the body's Japanese and is surface-independent, so a pr-body skip must
    # not suppress it. Only the markdown stdout output respects `skip`.
    output = transform(
        text,
        catalog_path=args.catalog,
        emoji_catalog_path=args.emoji_catalog,
        base_url=args.base_url,
        seed=args.seed,
        intensity=resolved_intensity,
    )

    if args.report_unstamped:
        report = report_unstamped(output)
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.report_unstamped_to is not None:
        report = report_unstamped(output)
        with open(args.report_unstamped_to, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")

    if skip:
        sys.stdout.write(text)
        return 0

    if resolved_intensity in ("normal", "minimal"):
        output += f"<!-- mojiemoji-intensity:{resolved_intensity} -->\n"

    sys.stdout.write(output)
    return 0


__all__ = [
    "main",
    "prestamp_text",
    "transform",
]
