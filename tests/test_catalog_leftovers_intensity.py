"""catalog_leftovers intensity sentinel thresholds."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from conftest import REPO_ROOT

_VALIDATOR = REPO_ROOT / "hooks" / "gate" / "validators" / "catalog_leftovers.py"
_SCRIPTS = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"


def _load_validator():
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    spec = importlib.util.spec_from_file_location("catalog_leftovers_val", _VALIDATOR)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _chunked_pairs(n: int) -> str:
    # Many plain-text hits of a 2-char catalog term (padding keeps words separate).
    return "".join(f"対応{x % 10}" for x in range(n))


def test_normal_sentinel_under_threshold() -> None:
    mod = _load_validator()
    body = "<!-- mojiemoji-intensity:normal -->\n" + _chunked_pairs(25)
    assert mod.validate_catalog_leftovers(body) == 0


def test_normal_sentinel_over_threshold_blocks() -> None:
    mod = _load_validator()
    body = "<!-- mojiemoji-intensity:normal -->\n" + _chunked_pairs(35)
    assert mod.validate_catalog_leftovers(body) == 2


def test_minimal_sentinel_under_threshold() -> None:
    mod = _load_validator()
    body = "<!-- mojiemoji-intensity:minimal -->\n" + _chunked_pairs(90)
    assert mod.validate_catalog_leftovers(body) == 0


def test_minimal_sentinel_over_threshold_blocks() -> None:
    mod = _load_validator()
    body = "<!-- mojiemoji-intensity:minimal -->\n" + _chunked_pairs(110)
    assert mod.validate_catalog_leftovers(body) == 2


def test_no_sentinel_uses_aggressive_style_threshold() -> None:
    mod = _load_validator()
    body = _chunked_pairs(15)
    assert mod.validate_catalog_leftovers(body) == 2


def test_sentinel_inside_inline_code_is_ignored() -> None:
    mod = _load_validator()
    body = "`<!-- mojiemoji-intensity:minimal -->`\n" + _chunked_pairs(15)
    assert mod.validate_catalog_leftovers(body) == 2


def test_sentinel_inside_fenced_code_block_is_ignored() -> None:
    mod = _load_validator()
    body = "```\n<!-- mojiemoji-intensity:minimal -->\n```\n" + _chunked_pairs(15)
    assert mod.validate_catalog_leftovers(body) == 2


def test_sentinel_outside_decoration_is_honored() -> None:
    mod = _load_validator()
    body = "<!-- mojiemoji-intensity:minimal -->\n" + _chunked_pairs(15)
    assert mod.validate_catalog_leftovers(body) == 0
