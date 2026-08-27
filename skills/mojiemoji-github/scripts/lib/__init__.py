"""Shared helpers for mojiemoji-github skill scripts.

Single provenance for constants and small helpers that were previously
duplicated across `bump_catalog`, `cache_record`, `cache_stats`,
`generate_catalog`, `mojiemoji_markdown`, and `prestamp`.

Importing this package also makes the ``mojiemoji`` core importable
(see `core_path`), so every consumer that already reaches for `lib.X`
gets the core resolved without repeating the bootstrap. Entry points
that import only `mojiemoji.*` call `ensure_core_importable()` directly
instead, to keep the dependency visible at the top of the file.
"""

from lib.core_path import ensure_core_importable

ensure_core_importable()
