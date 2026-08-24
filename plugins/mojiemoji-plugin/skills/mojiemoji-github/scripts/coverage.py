#!/usr/bin/env python3
"""coverage — measure mojiemoji stamp density on a markdown body.

Reads markdown from stdin, computes per-surface density / sentence-hit /
paragraph-hit / consecutive-unstamped-paragraph metrics, prints them,
and (in --mode block) exits 2 when any threshold is breached.

Trailing-decoration violations (heading / paragraph lacks a trailing
stamp) are reported as **warnings**, never as block failures — they
are a soft guideline from issue #60 Option 1. The previous "uses a
Unicode emoji that has a mojiemoji catalog variant" warning was
removed in #89: prestamp.py now auto-substitutes catalog emoji during
its emoji pass, so a Unicode emoji surviving into this check is always
intentional (catalog-miss or safe-zone) and should not nag.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.core_path import ensure_core_importable

ensure_core_importable()

from lib.repo_policy import should_skip_pr_body
from mojiemoji.lib.sentence import SENTENCE_SEP_RE


class _SurfaceThresholdsDict(dict):
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            return super().__getitem__((key, "aggressive"))
        return super().__getitem__(key)


SURFACE_THRESHOLDS: _SurfaceThresholdsDict = _SurfaceThresholdsDict(
    {
        ("issue-body", "aggressive"): {"min_density": 2.0, "min_sentence_hit": 0.30, "min_paragraph_hit": 0.40, "max_consecutive_unstamped_paragraphs": 2},
        ("issue-body", "normal"): {"min_density": 1.2, "min_sentence_hit": 0.18, "min_paragraph_hit": 0.24, "max_consecutive_unstamped_paragraphs": 3},
        ("issue-body", "minimal"): {"min_density": 0.4, "min_sentence_hit": 0.06, "min_paragraph_hit": 0.08, "max_consecutive_unstamped_paragraphs": 5},
        ("pr-body", "aggressive"): {"min_density": 2.0, "min_sentence_hit": 0.30, "min_paragraph_hit": 0.40, "max_consecutive_unstamped_paragraphs": 2},
        ("pr-body", "normal"): {"min_density": 1.2, "min_sentence_hit": 0.18, "min_paragraph_hit": 0.24, "max_consecutive_unstamped_paragraphs": 3},
        ("pr-body", "minimal"): {"min_density": 0.4, "min_sentence_hit": 0.06, "min_paragraph_hit": 0.08, "max_consecutive_unstamped_paragraphs": 5},
        ("review-body", "aggressive"): {"min_density": 2.5, "min_sentence_hit": 0.35, "min_paragraph_hit": 0.50, "max_consecutive_unstamped_paragraphs": 1},
        ("review-body", "normal"): {"min_density": 1.5, "min_sentence_hit": 0.21, "min_paragraph_hit": 0.30, "max_consecutive_unstamped_paragraphs": 2},
        ("review-body", "minimal"): {"min_density": 0.5, "min_sentence_hit": 0.07, "min_paragraph_hit": 0.10, "max_consecutive_unstamped_paragraphs": 4},
        ("comment-body", "aggressive"): {"min_density": 2.5, "min_sentence_hit": 0.35, "min_paragraph_hit": 0.50, "max_consecutive_unstamped_paragraphs": 1},
        ("comment-body", "normal"): {"min_density": 1.5, "min_sentence_hit": 0.21, "min_paragraph_hit": 0.30, "max_consecutive_unstamped_paragraphs": 2},
        ("comment-body", "minimal"): {"min_density": 0.5, "min_sentence_hit": 0.07, "min_paragraph_hit": 0.10, "max_consecutive_unstamped_paragraphs": 4},
        ("release-note", "aggressive"): {"min_density": 1.8, "min_sentence_hit": 0.25, "min_paragraph_hit": 0.40, "max_consecutive_unstamped_paragraphs": 2},
        ("release-note", "normal"): {"min_density": 1.1, "min_sentence_hit": 0.15, "min_paragraph_hit": 0.24, "max_consecutive_unstamped_paragraphs": 3},
        ("release-note", "minimal"): {"min_density": 0.4, "min_sentence_hit": 0.05, "min_paragraph_hit": 0.08, "max_consecutive_unstamped_paragraphs": 5},
    }
)

# Match only actual rendered stamps (<img src="…mojiemoji…">), not bare URLs
# in markdown links or prose.
_STAMP_URL_RE = re.compile(
    r'<img\s[^>]*src="https?://mojiemoji\.jozo\.beer/emoji/[^"]+"[^>]*>'
)

# Hiragana / Katakana / CJK Unified Ideographs.
_JAPANESE_CHAR_RE = re.compile(r"[぀-ゟ゠-ヿ一-鿿]")

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


def measure(text: str) -> dict[str, object]:
    stamp_count = len(_STAMP_URL_RE.findall(text))
    japanese_char_count = len(_JAPANESE_CHAR_RE.findall(text))
    density = 0.0 if japanese_char_count == 0 else stamp_count * 100.0 / japanese_char_count

    # Replace stamp URLs with a placeholder before sentence splitting so the
    # `?` in `?font=...` query strings does not fragment sentences (which
    # would also break the per-sentence stamp-hit check below).
    text_for_sentences = _STAMP_URL_RE.sub(" __STAMP__ ", text)
    sentences = [s for s in (s.strip() for s in SENTENCE_SEP_RE.split(text_for_sentences)) if s]
    sentence_hits = sum(1 for s in sentences if "__STAMP__" in s)
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
        # Note: "Unicode emoji has a catalog variant" used to warn here,
        # but prestamp.py now auto-substitutes catalog emoji during the
        # emoji pass (#89). If a plain Unicode emoji survives prestamp,
        # it is either catalog-miss (no asset) or inside a safe-zone
        # (code/img/url/fence) — either way, intentional. Don't nag.

    paragraph_warnings: list[str] = []
    for i, p in enumerate(inspect_paragraphs, 1):
        if not _is_prose_paragraph(p):
            continue
        if not _TRAILING_DECO_RE.search(p):
            paragraph_warnings.append(f"paragraph {i} lacks trailing decoration")
            continue
        # See heading note above — catalog-hit Unicode emoji are now
        # handled by prestamp.py's emoji pass, so any survivor here is
        # intentional and shouldn't trigger a warning.

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
    surface_choices = sorted({s for (s, _) in SURFACE_THRESHOLDS.keys()})
    parser.add_argument(
        "--surface",
        default="issue-body",
        choices=surface_choices,
        help="Surface type for thresholds",
    )
    parser.add_argument(
        "--intensity",
        default="aggressive",
        choices=["aggressive", "normal", "minimal"],
        help="Threshold tier (default: aggressive — same as pre-intensity behavior).",
    )
    parser.add_argument(
        "--mode",
        default="warn",
        choices=["warn", "block"],
        help="warn: stderr only, block: exit 2 on threshold failures",
    )
    args = parser.parse_args(argv)

    text = sys.stdin.read()
    if args.surface == "pr-body" and should_skip_pr_body():
        print(
            "surface=pr-body policy=skip stamps=0 japanese_chars=0 "
            "density=0.00 sentence_hit_rate=0.00 paragraph_hit_rate=0.00 "
            "max_consecutive_unstamped=0"
        )
        return 0

    threshold = SURFACE_THRESHOLDS[(args.surface, args.intensity)]
    metrics = measure(text)

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
