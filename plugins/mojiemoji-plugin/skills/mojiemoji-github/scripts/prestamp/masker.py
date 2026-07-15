"""Sentinel-based safe-zone masking + restoration.

Both transform passes mask the same shape of "do not touch" content
before running their regex substitutions: inline code spans, HTML tags,
markdown link targets, image URLs, and bare URLs. Each masked span is
replaced with an opaque ``__MOJIEMOJI_MASK_<n>__`` sentinel; after the
substitution finishes, the masker restores in reverse order.

Reverse-order restore matters because masks may contain ``<img>`` tags
that themselves contain URLs the previous round masked into a lower-
indexed sentinel — restoring oldest-first would reveal an inner mask
token to the outer replacement and leave it dangling.
"""

from __future__ import annotations

import re

from prestamp.render import _shields_badge_url

# Match a markdown link target, allowing one level of nested parens
# (e.g. https://en.wikipedia.org/wiki/Foo_(disambiguation)).
LINK_TARGET = r"(?:[^()\s]|\([^()]*\))+"


class _Masker:
    """Replace spans of text with opaque tokens, restorable in reverse order."""

    def __init__(self, token_prefix: str = "__MOJIEMOJI_MASK_") -> None:
        self._token_prefix = token_prefix
        self._tokens: list[str] = []

    def mask(self, text: str) -> str:
        token = f"{self._token_prefix}{len(self._tokens)}__"
        self._tokens.append(text)
        return token

    def restore(self, text: str) -> str:
        for idx in range(len(self._tokens) - 1, -1, -1):
            text = text.replace(f"{self._token_prefix}{idx}__", self._tokens[idx])
        return text

    def matching_tokens(self, pattern: re.Pattern[str]) -> frozenset[str]:
        """Return mask tokens whose original spans fully match ``pattern``."""
        return frozenset(
            f"{self._token_prefix}{idx}__"
            for idx, original in enumerate(self._tokens)
            if pattern.fullmatch(original)
        )

    def is_token(self, text: str) -> bool:
        """Return whether ``text`` starts with this masker's token prefix."""
        return text.startswith(self._token_prefix)


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
        if masker.is_token(target):
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


__all__ = [
    "LINK_TARGET",
    "_Masker",
    "_mask_safe_zones",
]
