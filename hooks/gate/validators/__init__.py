"""Validator stages composed into the gate's main pipeline.

Each stage returns 0 on success or 2 + writes stderr on violation.
First non-zero short-circuits in `mojiemoji_japanese_gate.main`.

`PIPELINE` is the URL-driven stage list (each takes the list of
mojiemoji URLs extracted from one inspect-text surface). Catalog
leftovers and schema-version drift are surface-level / global checks
and run separately from `main`.
"""
from __future__ import annotations

from .canonical import validate_canonical_values
from .catalog_leftovers import validate_catalog_leftovers
from .outline import validate_outline_values
from .required_params import validate_required_params
from .schema_version import validate_schema_version
from .url_presence import validate_url_presence

PIPELINE = (
    validate_url_presence,
    validate_required_params,
    validate_outline_values,
    validate_canonical_values,
)

__all__ = [
    "PIPELINE",
    "validate_canonical_values",
    "validate_catalog_leftovers",
    "validate_outline_values",
    "validate_required_params",
    "validate_schema_version",
    "validate_url_presence",
]
