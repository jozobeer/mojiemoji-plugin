#!/usr/bin/env python3
"""markdown — build a mojiemoji image URL and emit markdown / HTML.

Single-phrase fast path: one term in, one ``<img>`` (or markdown image)
out. The multi-term pipeline is `mojiemoji.prestamp`.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Optional
from urllib.parse import quote, urlencode

from mojiemoji.lib.constants import (
    COLOR_SHIFTING_ANIMATIONS,
    ROTATIONAL_ANIMATIONS,
    default_base_url,
)


HEX6_RE = re.compile(r"\A#?[0-9a-fA-F]{6}\Z")


def hex_to_hsl(hex_str: str) -> tuple[float, float, float]:
    h = hex_str.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2.0
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        hue = (g - b) / d + (6 if g < b else 0)
    elif mx == g:
        hue = (b - r) / d + 2
    else:
        hue = (r - g) / d + 4
    return (hue * 60.0) % 360.0, s, l


def hsl_to_hex(h: float, s: float, l: float) -> str:
    h_frac = (h % 360) / 360.0

    def hue_to_rgb(p: float, q: float, t: float) -> float:
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    if s == 0:
        r = g = b = l
    else:
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue_to_rgb(p, q, h_frac + 1 / 3)
        g = hue_to_rgb(p, q, h_frac)
        b = hue_to_rgb(p, q, h_frac - 1 / 3)
    return f"{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def hue_rotated(color_hex: Optional[str], degrees: float) -> Optional[str]:
    if not color_hex or not HEX6_RE.match(color_hex):
        return None
    h, s, l = hex_to_hsl(color_hex)
    return hsl_to_hex(h + degrees, s, l)


def escape_attr(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# Markdown image alt has its own escaping rules. CommonMark treats `]` as the
# alt terminator, `\` as an escape, and a literal newline breaks the image.
def escape_md_alt(value: object) -> str:
    s = str(value).replace("\\", "\\\\")
    s = s.replace("[", "\\[").replace("]", "\\]")
    return re.sub(r"\r?\n", " ", s)


# Markdown link/image URL is delimited by parentheses. A literal ')' closes
# it. Defensive escape in case the URL grows one.
def escape_md_url(value: object) -> str:
    return str(value).replace(")", "%29").replace("(", "%28")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a mojiemoji image URL and emit markdown or HTML.",
        usage="mojiemoji_markdown.py --text TEXT [options]",
    )
    parser.add_argument("--text", help="Render text as a mojiemoji image")
    parser.add_argument("--alt", help="Alt text; defaults to --text")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL for the mojiemoji service",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--path", dest="mode", action="store_const", const="path", help="Use /emoji/{text} form (default)")
    mode.add_argument("--query", dest="mode", action="store_const", const="query", help="Use /emoji?q={text} form")
    parser.set_defaults(mode="path")
    parser.add_argument("--html", action="store_true", help="Output HTML img tag instead of markdown")
    parser.add_argument(
        "--inline",
        action="store_true",
        help="Shortcut for inline stamps: --html --height 24 --align absmiddle",
    )
    parser.add_argument("--height", help="img height attribute (html only)")
    parser.add_argument("--width", help="img width attribute (html only)")
    parser.add_argument("--align", help="img align attribute, e.g. absmiddle (html only)")
    parser.add_argument("--font", help="font parameter")
    parser.add_argument("--color", help="color parameter")
    parser.add_argument("--animation", help="animation parameter")
    parser.add_argument("--speed", help="speed parameter")
    parser.add_argument("--gradient", help="gradient parameter")
    parser.add_argument("--flip", help="flip parameter")
    parser.add_argument("--padding", help="padding parameter")
    parser.add_argument(
        "--background",
        default="transparent",
        help="background parameter (default: transparent)",
    )
    parser.add_argument(
        "--outline",
        help="outline color (hex, 'darker' / 'lighter', or 'triadic' / 'complement' to derive from --color)",
    )
    parser.add_argument(
        "--outline-width",
        dest="outline_width",
        help="outline width 0..4 px (default 0 = no outline)",
    )
    return parser


def render(opts: argparse.Namespace) -> str:
    if not opts.text:
        raise SystemExit("error: --text is required")

    if opts.inline:
        opts.html = True
        if not opts.height:
            opts.height = "24"
        if not opts.align:
            opts.align = "absmiddle"

    # Resolve --outline = "triadic" / "complement" against --color.
    if opts.outline == "triadic":
        derived = hue_rotated(opts.color, 120.0)
        opts.outline = derived or opts.outline
    elif opts.outline == "complement":
        derived = hue_rotated(opts.color, 180.0)
        opts.outline = derived or opts.outline

    # Color-shifting animations look messy with a fixed-color outline.
    animation_val = (opts.animation or "").lower()
    if animation_val in COLOR_SHIFTING_ANIMATIONS:
        opts.outline = None
        opts.outline_width = None

    # Rotational animations are unreadable at default speed. If the caller
    # picked a rotation but didn't pick a speed, inject slow. Explicit
    # choice is left alone but warned about if it's not in {step, slow}.
    if animation_val in ROTATIONAL_ANIMATIONS:
        if not opts.speed:
            opts.speed = "slow"
        elif opts.speed.lower() not in {"step", "slow"}:
            print(
                f"mojiemoji_markdown.py: --animation {animation_val} with --speed "
                f"{opts.speed} renders as an unreadable streak; the PreToolUse "
                "hook will reject this URL. Use --speed slow / --speed step, "
                "or drop --speed to auto-inject slow.",
                file=sys.stderr,
            )

    params = [
        ("font", opts.font),
        ("color", opts.color),
        ("animation", opts.animation),
        ("speed", opts.speed),
        ("gradient", opts.gradient),
        ("flip", opts.flip),
        ("padding", opts.padding),
        ("background", opts.background),
        ("outline", opts.outline),
        ("outline_width", opts.outline_width),
    ]
    params = [(k, v) for k, v in params if v is not None]

    base = (opts.base_url or default_base_url()).rstrip("/")
    alt = opts.alt or opts.text

    if opts.mode == "query":
        query = urlencode([("q", opts.text)] + params)
        path = f"/emoji?{query}"
    else:
        suffix = ""
        if params:
            suffix = "?" + urlencode(params)
        path = f"/emoji/{quote(opts.text, safe='')}{suffix}"

    url = f"{base}{path}"

    if opts.html:
        if not opts.height and not opts.width:
            print(
                "mojiemoji_markdown.py: --html without --height/--width renders "
                "at intrinsic size; use --inline or --height for inline stamps.",
                file=sys.stderr,
            )
        attrs = [("src", url), ("alt", alt)]
        if opts.height:
            attrs.append(("height", opts.height))
        if opts.width:
            attrs.append(("width", opts.width))
        if opts.align:
            attrs.append(("align", opts.align))
        rendered = " ".join(f'{k}="{escape_attr(v)}"' for k, v in attrs)
        return f"<img {rendered}>"

    return f"![{escape_md_alt(alt)}]({escape_md_url(url)})"


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    opts = parser.parse_args(argv)
    if not opts.text:
        print("error: --text is required", file=sys.stderr)
        return 1
    print(render(opts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
