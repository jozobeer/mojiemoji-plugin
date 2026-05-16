#!/usr/bin/env python3
"""prestamp — replace catalog terms in markdown with mojiemoji <img> tags.

Reads markdown from stdin, replaces every catalog hit with a rendered
mojiemoji stamp, and writes the result to stdout. Catalog is loaded
lazily on first use so importing this module is cheap.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import zlib
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote, urlencode

import yaml

from lib.constants import DEFAULT_BASE_URL


DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "prestamp-catalog.yml"
DEFAULT_EMOJI_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "emoji-catalog.yml"

# Variation selector U+FE0F. Catalog keys are bare base codepoints
# (`⚠` not `⚠️`), per emoji-catalog.yml convention pinned by
# test_vs16_emoji_keys_use_base_codepoint. Strip from inputs before
# emoji lookup so `⚠️` (U+26A0 U+FE0F) still hits the `⚠` key.
VS16 = "️"

# Max consecutive emoji stamps in a single uninterrupted run. The 3rd
# (and beyond) emoji in `🎉🎊🎁🎀` stays raw Unicode — visually crowded
# stamps lose punch. Whitespace, other glyphs, or pre-existing `<img>`
# spans break the run (see _Masker — they become opaque tokens before
# the emoji regex sees them, so adjacency is naturally broken).
MAX_EMOJI_RUN = 2

# Single-char catalog entries need boundary assertions or they over-match.
# Single kanji (e.g. 月 / 火 / 後): block when preceded by another Han char,
# which would indicate the entry is the tail of a compound (e.g. `先月`).
# Single ASCII digit (1-9): only stamp when embedded in Japanese flow —
# preceded by kana/kanji AND followed by a non-ASCII-identifier char.
HAN_RANGE = "㐀-䶿一-鿿豈-﫿"
HIRAGANA_RANGE = "぀-ゟ"
KATAKANA_RANGE = "゠-ヿ"
SINGLE_HAN_LEFT_GUARD = f"(?<![{HAN_RANGE}])"
SINGLE_DIGIT_LEFT_GUARD = f"(?<=[{HAN_RANGE}{HIRAGANA_RANGE}{KATAKANA_RANGE}])"
SINGLE_DIGIT_RIGHT_GUARD = r"(?![A-Za-z0-9_.])"

HAN_CHAR_RE = re.compile(f"[{HAN_RANGE}]")
DIGIT_CHAR_RE = re.compile(r"\A[0-9]\Z")

# Match a markdown link target, allowing one level of nested parens
# (e.g. https://en.wikipedia.org/wiki/Foo_(disambiguation)).
LINK_TARGET = r"(?:[^()\s]|\([^()]*\))+"

# Fenced code blocks: CommonMark allows up to 3 leading spaces, and either
# ``` or ~~~ as the fence marker. The opening fence's marker and length
# determine the closing fence — track both.
FENCE_RE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})")


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> tuple[dict, dict]:
    """Return (defaults, terms) from a prestamp-catalog YAML file."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    defaults = data.get("defaults") or {}
    terms = {}
    for key, variants in (data.get("terms") or {}).items():
        # YAML auto-parses bare integer keys to int; coerce back to str so
        # the catalog regex (which is built over .keys()) works uniformly.
        terms[str(key)] = [dict(v) for v in (variants or [])]
    return defaults, terms


def build_term_re(terms: dict) -> Optional[re.Pattern[str]]:
    """Compile the 3-tier alternation pattern (multi / kanji / digit)."""
    multi_keys = sorted(
        (k for k in terms if len(k) > 1),
        key=lambda t: (-len(t), t),
    )
    kanji_keys = [k for k in terms if len(k) == 1 and HAN_CHAR_RE.match(k)]
    digit_keys = [k for k in terms if len(k) == 1 and DIGIT_CHAR_RE.match(k)]

    parts = []
    if multi_keys:
        parts.append("(?:" + "|".join(re.escape(k) for k in multi_keys) + ")")
    if kanji_keys:
        parts.append(
            f"(?:{SINGLE_HAN_LEFT_GUARD}(?:"
            + "|".join(re.escape(k) for k in kanji_keys)
            + "))"
        )
    if digit_keys:
        parts.append(
            f"(?:{SINGLE_DIGIT_LEFT_GUARD}(?:"
            + "|".join(re.escape(k) for k in digit_keys)
            + f"){SINGLE_DIGIT_RIGHT_GUARD})"
        )

    if not parts:
        return None
    return re.compile("|".join(parts))


def load_emoji_catalog(path: Path = DEFAULT_EMOJI_CATALOG_PATH) -> tuple[dict, dict]:
    """Return (defaults, emojis) from the emoji-catalog YAML file.

    Mirrors load_catalog() but reads the ``emojis:`` top-level key
    instead of ``terms:``. Values are kept as-is so the renderer sees
    the same per-variant schema (font / color / animation / outline /
    speed) as text catalog variants.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    defaults = data.get("defaults") or {}
    emojis = {}
    for key, variants in (data.get("emojis") or {}).items():
        emojis[str(key)] = [dict(v) for v in (variants or [])]
    return defaults, emojis


def build_emoji_re(emojis: dict) -> Optional[re.Pattern[str]]:
    """Compile an alternation regex matching any catalog emoji."""
    keys = sorted(emojis.keys(), key=lambda k: (-len(k), k))
    if not keys:
        return None
    return re.compile("|".join(re.escape(k) for k in keys))


def _build_url(base_url: str, text: str, flavor: dict, defaults: dict) -> str:
    merged = {**defaults, **flavor}
    params = [
        ("font", merged.get("font")),
        ("color", merged.get("color")),
        ("animation", merged.get("animation")),
        ("speed", merged.get("speed")),
        ("background", merged.get("background")),
        ("outline", merged.get("outline")),
        ("outline_width", merged.get("outline_width")),
    ]
    params = [(k, v) for k, v in params if v is not None]
    encoded = quote(text, safe="")
    return f"{base_url}/emoji/{encoded}?{urlencode(params)}"


def _render_img(base_url: str, text: str, flavor: dict, defaults: dict) -> str:
    url = _build_url(base_url, text, flavor, defaults)
    alt = html.escape(text, quote=True)
    # html.escape with quote=True escapes &, <, >, ", but the Ruby version
    # uses CGI.escapeHTML which also escapes '. Python's html.escape with
    # quote=True does both " and ' since Python 3.2 (' → &#x27;).
    src = html.escape(url, quote=True)
    return f'<img src="{src}" alt="{alt}" height="24" align="absmiddle">'


def _render_variant(base_url: str, term: str, variant: dict, defaults: dict) -> str:
    chunks = variant.get("chunks")
    if not chunks:
        return _render_img(base_url, term, variant, defaults)
    out = []
    for chunk in chunks:
        flavor = {k: v for k, v in chunk.items() if k != "text"}
        out.append(_render_img(base_url, chunk["text"], flavor, defaults))
    return "".join(out)


def _shields_badge_url(url: str) -> bool:
    return bool(re.match(r"\Ahttps?://img\.shields\.io(?:/|\Z)", url, re.IGNORECASE))


class _Masker:
    """Replace spans of text with opaque tokens, restorable in reverse order."""

    def __init__(self) -> None:
        self._tokens: list[str] = []

    def mask(self, text: str) -> str:
        token = f"__MOJIEMOJI_MASK_{len(self._tokens)}__"
        self._tokens.append(text)
        return token

    def restore(self, text: str) -> str:
        for idx in range(len(self._tokens) - 1, -1, -1):
            text = text.replace(f"__MOJIEMOJI_MASK_{idx}__", self._tokens[idx])
        return text


def _mask_safe_zones(text: str, masker: _Masker) -> str:
    """Mask code spans, HTML tags, link targets, and bare URLs.

    Shared between the text-catalog pass and the emoji pass — both
    must avoid touching identifiers, code, and existing `<img>` stamps
    inserted by the previous pass.
    """
    # Inline code spans: try 3 → 2 → 1 backtick lengths so multi-backtick
    # spans (e.g. ``foo`` or ```foo```) are masked before the 1-backtick
    # pattern would chop them mid-fence.
    text = re.sub(r"(`{3})[^`\n]+\1", lambda m: masker.mask(m.group(0)), text)
    text = re.sub(r"(`{2})(?:[^`\n]|`(?!`))+\1", lambda m: masker.mask(m.group(0)), text)
    text = re.sub(r"`[^`\n]+`", lambda m: masker.mask(m.group(0)), text)
    text = re.sub(r"<[^>]+>", lambda m: masker.mask(m.group(0)), text)

    def _img_link(m: re.Match) -> str:
        alt = m.group(1)
        url = m.group(2)
        if _shields_badge_url(url):
            return f"![{masker.mask(alt)}]({masker.mask(url)})"
        return f"![{alt}]({masker.mask(url)})"

    text = re.sub(rf"!\[([^\]]*)\]\(({LINK_TARGET})\)", _img_link, text)

    def _md_link(m: re.Match) -> str:
        target = m.group(2)
        if target.startswith("__MOJIEMOJI_MASK_"):
            return m.group(0)
        return f"{m.group(1)}{masker.mask(target)}{m.group(3)}"

    text = re.sub(rf"(!?\[[^\]]*\]\()({LINK_TARGET})(\))", _md_link, text)

    # Bare URLs: allow one level of nested parens (wikipedia-style) instead
    # of bailing at the first `)`, which would leave the URL tail exposed.
    text = re.sub(
        r"""https?://(?:[^\s<>"'()]|\([^\s<>"'()]*\))+""",
        lambda m: masker.mask(m.group(0)),
        text,
    )
    return text


def _protect_and_replace(
    text: str,
    *,
    term_re: Optional[re.Pattern[str]],
    terms: dict,
    defaults: dict,
    base_url: str,
    seed: str,
    state: dict,
) -> str:
    masker = _Masker()
    text = _mask_safe_zones(text, masker)

    if term_re is not None:
        def _replace_term(m: re.Match) -> str:
            term = m.group(0)
            variants = terms[term]
            crc_input = f"{seed}:{term}:{state['occurrence']}"
            state["occurrence"] += 1
            variant = variants[zlib.crc32(crc_input.encode("utf-8")) % len(variants)]
            return _render_variant(base_url, term, variant, defaults)

        text = term_re.sub(_replace_term, text)

    return masker.restore(text)


def _emoji_replace_line(
    line: str,
    *,
    emoji_re: re.Pattern[str],
    emojis: dict,
    defaults: dict,
    base_url: str,
    seed: str,
    state: dict,
) -> str:
    """Run the emoji pass on a single non-fenced line.

    Masks the same safe zones as the text pass — including `<img>`
    tags emitted by the text pass — and then replaces Unicode emoji
    that are catalog hits with rendered stamps. Catalog misses stay
    raw. A run of more than ``MAX_EMOJI_RUN`` adjacent catalog hits
    leaves the overflow as raw Unicode to avoid visual crowding.
    """
    masker = _Masker()
    line = _mask_safe_zones(line, masker)

    # Strip VS16 only outside masked spans — masked tokens preserve
    # their original VS16 sequences inside <img alt=...> / URL params.
    # Doing this after masking keeps that intent.
    line = line.replace(VS16, "")

    run_state = {"last_end": -1, "run": 0}

    def _replace_emoji(m: re.Match) -> str:
        if m.start() == run_state["last_end"]:
            run_state["run"] += 1
        else:
            run_state["run"] = 1
        run_state["last_end"] = m.end()

        if run_state["run"] > MAX_EMOJI_RUN:
            return m.group(0)

        emoji = m.group(0)
        variants = emojis[emoji]
        crc_input = f"{seed}:{emoji}:{state['occurrence']}"
        state["occurrence"] += 1
        variant = variants[zlib.crc32(crc_input.encode("utf-8")) % len(variants)]
        return _render_variant(base_url, emoji, variant, defaults)

    line = emoji_re.sub(_replace_emoji, line)
    return masker.restore(line)


_SUMMARY_OPEN_RE = re.compile(r"<summary\b[^>]*>")
_SUMMARY_CLOSE_RE = re.compile(r"</summary>")


def _inside_inline_code(line: str, pos: int) -> bool:
    """Return True if ``line[pos]`` falls inside an inline code span.

    Approximate: counts unescaped backticks before ``pos`` on the same
    line — odd count = inside. Handles the common `<details>/<summary>`
    documentation case (e.g. ``the `<details>/<summary>` element``)
    where a literal `<summary>` token sits between matched backticks but
    is not preceded by a backtick directly. Without this check the
    state machine flips into "skip until </summary>" mode and silently
    drops every catalog hit until a real `</summary>` shows up (which
    can be never — the issue body for #91 lost 58 stamps to this).
    """
    return line[:pos].count("`") % 2 == 1


def _find_real_summary_tag(pattern: re.Pattern[str], line: str, start: int) -> Optional[re.Match]:
    """Like ``pattern.search(line, start)`` but skips matches inside
    inline code spans.
    """
    cursor = start
    while True:
        m = pattern.search(line, cursor)
        if m is None:
            return None
        if not _inside_inline_code(line, m.start()):
            return m
        cursor = m.end()


def _transform_line(
    line: str,
    *,
    term_re: Optional[re.Pattern[str]],
    terms: dict,
    defaults: dict,
    base_url: str,
    seed: str,
    state: dict,
) -> str:
    out = []
    cursor = 0
    while True:
        if state["in_summary"]:
            close = _find_real_summary_tag(_SUMMARY_CLOSE_RE, line, cursor)
            if close:
                out.append(line[cursor : close.end()])
                cursor = close.end()
                state["in_summary"] = False
                continue
            out.append(line[cursor:])
            break

        open_match = _find_real_summary_tag(_SUMMARY_OPEN_RE, line, cursor)
        if open_match:
            segment = line[cursor : open_match.start()]
            out.append(_protect_and_replace(
                segment,
                term_re=term_re, terms=terms, defaults=defaults,
                base_url=base_url, seed=seed, state=state,
            ))
            out.append(open_match.group(0))
            cursor = open_match.end()
            state["in_summary"] = True
            continue

        out.append(_protect_and_replace(
            line[cursor:],
            term_re=term_re, terms=terms, defaults=defaults,
            base_url=base_url, seed=seed, state=state,
        ))
        break
    return "".join(out)


def _walk_lines_outside_fences(text: str):
    """Yield (line, is_outside_fence) tuples while tracking CommonMark fences.

    Centralizes the fence-state machine so both passes (text + emoji)
    follow the same definition of "in code block" — the fence marker
    line itself is reported as inside (it's structural code-block
    syntax, not prose).
    """
    in_fence = False
    fence_marker: Optional[str] = None
    for line in text.splitlines(keepends=True):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            if in_fence:
                if marker[0] == fence_marker[0] and len(marker) >= len(fence_marker):
                    in_fence = False
                    fence_marker = None
            else:
                in_fence = True
                fence_marker = marker
            yield line, False
        elif in_fence:
            yield line, False
        else:
            yield line, True


def transform(
    text: str,
    *,
    catalog_path: Optional[Path] = None,
    emoji_catalog_path: Optional[Path] = None,
    base_url: str = DEFAULT_BASE_URL,
    seed: str = "0",
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
    emoji_re: Optional[re.Pattern[str]] = None
    emoji_path = emoji_catalog_path or DEFAULT_EMOJI_CATALOG_PATH
    if emoji_path.exists():
        emoji_defaults, emojis = load_emoji_catalog(emoji_path)
        emoji_re = build_emoji_re(emojis)

    state = {"occurrence": 0, "in_summary": False}

    # Pass 1 — text catalog.
    pass1 = []
    for line, is_prose in _walk_lines_outside_fences(text):
        if is_prose:
            pass1.append(_transform_line(
                line,
                term_re=term_re, terms=terms, defaults=defaults,
                base_url=base_url, seed=seed, state=state,
            ))
        else:
            pass1.append(line)

    if emoji_re is None:
        return "".join(pass1)

    # Pass 2 — emoji catalog. Walks the pass-1 output with the same
    # fence semantics so emoji inside ```fenced code``` is left alone.
    pass2 = []
    for line, is_prose in _walk_lines_outside_fences("".join(pass1)):
        if is_prose:
            pass2.append(_emoji_replace_line(
                line,
                emoji_re=emoji_re, emojis=emojis, defaults=emoji_defaults,
                base_url=base_url, seed=seed, state=state,
            ))
        else:
            pass2.append(line)
    return "".join(pass2)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replace catalog terms in markdown with mojiemoji stamps.",
        usage="prestamp.py [--seed SEED] [--base-url URL] [--catalog PATH] < input.md > output.md",
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
    args = parser.parse_args(argv)

    text = sys.stdin.read()
    output = transform(
        text,
        catalog_path=args.catalog,
        emoji_catalog_path=args.emoji_catalog,
        base_url=args.base_url,
        seed=args.seed,
    )
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
