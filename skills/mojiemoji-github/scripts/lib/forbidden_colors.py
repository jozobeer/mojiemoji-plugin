"""Dark-mode-unreadable hex colors and their 400-series replacements.

GitHub's dark theme renders Tailwind 600+ shades as effectively
invisible (low contrast against the dark grey background). The
mojiemoji service silently falls back to default rendering for some
named palette entries too — visually the same problem.

This map is the SSOT for "catalog must not ship these colors":

  - `scripts/normalize-catalog-colors.py` consumes it to rewrite both
    `prestamp-catalog.yml` and `emoji-catalog.yml` (#97 cleanup).
  - `scripts/prestamp.py` keeps it wired into `_normalize_color_value`
    as a safety net for any author who hand-writes a forbidden hex
    into a body before running the script.
  - `.github/workflows/catalog-drift-check.yml` (extension of #81)
    fails CI when a catalog `color:` / `outline:` is re-introduced
    from this set.

The hook's `canonical` validator (`hooks/gate/validators/canonical.py`)
imports a smaller `FORBIDDEN_COLORS` set from `lib/constants.py`
covering only the truly-black + already-rejected-on-URL subset. The
cleanup map here is a superset — it includes Tailwind 500-band colors
that still render but are dim on dark backgrounds, so prestamp prefers
the matching 400-series for catalog output. Drift between the two
sets is intentional and tested via test_forbidden_color_sets.
"""

from __future__ import annotations


# Forbidden hex → 400-series replacement. Keys are bare 6-digit
# lowercase hex (no `#` prefix). Replacements selected to preserve
# the original hue family (red→red, blue→blue, etc.) at a brightness
# that survives both light- and dark-mode backgrounds.
FORBIDDEN_COLOR_REPLACEMENTS: dict[str, str] = {
    # Tailwind 600 → 400 (most common offender)
    "ca8a04": "facc15",   # yellow
    "16a34a": "4ade80",   # green
    "c026d3": "e879f9",   # fuchsia
    "d97706": "fbbf24",   # amber
    "9333ea": "c084fc",   # purple
    "e11d48": "fb7185",   # rose
    "0891b2": "22d3ee",   # cyan
    "2563eb": "60a5fa",   # blue
    "7c3aed": "a78bfa",   # violet
    "db2777": "f472b6",   # pink
    "dc2626": "f87171",   # red
    "4f46e5": "818cf8",   # indigo
    "0d9488": "2dd4bf",   # teal
    "059669": "34d399",   # emerald
    "65a30d": "a3e635",   # lime
    "ea580c": "fb923c",   # orange
    # Cool neutrals 600 → 400
    "525252": "a3a3a3",   # neutral
    "475569": "94a3b8",   # slate
    "4b5563": "9ca3af",   # gray
    "52525b": "a1a1aa",   # zinc
    "57534e": "a8a29e",   # stone
    # Tailwind 700/800 → 400 (rare, but the catalog still picked
    # them up before this list was wired into output normalization)
    "b91c1c": "f87171",   # red-700
    "991b1b": "f87171",   # red-800
    "c2410c": "fb923c",   # orange-700
    "15803d": "4ade80",   # green-700
    "0e7490": "22d3ee",   # cyan-700
    "1d4ed8": "60a5fa",   # blue-700
    "4338ca": "818cf8",   # indigo-700
    "7e22ce": "c084fc",   # purple-700
    "be185d": "f472b6",   # pink-700
}


def normalize_color_value(value: str | None) -> str | None:
    """Return ``value`` mapped through `FORBIDDEN_COLOR_REPLACEMENTS`.

    Accepts a 6-digit hex with or without `#` prefix and any letter
    case. Returns the original value (preserving prefix and case) when
    the color is not on the forbidden list, or the replacement when it
    is. Returns ``None`` for ``None`` input so callers can chain it
    over optional fields without a guard.
    """
    if value is None:
        return None
    key = value.lstrip("#").lower()
    return FORBIDDEN_COLOR_REPLACEMENTS.get(key, value)
