#!/usr/bin/env python3
"""coverage — measure mojiemoji stamp density on a markdown body.

Reads markdown from stdin, computes per-surface density / sentence-hit /
paragraph-hit / consecutive-unstamped-paragraph metrics, prints them,
and (in --mode block) exits 2 when any threshold is breached.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

import yaml

SURFACE_THRESHOLDS: dict[str, dict[str, float]] = {
    "issue-body":   {"min_density": 2.0, "min_sentence_hit": 0.30, "min_paragraph_hit": 0.40, "max_consecutive_unstamped_paragraphs": 2},
    "pr-body":      {"min_density": 2.0, "min_sentence_hit": 0.30, "min_paragraph_hit": 0.40, "max_consecutive_unstamped_paragraphs": 2},
    "review-body":  {"min_density": 2.5, "min_sentence_hit": 0.35, "min_paragraph_hit": 0.50, "max_consecutive_unstamped_paragraphs": 1},
    "comment-body": {"min_density": 2.5, "min_sentence_hit": 0.35, "min_paragraph_hit": 0.50, "max_consecutive_unstamped_paragraphs": 1},
    "release-note": {"min_density": 1.8, "min_sentence_hit": 0.25, "min_paragraph_hit": 0.40, "max_consecutive_unstamped_paragraphs": 2},
}

# Match only actual rendered stamps (<img src="…mojiemoji…">), not bare URLs
# in markdown links or prose.
_STAMP_URL_RE = re.compile(
    r'<img\s[^>]*src="https?://mojiemoji\.jozo\.beer/emoji/[^"]+"[^>]*>'
)

# Hiragana / Katakana / CJK Unified Ideographs.
_JAPANESE_CHAR_RE = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")
_SENTENCE_SEP_RE = re.compile(r"[。．！？!?\n]+")

# Regex for detecting trailing decorations (mojiemoji <img> tag OR Unicode emoji).
# Unicode emoji range: includes Miscellaneous Symbols, Dingbats, Emoticons,
# Supplemental Symbols and Pictographs, etc.
_EMOJI_RE = re.compile(r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]")
_TRAILING_DECO_RE = re.compile(rf"(?:{_STAMP_URL_RE.pattern}|{_EMOJI_RE.pattern})\s*$")

_HEADING_RE = re.compile(r"^#+\s+(.*)$")

DEFAULT_EMOJI_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "emoji-catalog.yml"


def load_emoji_catalog(path: Path = DEFAULT_EMOJI_CATALOG_PATH) -> set[str]:
    """Return a set of emojis present in the mojiemoji catalog."""
    if not path.exists():
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return set((data.get("emojis") or {}).keys())
    except Exception:
        return set()


def measure(text: str, emoji_catalog: set[str] = set()) -> dict[str, any]:
    stamp_count = len(_STAMP_URL_RE.findall(text))
    japanese_char_count = len(_JAPANESE_CHAR_RE.findall(text))
    density = 0.0 if japanese_char_count == 0 else stamp_count * 100.0 / japanese_char_count

    sentences = [s for s in (s.strip() for s in _SENTENCE_SEP_RE.split(text)) if s]
    sentence_hits = sum(1 for s in sentences if _STAMP_URL_RE.search(s))
    sentence_hit_rate = 0.0 if not sentences else sentence_hits / len(sentences)

    paragraphs = [p for p in (p.strip() for p in re.split(r"\n{2,}", text)) if p]
    paragraph_stamp_counts = [len(_STAMP_URL_RE.findall(p)) for p in paragraphs]
    paragraph_hits = sum(1 for c in paragraph_stamp_counts if c > 0)
    paragraph_hit_rate = 0.0 if not paragraphs else paragraph_hits / len(paragraphs)

    max_consecutive_unstamped = 0
    current_run = 0
    for count in paragraph_stamp_counts:
        if count == 0:
            current_run += 1
            if current_run > max_consecutive_unstamped:
                max_consecutive_unstamped = current_run
        else:
            current_run = 0

    # Trailing slot detection
    heading_violations = []
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        m = _HEADING_RE.match(line.strip())
        if m:
            heading_text = m.group(1).strip()
            if not _TRAILING_DECO_RE.search(heading_text):
                heading_violations.append(f"line {i}: heading lacks trailing decoration")
            else:
                # Check for Unicode emoji that could have been mojiemoji-fied
                emojis = _EMOJI_RE.findall(heading_text)
                for emoji in emojis:
                    if emoji in emoji_catalog:
                        heading_violations.append(f"line {i}: uses Unicode {emoji} but mojiemoji variant exists in catalog")

    paragraph_violations = []
    for i, p in enumerate(paragraphs, 1):
        if not _TRAILING_DECO_RE.search(p):
            paragraph_violations.append(f"paragraph {i} lacks trailing decoration")
        else:
            emojis = _EMOJI_RE.findall(p)
            for emoji in emojis:
                if emoji in emoji_catalog:
                    paragraph_violations.append(f"paragraph {i} uses Unicode {emoji} but mojiemoji variant exists in catalog")

    return {
        "stamp_count": stamp_count,
        "japanese_char_count": japanese_char_count,
        "density": density,
        "sentence_hits": sentence_hits,
        "sentence_total": len(sentences),
        "sentence_hit_rate": sentence_hit_rate,
        "paragraph_hits": paragraph_hits,
        "paragraph_total": len(paragraphs),
        "paragraph_hit_rate": paragraph_hit_rate,
        "max_consecutive_unstamped": max_consecutive_unstamped,
        "heading_violations": heading_violations,
        "paragraph_violations": paragraph_violations,
    }


def check_failures(metrics: dict[str, any], threshold: dict[str, float]) -> list[str]:
    failures: list[str] = []
    if metrics["density"] < threshold["min_density"]:
        failures.append(
            f"density {metrics['density']:.2f} < {threshold['min_density']:.2f} "
            f"(stamps={int(metrics['stamp_count'])}, japanese_chars={int(metrics['japanese_char_count'])})"
        )
    if metrics["sentence_hit_rate"] < threshold["min_sentence_hit"]:
        failures.append(
            f"sentence_hit_rate {metrics['sentence_hit_rate']:.2f} < "
            f"{threshold['min_sentence_hit']:.2f} "
            f"({int(metrics['sentence_hits'])}/{int(metrics['sentence_total'])})"
        )
    if metrics["paragraph_hit_rate"] < threshold["min_paragraph_hit"]:
        failures.append(
            f"paragraph_hit_rate {metrics['paragraph_hit_rate']:.2f} < "
            f"{threshold['min_paragraph_hit']:.2f} "
            f"({int(metrics['paragraph_hits'])}/{int(metrics['paragraph_total'])})"
        )
    if metrics["max_consecutive_unstamped"] > threshold["max_consecutive_unstamped_paragraphs"]:
        failures.append(
            f"consecutive_unstamped_paragraphs {int(metrics['max_consecutive_unstamped'])} > "
            f"{int(threshold['max_consecutive_unstamped_paragraphs'])}"
        )
    
    # Trailing slot failures (always warn for now as per issue 60 Option 1)
    for v in metrics["heading_violations"]:
        failures.append(f"trailing-slot: {v}")
    for v in metrics["paragraph_violations"]:
        failures.append(f"trailing-slot: {v}")

    return failures


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure mojiemoji stamp density on a markdown body.",
        usage="coverage.py [--surface SURFACE] [--mode warn|block] < input.md",
    )
    parser.add_argument(
        "--surface",
        default="issue-body",
        choices=list(SURFACE_THRESHOLDS.keys()),
        help="Surface type for thresholds",
    )
    parser.add_argument(
        "--mode",
        default="warn",
        choices=["warn", "block"],
        help="warn: stderr only, block: exit 2 on threshold failures",
    )
    args = parser.parse_args(argv)

    text = sys.stdin.read()
    emoji_catalog = load_emoji_catalog()
    threshold = SURFACE_THRESHOLDS[args.surface]
    metrics = measure(text, emoji_catalog)

    print(
        f"surface={args.surface} "
        f"stamps={int(metrics['stamp_count'])} "
        f"japanese_chars={int(metrics['japanese_char_count'])} "
        f"density={metrics['density']:.2f} "
        f"sentence_hit_rate={metrics['sentence_hit_rate']:.2f} "
        f"paragraph_hit_rate={metrics['paragraph_hit_rate']:.2f} "
        f"max_consecutive_unstamped={int(metrics['max_consecutive_unstamped'])}"
    )

    failures = check_failures(metrics, threshold)
    if failures:
        for failure in failures:
            print(f"coverage warning: {failure}", file=sys.stderr)
        if args.mode == "block":
            # Heading/Paragraph trailing violations also block if mode is block
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
