"""`prestamp.py` 未通過 detection.

Catch bodies that were posted without running prestamp.py first. The
catalog has 450+ frequent 2-char terms that should be mechanically
replaced with `<img>` tags before any AI decoration. When that step is
skipped, those terms remain plain text and the AI's manual decoration
burns tokens on what could have been a deterministic substitution.

Threshold-based to absorb single-term natural recurrence (e.g., a body
discussing 「対応」 incidentally once).

See https://github.com/jozobeer/mojiemoji-plugin/issues/70.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from lib.term_boundaries import count_occurrences

CATALOG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "skills" / "mojiemoji-github" / "data" / "prestamp-catalog.yml"
)
CATALOG_LEFTOVER_BLOCK_THRESHOLD = 10

_INTENSITY_SENTINEL_RE = re.compile(r"<!--\s*mojiemoji-intensity:(normal|minimal)\s*-->")
_INTENSITY_THRESHOLDS = {None: CATALOG_LEFTOVER_BLOCK_THRESHOLD, "normal": 30, "minimal": 100}


_catalog_terms_cache: frozenset | None = None


def _load_catalog_terms() -> frozenset:
    """Lazily parse `terms:` keys from the prestamp catalog. Fail-soft: any
    error returns an empty set so the stage is a no-op rather than a
    spurious block (catalog file missing, pyyaml unavailable, etc.)."""
    global _catalog_terms_cache
    if _catalog_terms_cache is not None:
        return _catalog_terms_cache
    try:
        import yaml  # type: ignore[import-untyped]
        with open(CATALOG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        terms = data.get("terms", {}) if isinstance(data, dict) else {}
        # Only check 2+ char terms — single-char entries (e.g. 後, 前, 月)
        # need boundary-aware matching (handled by prestamp.py) and would
        # false-positive everywhere here (先月, 以後, etc.).
        _catalog_terms_cache = frozenset(
            t for t in terms.keys() if isinstance(t, str) and len(t) >= 2
        )
    except Exception:
        _catalog_terms_cache = frozenset()
    return _catalog_terms_cache


_IMG_TAG_RE = re.compile(r"<img\s+[^>]*>", re.IGNORECASE)
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_URL_RE = re.compile(r"https?://\S+")


def _strip_decoration(text: str) -> str:
    """Remove regions that legitimately contain catalog terms without
    needing a stamp: already-rendered img tags, code blocks, inline code,
    and bare URLs (where URL-encoded JP can match catalog keys)."""
    text = _IMG_TAG_RE.sub("", text)
    text = _FENCED_CODE_RE.sub("", text)
    text = _INLINE_CODE_RE.sub("", text)
    text = _URL_RE.sub("", text)
    return text


def validate_catalog_leftovers(text: str) -> int:
    """Block when N+ catalog-registered terms remain as plain text — the
    signature of a body posted without running prestamp.py first.

    See https://github.com/jozobeer/mojiemoji-plugin/issues/70.
    """
    catalog = _load_catalog_terms()
    if not catalog:
        return 0
    stripped = _strip_decoration(text)
    m = _INTENSITY_SENTINEL_RE.search(stripped)
    intensity = m.group(1) if m else None
    threshold = _INTENSITY_THRESHOLDS[intensity]
    hits: list[tuple[str, int]] = []
    for term in catalog:
        # ASCII keys (URL, PR, OS, CI, …) need word boundaries so
        # `POST` doesn't false-count as an `OS` hit. Non-ASCII keys
        # use plain substring matching — see lib/term_boundaries.py
        # for the boundary contract shared with prestamp.py.
        n = count_occurrences(stripped, term)
        if n > 0:
            hits.append((term, n))
    total = sum(n for _, n in hits)
    if total < threshold:
        return 0
    hits.sort(key=lambda x: -x[1])
    top = ", ".join(f"{t}×{n}" if n > 1 else t for t, n in hits[:20])
    rest = f" (他 {len(hits) - 20} 語)" if len(hits) > 20 else ""
    intensity_note = ""
    if intensity is not None:
        intensity_note = f"（intensity={intensity} のため残存しきい値 {threshold} 件）"
    sys.stderr.write(
        f"🚧 prestamp.py 未通過: catalog 登録済の 2+ 字語が plain で {total} 個残存{intensity_note}\n\n"
        f"残存語 (top 20): {top}{rest}\n\n"
        f"対応: body を投稿する前に prestamp.py で機械的下処理を通してください\n"
        f"  $ python3 \"${{CLAUDE_PLUGIN_ROOT}}/skills/mojiemoji-github/scripts/prestamp.py\" \\\n"
        f"      < body.md > body-pre.md\n"
        f"  (または pipe: prestamp.py < draft.md | gh pr create --body-file -)\n\n"
        f"なぜ: catalog hit は機械的置換 (AI トークン 0) で済む箇所です。AI が\n"
        f"  hand-craft で <img> を組むと 1 stamp ≈ 100 token、{total} stamp で\n"
        f"  約 {total * 100} token / 投稿の無駄が発生します。\n"
        f"  詳細: https://github.com/jozobeer/mojiemoji-plugin/issues/70\n"
    )
    return 2
