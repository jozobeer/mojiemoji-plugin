"""Per-stage validators.

Each validator returns `0` on pass, `2` on fail (and writes guidance
to stderr). The pipeline tuple is consumed by the hook entry point;
the catalog-leftover and schema-version checks have different
signatures and run outside the URL pipeline.
"""

from __future__ import annotations

from .canonical import validate_canonical_values
from .catalog_leftovers import validate_catalog_leftovers
from .outline import validate_outline_values
from .required_params import validate_required_params
from .schema_version import validate_schema_version
from .url_presence import validate_url_presence


# Validation stage pipeline. Each stage takes `urls` (a list of
# extracted mojiemoji URLs), returns 2 + writes stderr on violation,
# 0 otherwise. First failure short-circuits.
VALIDATION_PIPELINE = (
    validate_url_presence,
    validate_required_params,
    validate_outline_values,
    validate_canonical_values,
)

__all__ = [
    "VALIDATION_PIPELINE",
    "validate_url_presence",
    "validate_required_params",
    "validate_outline_values",
    "validate_canonical_values",
    "validate_catalog_leftovers",
    "validate_schema_version",
]
