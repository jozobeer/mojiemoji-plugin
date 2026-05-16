#!/usr/bin/env python3
"""coverage — measure mojiemoji stamp density on a markdown body.

Reads markdown from stdin, computes per-surface density / sentence-hit /
paragraph-hit / consecutive-unstamped-paragraph metrics, prints them,
and (in --mode block) exits 2 when any threshold is breached.

Trailing-decoration violations (heading / paragraph lacks trailing
stamp, or uses a Unicode emoji that has a mojiemoji catalog variant)
are reported as **warnings**, never as block failures — they are a
soft guideline from issue #60 Option 1.
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

# Unicode emoji ranges: Miscellaneous Symbols, Dingbats, Emoticons,
# Supplemental Symbols and Pictographs, etc.
_EMOJI_RE = re.compile(r"[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF☀-⛿✀-➿]")
_TRAILING_DECO_RE = re.compile(rf"(?:{_STAMP_URL_RE.pattern}|{_EMOJI_RE.pattern})\s*$")

_HEADING_RE = re.compile(r"^#+\s+(.*)$")

# Fenced code blocks: ``` or ~~~ delimited. Capture multiline lazily so
# nested fences (rare) terminate at the first matching closer.
_FENCED_CODE_RE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~", re.MULTILINE)

# Trailing-deco check is only meaningful for prose paragraphs. Skip when
# the paragraph is:
#   - a table row (starts with `|` or contains a separator row)
#   - a bullet / numbered list
#   - a pure HTML block (starts with `<` and has no Japanese prose between tags)
#   - too short to be prose (<10 Japanese chars — likely metadata / inline code)
# Headings are checked separately and always required to have trailing
# decoration when they contain Japanese.
_TABLE_LINE_RE = re.compile(r"^\s*\|")
_LIST_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
_PURE_HTML_RE = re.compile(r"^\s*<")
_MIN_JAPANESE_CHARS_FOR_TRAILING_CHECK = 10

DEFAULT_EMOJI_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "emoji-catalog.yml"


def load_emoji_catalog(path: Path = DEFAULT_EMOJI_CATALOG_PATH) -> set[str]:
    """Return the set of Unicode emojis present in the mojiemoji catalog.

    Missing file → empty set (catalog is optional). Malformed YAML →
    write diagnostic to stderr and return empty set (degrade to no-op
    rather than crashing the warn path), but still surface the error so
    the maintainer notices.
    """
    if not path.exists():
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return set((data.get("emojis") or {}).keys())
    except yaml.YAMLError as exc:
        print(f"coverage: failed to parse {path}: {exc}", file=sys.stderr)
        return set()


def _is_prose_paragraph(paragraph: str) -> bool:
    """True if the paragraph should be subject to trailing-deco check.

    Filters out tables, lists, pure HTML blocks, and chunks too short to
    be considered prose. Heuristic — false positives here just mean a
    missed warning, not a wrong block.
    """
    if not paragraph.strip():
        return False
    if _JAPANESE_CHAR_RE.findall(paragraph).__len__() < _MIN_JAPANESE_CHARS_FOR_TRAILING_CHECK:
        return False
    first_line = paragraph.splitlines()[0].strip() if paragraph.splitlines() else ""
    if _TABLE_LINE_RE.match(first_line):
        return False
    if _LIST_LINE_RE.match(first_line):
        return False
    if _PURE_HTML_RE.match(first_line):
        return False
    return True


def _strip_fenced_code(text: str) -> str:
    """Remove fenced code blocks before paragraph analysis."""
    return _FENCED_CODE_RE.sub("", text)


def measure(text: str, emoji_catalog: Optional[set[str]] = None) -> dict[str, object]:
    if emoji_catalog is None:
        emoji_catalog = set()

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

    # Trailing slot detection (warning-only — never blocks).
    # Strip fenced code blocks first; otherwise headings inside ``` get
    # checked against trailing-deco regex.
    inspect_text = _strip_fenced_code(text)
    inspect_paragraphs = [
        p for p in (p.strip() for p in re.split(r"\n{2,}", inspect_text)) if p
    ]

    heading_warnings: list[str] = []
    for i, line in enumerate(inspect_text.splitlines(), 1):
        m = _HEADING_RE.match(line.strip())
        if not m:
            continue
        heading_text = m.group(1).strip()
        # Skip headings with no Japanese (e.g., "## TL;DR") — trailing
        # decoration is only enforced when the heading is Japanese prose.
        if not _JAPANESE_CHAR_RE.search(heading_text):
            continue
        if not _TRAILING_DECO_RE.search(heading_text):
            heading_warnings.append(f"line {i}: heading lacks trailing decoration")
            continue
        for emoji in _EMOJI_RE.findall(heading_text):
            if emoji in emoji_catalog:
                heading_warnings.append(
                    f"line {i}: heading uses Unicode {emoji} but mojiemoji variant exists in catalog"
                )

    paragraph_warnings: list[str] = []
    for i, p in enumerate(inspect_paragraphs, 1):
        if not _is_prose_paragraph(p):
            continue
        if not _TRAILING_DECO_RE.search(p):
            paragraph_warnings.append(f"paragraph {i} lacks trailing decoration")
            continue
        for emoji in _EMOJI_RE.findall(p):
            if emoji in emoji_catalog:
                paragraph_warnings.append(
                    f"paragraph {i} uses Unicode {emoji} but mojiemoji variant exists in catalog"
                )

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
        "heading_warnings": heading_warnings,
        "paragraph_warnings": paragraph_warnings,
    }


def check_failures(metrics: dict[str, object], threshold: dict[str, float]) -> list[str]:
    """Return only the hard-block failures (density / sentence / paragraph thresholds).

    Trailing-decoration violations are *not* included here — they are
    returned separately via ``metrics["heading_warnings"]`` /
    ``metrics["paragraph_warnings"]`` and emitted as warnings by
    ``main()`` without affecting the exit code.
    """
    failures: list[str] = []
    density = float(metrics["density"])  # type: ignore[arg-type]
    if density < threshold["min_density"]:
        failures.append(
            f"density {density:.2f} < {threshold['min_density']:.2f} "
            f"(stamps={int(metrics['stamp_count'])}, japanese_chars={int(metrics['japanese_char_count'])})"  # type: ignore[arg-type]
        )
    sentence_hit_rate = float(metrics["sentence_hit_rate"])  # type: ignore[arg-type]
    if sentence_hit_rate < threshold["min_sentence_hit"]:
        failures.append(
            f"sentence_hit_rate {sentence_hit_rate:.2f} < "
            f"{threshold['min_sentence_hit']:.2f} "
            f"({int(metrics['sentence_hits'])}/{int(metrics['sentence_total'])})"  # type: ignore[arg-type]
        )
    paragraph_hit_rate = float(metrics["paragraph_hit_rate"])  # type: ignore[arg-type]
    if paragraph_hit_rate < threshold["min_paragraph_hit"]:
        failures.append(
            f"paragraph_hit_rate {paragraph_hit_rate:.2f} < "
            f"{threshold['min_paragraph_hit']:.2f} "
            f"({int(metrics['paragraph_hits'])}/{int(metrics['paragraph_total'])})"  # type: ignore[arg-type]
        )
    max_consecutive = int(metrics["max_consecutive_unstamped"])  # type: ignore[arg-type]
    if max_consecutive > threshold["max_consecutive_unstamped_paragraphs"]:
        failures.append(
            f"consecutive_unstamped_paragraphs {max_consecutive} > "
            f"{int(threshold['max_consecutive_unstamped_paragraphs'])}"
        )
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
        f"stamps={int(metrics['stamp_count'])} "  # type: ignore[arg-type]
        f"japanese_chars={int(metrics['japanese_char_count'])} "  # type: ignore[arg-type]
        f"density={float(metrics['density']):.2f} "  # type: ignore[arg-type]
        f"sentence_hit_rate={float(metrics['sentence_hit_rate']):.2f} "  # type: ignore[arg-type]
        f"paragraph_hit_rate={float(metrics['paragraph_hit_rate']):.2f} "  # type: ignore[arg-type]
        f"max_consecutive_unstamped={int(metrics['max_consecutive_unstamped'])}"  # type: ignore[arg-type]
    )

    # Trailing-deco warnings: always stderr, never affect exit code.
    for w in metrics["heading_warnings"]:  # type: ignore[union-attr]
        print(f"coverage warning: trailing-slot: {w}", file=sys.stderr)
    for w in metrics["paragraph_warnings"]:  # type: ignore[union-attr]
        print(f"coverage warning: trailing-slot: {w}", file=sys.stderr)

    failures = check_failures(metrics, threshold)
    if failures:
        for failure in failures:
            print(f"coverage warning: {failure}", file=sys.stderr)
        if args.mode == "block":
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
